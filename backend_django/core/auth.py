from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as datetime_timezone
import hashlib
import math
import secrets
from typing import Optional

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import APIException, AuthenticationFailed, NotAuthenticated

from users.models import AuthRefreshToken, AuthSession, LocalUser


_signer = TimestampSigner(salt="local-flavor-auth")


@dataclass(frozen=True)
class IssuedSessionCredentials:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    session: AuthSession

    @property
    def expires_in(self) -> int:
        return max(
            0,
            math.ceil((self.access_expires_at - timezone.now()).total_seconds()),
        )


@dataclass(frozen=True)
class AuthTokenResolution:
    user: LocalUser
    session: AuthSession | None
    is_legacy: bool = False


class RefreshTokenRejected(APIException):
    status_code = 401
    default_detail = "Invalid or expired refresh token"
    default_code = "invalid_refresh_token"


def extract_bearer_token(request) -> Optional[str]:
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def issue_token(openid: str) -> str:
    """Issue a legacy signed token for the bounded migration window only."""
    return _signer.sign(openid)


def resolve_openid_from_token(token: str) -> Optional[str]:
    token_ttl_seconds = int(
        getattr(settings, "AUTH_TOKEN_TTL_SECONDS", 30 * 24 * 3600)
    )
    if not token or ":" not in token:
        return None
    try:
        return str(_signer.unsign(token, max_age=token_ttl_seconds))
    except (BadSignature, SignatureExpired):
        return None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_token(prefix: str) -> str:
    return f"{prefix}{secrets.token_urlsafe(32)}"


def _ttl_seconds(setting_name: str, default: int) -> int:
    value = int(getattr(settings, setting_name, default))
    if value <= 0:
        raise ImproperlyConfigured(f"{setting_name} must be greater than zero")
    return value


@transaction.atomic
def create_auth_session(
    user: LocalUser,
    *,
    device_label: str = "",
) -> IssuedSessionCredentials:
    now = timezone.now()
    refresh_expires_at = now + timedelta(
        seconds=_ttl_seconds("AUTH_REFRESH_TOKEN_TTL_SECONDS", 30 * 24 * 3600)
    )
    access_expires_at = min(
        now
        + timedelta(
            seconds=_ttl_seconds("AUTH_ACCESS_TOKEN_TTL_SECONDS", 15 * 60)
        ),
        refresh_expires_at,
    )
    access_token = _new_token("lf_a_")
    refresh_token = _new_token("lf_r_")
    session = AuthSession.objects.create(
        user=user,
        access_token_hash=_hash_token(access_token),
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
        last_seen_at=now,
        device_label=(device_label or "").strip()[:120],
    )
    AuthRefreshToken.objects.create(
        session=session,
        token_hash=_hash_token(refresh_token),
        expires_at=refresh_expires_at,
    )
    return IssuedSessionCredentials(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
        session=session,
    )


def refresh_auth_session(refresh_token: str) -> IssuedSessionCredentials:
    if not refresh_token or not refresh_token.startswith("lf_r_"):
        raise RefreshTokenRejected()
    token_hash = _hash_token(refresh_token)
    rejected = False
    with transaction.atomic():
        credential = (
            AuthRefreshToken.objects.select_for_update()
            .filter(token_hash=token_hash)
            .first()
        )
        if credential is None:
            raise RefreshTokenRejected()

        session = (
            AuthSession.objects.select_for_update()
            .select_related("user")
            .get(id=credential.session_id)
        )
        now = timezone.now()
        if credential.used_at is not None:
            if session.revoked_at is None:
                session.revoked_at = now
                session.save(update_fields=["revoked_at", "updated_at"])
            rejected = True
        elif (
            session.revoked_at is not None
            or credential.expires_at <= now
            or session.refresh_expires_at <= now
        ):
            rejected = True
        else:
            access_token = _new_token("lf_a_")
            rotated_refresh_token = _new_token("lf_r_")
            access_expires_at = min(
                now
                + timedelta(
                    seconds=_ttl_seconds("AUTH_ACCESS_TOKEN_TTL_SECONDS", 15 * 60)
                ),
                session.refresh_expires_at,
            )
            successor = AuthRefreshToken.objects.create(
                session=session,
                token_hash=_hash_token(rotated_refresh_token),
                expires_at=session.refresh_expires_at,
            )
            credential.used_at = now
            credential.successor = successor
            credential.save(update_fields=["used_at", "successor"])
            session.access_token_hash = _hash_token(access_token)
            session.access_expires_at = access_expires_at
            session.last_seen_at = now
            session.save(
                update_fields=[
                    "access_token_hash",
                    "access_expires_at",
                    "last_seen_at",
                    "updated_at",
                ]
            )
    if rejected:
        raise RefreshTokenRejected()
    return IssuedSessionCredentials(
        access_token=access_token,
        refresh_token=rotated_refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=session.refresh_expires_at,
        session=session,
    )


