from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone as datetime_timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Barrier
import tempfile

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import close_old_connections, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django.urls import path, re_path, reverse
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

import core.auth as auth
from core.responses import api_success
from messaging import ws_auth
from messaging.consumers import ConversationConsumer
from messaging.models import Conversation, ConversationMember
from users.models import LocalUser


class OnePerMinuteUserThrottle(UserRateThrottle):
    rate = "1/minute"


class AuthenticatedThrottleProbeView(APIView):
    throttle_classes = [OnePerMinuteUserThrottle]

    def get(self, request):
        return api_success({"user_id": request.user.id})


urlpatterns = [
    path("throttle-probe", AuthenticatedThrottleProbeView.as_view()),
]


def _session_model(test_case):
    try:
        return apps.get_model("users", "AuthSession")
    except LookupError:
        test_case.fail("AuthSession model is not implemented")


@override_settings(
    AUTH_ACCESS_TOKEN_TTL_SECONDS=900,
    AUTH_REFRESH_TOKEN_TTL_SECONDS=30 * 24 * 3600,
    AUTH_LEGACY_TOKEN_ENABLED=True,
    AUTH_LEGACY_TOKEN_ACCEPT_UNTIL="",
)
class AuthSessionApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = LocalUser.objects.create(
            openid="auth-user",
            phone="13800000000",
            password_hash=make_password("correct-password"),
            nickname="Auth User",
        )

    def _login(self, *, phone="13800000000", device_label="test phone"):
        return self.client.post(
            "/django/api/v1/user/phone-login",
            {
                "phone": phone,
                "password": "correct-password",
                "device_label": device_label,
            },
            content_type="application/json",
        )

    def _bearer(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_login_issues_opaque_credentials_without_storing_plaintext(self):
        response = self._login()
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertFalse(payload["access_token"].startswith("lf_a_"))
        self.assertEqual(payload["token"], payload["access_token"])
        opaque = payload["session"]
        self.assertTrue(opaque["access_token"].startswith("lf_a_"))
        self.assertTrue(opaque["refresh_token"].startswith("lf_r_"))
        self.assertNotIn("refresh_token", payload)
        legacy_resolution = auth.resolve_auth_token(payload["access_token"])
        self.assertIsNotNone(legacy_resolution)
        self.assertTrue(legacy_resolution.is_legacy)
        legacy_rest = self.client.get(
            "/django/api/v1/user/me", **self._bearer(payload["access_token"])
        )
        self.assertEqual(legacy_rest.status_code, 200)
        self.assertEqual(
            ws_auth._get_user_by_token.func(payload["access_token"]),
            self.user,
        )
        self.assertEqual(opaque["expires_in"], 900)

        AuthSession = _session_model(self)
        session = AuthSession.objects.get(user=self.user)
        AuthRefreshToken = apps.get_model("users", "AuthRefreshToken")
        stored_values = {session.access_token_hash}
        stored_values.update(
            AuthRefreshToken.objects.filter(session=session).values_list(
                "token_hash", flat=True
            )
        )
        self.assertNotIn(opaque["access_token"], stored_values)
        self.assertNotIn(opaque["refresh_token"], stored_values)
        self.assertEqual(len(session.access_token_hash), 64)
        self.assertTrue(all(len(value) == 64 for value in stored_values))

        AuthSession.objects.update(access_expires_at=timezone.now() - timedelta(seconds=1))
        self.assertIsNone(auth.resolve_auth_token(opaque["access_token"]))
        self.assertIsNotNone(auth.resolve_auth_token(payload["access_token"]))

    @override_settings(AUTH_LEGACY_TOKEN_ENABLED=False)
    def test_login_omits_legacy_fields_when_legacy_authentication_is_closed(self):
        payload = self._login().json()["data"]
        self.assertNotIn("access_token", payload)
        self.assertNotIn("token", payload)
        self.assertTrue(payload["session"]["access_token"].startswith("lf_a_"))

    def test_login_legacy_fields_follow_runtime_cutoff(self):
        future = (timezone.now() + timedelta(days=1)).isoformat()
        with override_settings(
            AUTH_LEGACY_TOKEN_ENABLED=True,
            AUTH_LEGACY_TOKEN_ACCEPT_UNTIL=future,
        ):
            before = self._login().json()["data"]
            self.assertIn("access_token", before)
            self.assertIsNotNone(auth.resolve_auth_token(before["access_token"]))

        with override_settings(
            AUTH_LEGACY_TOKEN_ENABLED=True,
            AUTH_LEGACY_TOKEN_ACCEPT_UNTIL="2020-01-01T00:00:00+00:00",
        ):
            after = self._login().json()["data"]
            self.assertNotIn("access_token", after)
            self.assertNotIn("token", after)

    @override_settings(
        AUTH_ACCESS_TOKEN_TTL_SECONDS=3600,
        AUTH_REFRESH_TOKEN_TTL_SECONDS=1,
    )
    def test_initial_access_expiry_never_exceeds_family_absolute_expiry(self):
        issued = auth.create_auth_session(self.user)
        self.assertLessEqual(issued.access_expires_at, issued.refresh_expires_at)

    @override_settings(AUTH_ACCESS_TOKEN_TTL_SECONDS=0)
    def test_non_positive_auth_ttl_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            auth.create_auth_session(self.user)

    def test_access_expiry_and_forgery_are_rejected(self):
        payload = self._login().json()["data"]
        opaque = payload["session"]
        response = self.client.get(
            "/django/api/v1/user/me", **self._bearer(opaque["access_token"])
        )
        self.assertEqual(response.status_code, 200)

        AuthSession = _session_model(self)
        AuthSession.objects.update(access_expires_at=timezone.now() - timedelta(seconds=1))
        expired = self.client.get(
            "/django/api/v1/user/me", **self._bearer(opaque["access_token"])
        )
        forged = self.client.get(
            "/django/api/v1/user/me", **self._bearer("lf_a_forged")
        )
        self.assertEqual(expired.status_code, 401)
        self.assertEqual(forged.status_code, 401)

    def test_refresh_rotates_both_credentials_and_rejects_replay(self):
        original = self._login().json()["data"]["session"]
        first = self.client.post(
            "/django/api/v1/user/session/refresh",
            {"refresh_token": original["refresh_token"]},
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        rotated = first.json()["data"]
        self.assertNotEqual(rotated["access_token"], original["access_token"])
        self.assertNotEqual(rotated["refresh_token"], original["refresh_token"])

        stale_access = self.client.get(
            "/django/api/v1/user/me", **self._bearer(original["access_token"])
        )
        replay = self.client.post(
            "/django/api/v1/user/session/refresh",
            {"refresh_token": original["refresh_token"]},
            content_type="application/json",
        )
        self.assertEqual(stale_access.status_code, 401)
        self.assertEqual(replay.status_code, 401)
        self.assertIsNone(auth.resolve_auth_token(rotated["access_token"]))
        successor_after_replay = self.client.post(
            "/django/api/v1/user/session/refresh",
            {"refresh_token": rotated["refresh_token"]},
            content_type="application/json",
        )
        self.assertEqual(successor_after_replay.status_code, 401)

    def test_refresh_never_slides_family_absolute_expiry(self):
        original = self._login().json()["data"]["session"]
        AuthSession = _session_model(self)
        absolute_expiry = timezone.now() + timedelta(days=1)
        AuthSession.objects.filter(id=original["session_id"]).update(
            refresh_expires_at=absolute_expiry
        )
        rotated = self.client.post(
            "/django/api/v1/user/session/refresh",
            {"refresh_token": original["refresh_token"]},
            content_type="application/json",
        )
        self.assertEqual(rotated.status_code, 200)
        session = AuthSession.objects.get(id=original["session_id"])
        self.assertEqual(session.refresh_expires_at, absolute_expiry)
        self.assertLessEqual(
            datetime.fromisoformat(
                rotated.json()["data"]["refresh_expires_at"].replace("Z", "+00:00")
            ),
            absolute_expiry,
        )

    def test_logout_revokes_current_session_for_rest_and_shared_resolver(self):
        payload = self._login().json()["data"]["session"]
        logout = self.client.post(
            "/django/api/v1/user/session/logout",
            {},
            content_type="application/json",
            **self._bearer(payload["access_token"]),
        )
        self.assertEqual(logout.status_code, 200)
        self.assertIsNone(auth.resolve_auth_token(payload["access_token"]))
        denied = self.client.get(
            "/django/api/v1/user/me", **self._bearer(payload["access_token"])
        )
        self.assertEqual(denied.status_code, 401)

    def test_session_list_and_revoke_endpoints_are_owner_scoped(self):
        first = self._login(device_label="phone").json()["data"]["session"]
        second = self._login(device_label="tablet").json()["data"]["session"]
        outsider = LocalUser.objects.create(
            openid="outsider",
            phone="13900000000",
            password_hash=make_password("correct-password"),
        )
        outsider_login = self._login(phone=outsider.phone).json()["data"]["session"]

        response = self.client.get(
            "/django/api/v1/user/sessions", **self._bearer(second["access_token"])
        )
        self.assertEqual(response.status_code, 200)
        sessions = response.json()["data"]
        self.assertEqual({row["device_label"] for row in sessions}, {"phone", "tablet"})
        self.assertNotIn("access_token_hash", sessions[0])
        self.assertNotIn("refresh_token_hash", sessions[0])

        AuthSession = _session_model(self)
        outsider_session = AuthSession.objects.get(user=outsider)
        forbidden = self.client.post(
            f"/django/api/v1/user/sessions/{outsider_session.id}/revoke",
            {},
            content_type="application/json",
            **self._bearer(second["access_token"]),
        )
        self.assertEqual(forbidden.status_code, 404)
        self.assertIsNotNone(auth.resolve_auth_token(outsider_login["access_token"]))

        revoke_others = self.client.post(
            "/django/api/v1/user/sessions/revoke-others",
            {},
            content_type="application/json",
            **self._bearer(second["access_token"]),
        )
        self.assertEqual(revoke_others.status_code, 200)
        self.assertIsNone(auth.resolve_auth_token(first["access_token"]))
        self.assertIsNotNone(auth.resolve_auth_token(second["access_token"]))

    @override_settings(AUTH_LEGACY_TOKEN_ENABLED=True, AUTH_LEGACY_TOKEN_ACCEPT_UNTIL="")
    def test_legacy_token_can_be_enabled_during_migration(self):
        legacy = auth.issue_token(self.user.openid)
        response = self.client.get(
            "/django/api/v1/user/me", **self._bearer(legacy)
        )
        self.assertEqual(response.status_code, 200)

    def test_legacy_openid_that_starts_with_opaque_prefix_still_resolves(self):
        prefixed = LocalUser.objects.create(openid="lf_a_legacy-openid")
        legacy = auth.issue_token(prefixed.openid)
        resolution = auth.resolve_auth_token(legacy)
        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.user, prefixed)
        self.assertTrue(resolution.is_legacy)

    def test_legacy_credential_cannot_manage_opaque_sessions(self):
        payload = self._login().json()["data"]
        response = self.client.get(
            "/django/api/v1/user/sessions", **self._bearer(payload["token"])
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(AUTH_LEGACY_TOKEN_ENABLED=False)
    def test_legacy_token_can_be_disabled(self):
        legacy = auth.issue_token(self.user.openid)
        response = self.client.get(
            "/django/api/v1/user/me", **self._bearer(legacy)
        )
        self.assertEqual(response.status_code, 401)

    @override_settings(
        AUTH_LEGACY_TOKEN_ENABLED=True,
        AUTH_LEGACY_TOKEN_ACCEPT_UNTIL="2020-01-01T00:00:00+00:00",
    )
    def test_legacy_token_cutoff_is_enforced(self):
        legacy = auth.issue_token(self.user.openid)
        response = self.client.get(
            "/django/api/v1/user/me", **self._bearer(legacy)
        )
        self.assertEqual(response.status_code, 401)

    def test_drf_authentication_sets_real_request_user_for_user_throttling(self):
        payload = self._login().json()["data"]["session"]
        factory = APIRequestFactory()
        raw_request = factory.get(
            "/protected", HTTP_AUTHORIZATION=f"Bearer {payload['access_token']}"
        )
        drf_request = Request(raw_request)
        authenticator = auth.OpaqueSessionAuthentication()
        user, session = authenticator.authenticate(drf_request)
        self.assertEqual(user, self.user)
        self.assertEqual(session.user_id, self.user.id)
        self.assertTrue(user.is_authenticated)

    def test_real_api_user_throttle_is_per_authenticated_user(self):
        second_user = LocalUser.objects.create(openid="throttle-second-user")
        first_credentials = auth.create_auth_session(self.user)
        second_credentials = auth.create_auth_session(second_user)
        cache.clear()
        with override_settings(ROOT_URLCONF=__name__):
            first = self.client.get(
                "/throttle-probe",
                **self._bearer(first_credentials.access_token),
            )
            limited = self.client.get(
                "/throttle-probe",
                **self._bearer(first_credentials.access_token),
            )
            other_user = self.client.get(
                "/throttle-probe",
                **self._bearer(second_credentials.access_token),
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(other_user.status_code, 200)

    def test_last_seen_touch_updates_session_audit_timestamp(self):
        issued = auth.create_auth_session(self.user)
        old = timezone.now() - timedelta(days=1)
        AuthSession = _session_model(self)
        AuthSession.objects.filter(id=issued.session.id).update(
            last_seen_at=old,
            updated_at=old,
        )
        self.assertIsNotNone(auth.resolve_auth_token(issued.access_token))
        touched = AuthSession.objects.get(id=issued.session.id)
        self.assertGreater(touched.last_seen_at, old)
        self.assertEqual(touched.updated_at, touched.last_seen_at)

    def test_ws_header_precedes_query_and_shared_resolver_honors_revocation(self):
        payload = self._login().json()["data"]["session"]
        scope = {
            "headers": [(b"authorization", f"Bearer {payload['access_token']}".encode())],
            "query_string": b"token=lf_a_wrong",
        }
        self.assertEqual(ws_auth._extract_token(scope), payload["access_token"])
        resolved = ws_auth._get_user_by_token.func(payload["access_token"])
        self.assertEqual(resolved, self.user)

        AuthSession = _session_model(self)
        AuthSession.objects.update(revoked_at=timezone.now())
        self.assertIsNone(ws_auth._get_user_by_token.func(payload["access_token"]))

    @override_settings(AUTH_WS_QUERY_TOKEN_ENABLED=False)
    def test_ws_query_fallback_can_be_disabled(self):
        self.assertIsNone(
            ws_auth._extract_token(
                {"headers": [], "query_string": b"token=legacy-or-opaque"}
            )
        )


@override_settings(
    AUTH_ACCESS_TOKEN_TTL_SECONDS=900,
    AUTH_REFRESH_TOKEN_TTL_SECONDS=30 * 24 * 3600,
)
class ConcurrentRefreshTests(TransactionTestCase):
    reset_sequences = True

    def test_only_one_concurrent_refresh_can_rotate_a_credential(self):
        if not connection.features.has_select_for_update:
            self.skipTest("database does not support SELECT FOR UPDATE")
        user = LocalUser.objects.create(openid="concurrent-user")
        issued = auth.create_auth_session(user)
        barrier = Barrier(2)

        def rotate():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                auth.refresh_auth_session(issued.refresh_token)
                return "ok"
            except auth.RefreshTokenRejected:
                return "rejected"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _index: rotate(), range(2)))
        self.assertEqual(sorted(results), ["ok", "rejected"])
        session = _session_model(self).objects.get(id=issued.session.id)
        self.assertIsNotNone(session.revoked_at)


class AuthSessionAdminTests(TestCase):
    def test_change_view_does_not_render_token_hashes(self):
        admin_user = get_user_model().objects.create_superuser(
            username="auth-admin",
            email="admin@example.com",
            password="admin-password",
        )
        local_user = LocalUser.objects.create(openid="admin-session-user")
        AuthSession = _session_model(self)
        access_hash = "a" * 64
        refresh_hash = "b" * 64
        now = timezone.now()
        session = AuthSession.objects.create(
            user=local_user,
            access_token_hash=access_hash,
            access_expires_at=now + timedelta(minutes=15),
            refresh_expires_at=now + timedelta(days=30),
        )
        apps.get_model("users", "AuthRefreshToken").objects.create(
            session=session,
            token_hash=refresh_hash,
            expires_at=now + timedelta(days=30),
        )
        self.client.force_login(admin_user)

        response = self.client.get(
            reverse("admin:users_authsession_change", args=[session.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, access_hash)
        self.assertNotContains(response, refresh_hash)


class LocalUserAdminPasswordHashTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username="local-user-admin",
            email="local-admin@example.com",
            password="admin-password",
        )
        self.local_user = LocalUser.objects.create(
            openid="admin-local-user",
            password_hash="pbkdf2_sha256$hidden-password-digest",
        )
        self.client.force_login(self.admin_user)

    def test_registry_fields_exclude_password_hash(self):
        request = APIRequestFactory().get("/django/admin/users/localuser/")
        request.user = self.admin_user
        model_admin = admin.site._registry[LocalUser]
        self.assertNotIn("password_hash", model_admin.get_fields(request, self.local_user))

    def test_add_and_change_html_never_render_password_hash(self):
        add_response = self.client.get(reverse("admin:users_localuser_add"))
        change_response = self.client.get(
            reverse("admin:users_localuser_change", args=[self.local_user.id])
        )
        self.assertEqual(add_response.status_code, 200)
        self.assertEqual(change_response.status_code, 200)
        for response in (add_response, change_response):
            self.assertNotContains(response, "password_hash")
            self.assertNotContains(response, self.local_user.password_hash)


class ProductionAuthSettingsTests(SimpleTestCase):
    def _load_settings(
        self,
        django_env="pro",
        env_file=None,
        load_env_file="0",
        **auth_env,
    ):
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("AUTH_") and key != "CHAT_ENABLE_WS"
        }
        env.update(
            {
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "test-only-production-secret",
                "DJANGO_ALLOWED_HOSTS": "example.com",
                "DB_ENGINE": "sqlite",
                "CHAT_ENABLE_WS": "0",
                "DJANGO_LOAD_ENV_FILE": load_env_file,
                "DJANGO_ENV_FILE": os.path.join(
                    os.environ.get("TEMP", "."), "missing-local-flavor-env-file"
                ),
                **auth_env,
            }
        )
        if django_env is not None:
            env["DJANGO_ENV"] = django_env
        else:
            env.pop("DJANGO_ENV", None)
        if env_file is not None:
            env["DJANGO_ENV_FILE"] = env_file
        return subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json; from config import settings; "
                    "print(json.dumps({"
                    "'legacy': settings.AUTH_LEGACY_TOKEN_ENABLED, "
                    "'query': settings.AUTH_WS_QUERY_TOKEN_ENABLED, "
                    "'env': settings.DJANGO_ENV, 'debug': settings.DEBUG, "
                    "'hosts': settings.ALLOWED_HOSTS}))"
                ),
            ],
            cwd=str(settings.BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_production_requires_explicit_compatibility_switches(self):
        missing = self._load_settings()
        self.assertNotEqual(missing.returncode, 0)
        closed = self._load_settings(
            AUTH_LEGACY_TOKEN_ENABLED="0",
            AUTH_WS_QUERY_TOKEN_ENABLED="0",
        )
        self.assertEqual(closed.returncode, 0, closed.stderr)
        payload = json.loads(closed.stdout.strip())
        self.assertFalse(payload["legacy"])
        self.assertFalse(payload["query"])

    def test_prod_alias_is_safe_and_unknown_environment_is_rejected(self):
        prod = self._load_settings(
            django_env="prod",
            AUTH_LEGACY_TOKEN_ENABLED="0",
            AUTH_WS_QUERY_TOKEN_ENABLED="0",
        )
        self.assertEqual(prod.returncode, 0, prod.stderr)
        payload = json.loads(prod.stdout.strip())
        self.assertEqual(payload["env"], "pro")
        self.assertFalse(payload["debug"])
        self.assertNotEqual(payload["hosts"], ["*"])

        typo = self._load_settings(
            django_env="prdo",
            AUTH_LEGACY_TOKEN_ENABLED="0",
            AUTH_WS_QUERY_TOKEN_ENABLED="0",
        )
        self.assertNotEqual(typo.returncode, 0)

    def test_production_legacy_requires_valid_future_utc_cutoff(self):
        missing = self._load_settings(
            AUTH_LEGACY_TOKEN_ENABLED="1", AUTH_WS_QUERY_TOKEN_ENABLED="0"
        )
        naive = self._load_settings(
            AUTH_LEGACY_TOKEN_ENABLED="1",
            AUTH_WS_QUERY_TOKEN_ENABLED="0",
            AUTH_LEGACY_TOKEN_ACCEPT_UNTIL="2030-01-01T00:00:00",
        )
        past = self._load_settings(
            AUTH_LEGACY_TOKEN_ENABLED="1",
            AUTH_WS_QUERY_TOKEN_ENABLED="0",
            AUTH_LEGACY_TOKEN_ACCEPT_UNTIL="2020-01-01T00:00:00+00:00",
        )
        too_far = self._load_settings(
            AUTH_LEGACY_TOKEN_ENABLED="1",
            AUTH_WS_QUERY_TOKEN_ENABLED="0",
            AUTH_LEGACY_TOKEN_ACCEPT_UNTIL=(
                datetime.now(datetime_timezone.utc) + timedelta(days=91)
            ).isoformat(),
        )
        for result in (missing, naive, past, too_far):
            self.assertNotEqual(result.returncode, 0)

        valid = self._load_settings(
            AUTH_LEGACY_TOKEN_ENABLED="1",
            AUTH_WS_QUERY_TOKEN_ENABLED="0",
            AUTH_LEGACY_TOKEN_ACCEPT_UNTIL=(
                datetime.now(datetime_timezone.utc) + timedelta(days=30)
            ).isoformat(),
        )
        self.assertEqual(valid.returncode, 0, valid.stderr)

    def test_production_ws_query_fallback_requires_bounded_legacy_window(self):
        result = self._load_settings(AUTH_WS_QUERY_TOKEN_ENABLED="1")
        self.assertNotEqual(result.returncode, 0)

    def test_auth_numeric_settings_require_positive_decimal_integers(self):
        names = (
            "AUTH_TOKEN_TTL_SECONDS",
            "AUTH_ACCESS_TOKEN_TTL_SECONDS",
            "AUTH_REFRESH_TOKEN_TTL_SECONDS",
            "AUTH_SESSION_LAST_SEEN_INTERVAL_SECONDS",
            "AUTH_LEGACY_MAX_WINDOW_SECONDS",
        )
        for name in names:
            for invalid in ("0", "-1", "abc", "1.5", ""):
                with self.subTest(name=name, invalid=invalid):
                    result = self._load_settings(
                        AUTH_LEGACY_TOKEN_ENABLED="0",
                        AUTH_WS_QUERY_TOKEN_ENABLED="0",
                        **{name: invalid},
                    )
                    self.assertNotEqual(result.returncode, 0)

    def test_auth_switches_only_accept_zero_or_one(self):
        for name in (
            "AUTH_LEGACY_TOKEN_ENABLED",
            "AUTH_WS_QUERY_TOKEN_ENABLED",
        ):
            for invalid in ("true", "yes", "", "2", "-1"):
                with self.subTest(name=name, invalid=invalid):
                    env = {
                        "AUTH_LEGACY_TOKEN_ENABLED": "0",
                        "AUTH_WS_QUERY_TOKEN_ENABLED": "0",
                    }
                    env[name] = invalid
                    result = self._load_settings(**env)
                    self.assertNotEqual(result.returncode, 0)

    def test_explicit_env_file_environment_is_reparsed_strictly(self):
        with tempfile.TemporaryDirectory() as directory:
            for alias in ("pro", "prod", "production"):
                file_path = os.path.join(directory, f"env-{alias}")
                with open(file_path, "w", encoding="utf-8") as handle:
                    handle.write(f"DJANGO_ENV={alias}\n")
                result = self._load_settings(
                    django_env=None,
                    env_file=file_path,
                    load_env_file="1",
                    AUTH_LEGACY_TOKEN_ENABLED="0",
                    AUTH_WS_QUERY_TOKEN_ENABLED="0",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout.strip())
                self.assertEqual(payload["env"], "pro")
                self.assertFalse(payload["debug"])
                self.assertNotEqual(payload["hosts"], ["*"])

            invalid_path = os.path.join(directory, "env-invalid")
            with open(invalid_path, "w", encoding="utf-8") as handle:
                handle.write("DJANGO_ENV=prdo\n")
            invalid = self._load_settings(
                django_env=None,
                env_file=invalid_path,
                load_env_file="1",
                AUTH_LEGACY_TOKEN_ENABLED="0",
                AUTH_WS_QUERY_TOKEN_ENABLED="0",
            )
            self.assertNotEqual(invalid.returncode, 0)

    def test_process_environment_has_priority_over_explicit_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = os.path.join(directory, "env-pro")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("DJANGO_ENV=pro\n")
            result = self._load_settings(
                django_env="dev",
                env_file=file_path,
                load_env_file="1",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout.strip())["env"], "dev")

    def test_env_file_loading_switch_is_strict_and_zero_isolated(self):
        isolated = self._load_settings(
            load_env_file="0",
            AUTH_LEGACY_TOKEN_ENABLED="0",
            AUTH_WS_QUERY_TOKEN_ENABLED="0",
        )
        self.assertEqual(isolated.returncode, 0, isolated.stderr)
        for invalid in ("true", "yes", "", "2", "-1"):
            with self.subTest(invalid=invalid):
                result = self._load_settings(
                    load_env_file=invalid,
                    AUTH_LEGACY_TOKEN_ENABLED="0",
                    AUTH_WS_QUERY_TOKEN_ENABLED="0",
                )
                self.assertNotEqual(result.returncode, 0)

    def test_explicit_env_file_must_exist_and_be_regular_file(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = self._load_settings(
                env_file=os.path.join(directory, "missing.env"),
                load_env_file="1",
                AUTH_LEGACY_TOKEN_ENABLED="0",
                AUTH_WS_QUERY_TOKEN_ENABLED="0",
            )
            is_directory = self._load_settings(
                env_file=directory,
                load_env_file="1",
                AUTH_LEGACY_TOKEN_ENABLED="0",
                AUTH_WS_QUERY_TOKEN_ENABLED="0",
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertNotEqual(is_directory.returncode, 0)


@override_settings(
    CHAT_ENABLE_WS=True,
    AUTH_WS_QUERY_TOKEN_ENABLED=True,
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)
class WebSocketSessionContinuityTests(TransactionTestCase):
    def setUp(self):
        self.user = LocalUser.objects.create(openid="lf_a_ws-session-user")
        peer = LocalUser.objects.create(openid="ws-session-peer")
        self.conversation = Conversation.objects.create(
            participant_low=self.user,
            participant_high=peer,
            context_key=Conversation.CONTEXT_GLOBAL,
        )
        ConversationMember.objects.create(
            conversation=self.conversation,
            user=self.user,
        )
        self.credentials = auth.create_auth_session(self.user)
        self.application = ws_auth.TokenAuthMiddleware(
            URLRouter(
                [
                    re_path(
                        r"^ws/chat/conversations/(?P<conversation_id>\d+)/?$",
                        ConversationConsumer.as_asgi(),
                    )
                ]
            )
        )

    def _communicator(self, credentials=None, source="header"):
        credentials = credentials or self.credentials
        path = f"/ws/chat/conversations/{self.conversation.id}/"
        headers = None
        if source == "query":
            path += f"?token={credentials.access_token}"
        else:
            headers = [(b"authorization", f"Bearer {credentials.access_token}".encode())]
        return WebsocketCommunicator(
            self.application,
            path,
            headers=headers,
        )

    def test_opaque_access_token_in_query_is_rejected(self):
        async def scenario():
            communicator = self._communicator(source="query")
            connected, _subprotocol = await communicator.connect()
            self.assertFalse(connected)

        async_to_sync(scenario)()

    def test_opaque_access_token_in_authorization_header_is_accepted(self):
        async def scenario():
            communicator = self._communicator(source="header")
            connected, _subprotocol = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_legacy_token_that_starts_with_opaque_prefix_is_accepted_in_query(self):
        legacy_token = auth.issue_token(self.user.openid)
        self.assertTrue(legacy_token.startswith("lf_a_"))
        self.assertIsNone(auth.resolve_auth_token(legacy_token).session)

        async def scenario():
            path = f"/ws/chat/conversations/{self.conversation.id}/?token={legacy_token}"
            communicator = WebsocketCommunicator(self.application, path)
            connected, _subprotocol = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_revoked_session_closes_before_delivering_group_push(self):
        async def scenario():
            communicator = self._communicator()
            connected, _subprotocol = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()
            await database_sync_to_async(
                lambda: _session_model(self).objects.filter(
                    id=self.credentials.session.id
                ).update(revoked_at=timezone.now())
            )()
            await get_channel_layer().group_send(
                f"chat.conversation.{self.conversation.id}",
                {"type": "chat_event", "payload": {"event": "secret.push"}},
            )
            output = await communicator.receive_output(timeout=2)
            self.assertEqual(output["type"], "websocket.close")
            self.assertEqual(output["code"], 4401)

        async_to_sync(scenario)()

    def test_expired_access_closes_before_processing_next_inbound_event(self):
        async def scenario():
            communicator = self._communicator()
            connected, _subprotocol = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()
            await database_sync_to_async(
                lambda: _session_model(self).objects.filter(
                    id=self.credentials.session.id
                ).update(access_expires_at=timezone.now() - timedelta(seconds=1))
            )()
            await communicator.send_json_to({"event": "ping"})
            output = await communicator.receive_output(timeout=2)
            self.assertEqual(output["type"], "websocket.close")
            self.assertEqual(output["code"], 4401)

        async_to_sync(scenario)()

    def test_query_connection_closes_when_migration_cutoff_passes(self):
        legacy_token = auth.issue_token(self.user.openid)

        async def scenario():
            communicator = WebsocketCommunicator(
                self.application,
                f"/ws/chat/conversations/{self.conversation.id}/?token={legacy_token}",
            )
            connected, _subprotocol = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()
            with override_settings(
                AUTH_LEGACY_TOKEN_ENABLED=True,
                AUTH_LEGACY_TOKEN_ACCEPT_UNTIL="2020-01-01T00:00:00+00:00",
            ):
                await communicator.send_json_to({"event": "ping"})
                output = await communicator.receive_output(timeout=2)
            self.assertEqual(output["type"], "websocket.close")
            self.assertEqual(output["code"], 4401)

        async_to_sync(scenario)()

    def test_header_connection_is_not_closed_by_query_cutoff(self):
        async def scenario():
            communicator = self._communicator(source="header")
            connected, _subprotocol = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()
            with override_settings(
                AUTH_LEGACY_TOKEN_ENABLED=True,
                AUTH_LEGACY_TOKEN_ACCEPT_UNTIL="2020-01-01T00:00:00+00:00",
            ):
                await communicator.send_json_to({"event": "ping"})
                payload = await communicator.receive_json_from(timeout=2)
            self.assertEqual(payload, {"event": "pong"})
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_refresh_invalidates_existing_socket_and_successor_can_reconnect(self):
        async def scenario():
            old_socket = self._communicator(source="header")
            connected, _subprotocol = await old_socket.connect()
            self.assertTrue(connected)
            await old_socket.receive_json_from()
            successor = await database_sync_to_async(auth.refresh_auth_session)(
                self.credentials.refresh_token
            )
            await old_socket.send_json_to({"event": "ping"})
            closed = await old_socket.receive_output(timeout=2)
            self.assertEqual(closed["type"], "websocket.close")
            self.assertEqual(closed["code"], 4401)

            new_socket = self._communicator(successor, source="header")
            reconnected, _subprotocol = await new_socket.connect()
            self.assertTrue(reconnected)
            await new_socket.receive_json_from()
            await new_socket.disconnect()

        async_to_sync(scenario)()


@override_settings(ALLOWED_HOSTS=["chat.example.test"])
class WebSocketOriginAdmissionTests(SimpleTestCase):
    def test_asgi_wraps_token_authentication_with_origin_admission(self):
        asgi_source = (Path(__file__).resolve().parent.parent / "config" / "asgi.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("WebSocketOriginAuthValidator(", asgi_source)

    def _application(self, received_scopes):
        validator = getattr(ws_auth, "WebSocketOriginAuthValidator", None)
        self.assertIsNotNone(
            validator,
            "WebSocket connections require an origin/no-origin admission wrapper",
        )

        async def inner(scope, receive, send):
            received_scopes.append(scope)
            await send({"type": "websocket.accept"})

        return validator(inner)

    def test_allowed_browser_origin_reaches_inner_application(self):
        received_scopes = []

        async def scenario():
            communicator = WebsocketCommunicator(
                self._application(received_scopes),
                "/ws/chat/conversations/1/",
                headers=[(b"origin", b"https://chat.example.test")],
            )
            connected, _subprotocol = await communicator.connect()
            self.assertTrue(connected)
            self.assertEqual(len(received_scopes), 1)
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_disallowed_browser_origin_is_rejected_before_inner_application(self):
        received_scopes = []

        async def scenario():
            communicator = WebsocketCommunicator(
                self._application(received_scopes),
                "/ws/chat/conversations/1/",
                headers=[(b"origin", b"https://attacker.example")],
            )
            connected, _subprotocol = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(received_scopes, [])

        async_to_sync(scenario)()

    def test_no_origin_bearer_header_reaches_inner_application(self):
        received_scopes = []

        async def scenario():
            communicator = WebsocketCommunicator(
                self._application(received_scopes),
                "/ws/chat/conversations/1/",
                headers=[(b"authorization", b"Bearer opaque-access-token")],
            )
            connected, _subprotocol = await communicator.connect()
            self.assertTrue(connected)
            self.assertEqual(len(received_scopes), 1)
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_no_origin_query_token_is_rejected_before_inner_application(self):
        received_scopes = []

        async def scenario():
            communicator = WebsocketCommunicator(
                self._application(received_scopes),
                "/ws/chat/conversations/1/?token=legacy-token",
            )
            connected, _subprotocol = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(received_scopes, [])

        async_to_sync(scenario)()


class AuthMigrationRoundTripTests(TransactionTestCase):
    reset_sequences = True

    def test_final_auth_migration_round_trips_with_existing_local_user(self):
        initial_targets = MigrationExecutor(connection).loader.graph.leaf_nodes("users")
        cleanup_ran = False
        body_error = None
        body_traceback = None
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([("users", "0005_userpreferencesnapshot")])
            old_apps = executor.loader.project_state(
                [("users", "0005_userpreferencesnapshot")]
            ).apps
            old_apps.get_model("users", "LocalUser").objects.create(
                openid="migration-existing-user"
            )

            executor = MigrationExecutor(connection)
            executor.migrate([("users", "0006_authsession")])
            final_apps = executor.loader.project_state(
                [("users", "0006_authsession")]
            ).apps
            user = final_apps.get_model("users", "LocalUser").objects.get(
                openid="migration-existing-user"
            )
            session = final_apps.get_model("users", "AuthSession").objects.create(
                user_id=user.id,
                access_token_hash="c" * 64,
                access_expires_at=timezone.now() + timedelta(minutes=15),
                refresh_expires_at=timezone.now() + timedelta(days=30),
            )
            final_apps.get_model("users", "AuthRefreshToken").objects.create(
                session_id=session.id,
                token_hash="d" * 64,
                expires_at=session.refresh_expires_at,
            )

            executor = MigrationExecutor(connection)
            executor.migrate([("users", "0005_userpreferencesnapshot")])
            self.assertNotIn("auth_sessions", connection.introspection.table_names())
            self.assertNotIn(
                "auth_refresh_tokens", connection.introspection.table_names()
            )

            executor = MigrationExecutor(connection)
            executor.migrate([("users", "0006_authsession")])
            tables = connection.introspection.table_names()
            self.assertIn("auth_sessions", tables)
            self.assertIn("auth_refresh_tokens", tables)
            final_apps = executor.loader.project_state(
                [("users", "0006_authsession")]
            ).apps
            self.assertTrue(
                final_apps.get_model("users", "LocalUser").objects.filter(
                    openid="migration-existing-user"
                ).exists()
            )
        except BaseException as exc:
            body_error = exc
            body_traceback = exc.__traceback__
        finally:
            try:
                MigrationExecutor(connection).migrate(initial_targets)
                cleanup_ran = True
            except BaseException as cleanup_error:
                if body_error is not None:
                    raise RuntimeError(
                        "Migration test body and cleanup both failed; "
                        f"body={body_error!r}"
                    ) from cleanup_error
                raise
        if body_error is not None:
            raise body_error.with_traceback(body_traceback)
        self.assertTrue(cleanup_ran)