def legacy_tokens_allowed(now: datetime) -> bool:
    if not bool(getattr(settings, "AUTH_LEGACY_TOKEN_ENABLED", False)):
        return False
    raw_cutoff = str(getattr(settings, "AUTH_LEGACY_TOKEN_ACCEPT_UNTIL", "") or "").strip()
    if not raw_cutoff:
        return True
    cutoff = parse_datetime(raw_cutoff)
    if cutoff is None:
        return False
    if timezone.is_naive(cutoff):
        cutoff = timezone.make_aware(cutoff, datetime_timezone.utc)
    return now < cutoff


def resolve_auth_token(token: str | None) -> AuthTokenResolution | None:
    if not token:
        return None
    now = timezone.now()
    if token.startswith("lf_a_"):
        session = (
            AuthSession.objects.select_related("user")
            .filter(
                access_token_hash=_hash_token(token),
                revoked_at__isnull=True,
                access_expires_at__gt=now,
                refresh_expires_at__gt=now,
            )
            .first()
        )
        if session is not None:
            last_seen_interval = _ttl_seconds("AUTH_SESSION_LAST_SEEN_INTERVAL_SECONDS", 300)
            threshold = now - timedelta(seconds=last_seen_interval)
            if session.last_seen_at is None or session.last_seen_at < threshold:
                AuthSession.objects.filter(id=session.id).filter(
                    Q(last_seen_at__isnull=True) | Q(last_seen_at__lt=threshold)
                ).update(last_seen_at=now, updated_at=now)
                session.last_seen_at = now
            return AuthTokenResolution(user=session.user, session=session)

    if not legacy_tokens_allowed(now):
        return None
    openid = resolve_openid_from_token(token)
    if not openid:
        return None
    user = LocalUser.objects.filter(openid=openid).first()
    if user is None:
        return None
    return AuthTokenResolution(user=user, session=None, is_legacy=True)


class OpaqueSessionAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        raw_header = get_authorization_header(request).split()
        if not raw_header:
            return None
        if raw_header[0].lower() != self.keyword.lower().encode():
            return None
        if len(raw_header) != 2:
            raise AuthenticationFailed("Invalid Authorization header")
        try:
            token = raw_header[1].decode("utf-8")
        except UnicodeError as exc:
            raise AuthenticationFailed("Invalid Authorization header") from exc
        resolution = resolve_auth_token(token)
        if resolution is None:
            raise AuthenticationFailed("Invalid or expired token")
        return resolution.user, resolution.session

    def authenticate_header(self, request):
        return self.keyword


def get_current_user(request, required: bool = True) -> Optional[LocalUser]:
    request_user = getattr(request, "user", None)
    if isinstance(request_user, LocalUser):
        return request_user

    token = extract_bearer_token(request)
    if not token:
        if required:
            raise NotAuthenticated("Authentication credentials were not provided.")
        return None

    resolution = resolve_auth_token(token)
    if resolution is None:
        if required:
            raise NotAuthenticated("Invalid or expired token")
        return None
    return resolution.user
