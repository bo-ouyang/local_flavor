from datetime import timedelta

from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.views import APIView

from core.auth import (
    create_auth_session,
    get_current_user,
    issue_token,
    legacy_tokens_allowed,
    refresh_auth_session,
)
from core.geolocation import reverse_geocode
from core.responses import api_success
from core.throttles import LoginRateThrottle
from core.wechat import code2session
from users.models import AuthSession, LocalUser, Region
from users.serializers import (
    AuthSessionReadSerializer,
    LocalUserReadSerializer,
    PhoneLoginSerializer,
    RefreshSessionSerializer,
    UserRegionUpdateSerializer,
    WechatLoginSerializer,
)
from items.tasks import sync_user_preference_task


def _session_credential_payload(credentials):
    return {
        "access_token": credentials.access_token,
        "refresh_token": credentials.refresh_token,
        "token_type": "bearer",
        "expires_in": credentials.expires_in,
        "access_expires_at": credentials.access_expires_at,
        "refresh_expires_at": credentials.refresh_expires_at,
        "session_id": credentials.session.id,
    }


def _login_credential_payload(credentials, user):
    data = {
        "token_type": "bearer",
        "user": LocalUserReadSerializer(user).data,
        "session": _session_credential_payload(credentials),
    }
    if legacy_tokens_allowed(timezone.now()):
        legacy_token = issue_token(user.openid)
        # AUTH-01A migration bridge: the current frontend reads access_token.
        data["access_token"] = legacy_token
        data["token"] = legacy_token
    return data


def _current_auth_session(request) -> AuthSession:
    session = request.auth if isinstance(request.auth, AuthSession) else None
    if session is None:
        raise PermissionDenied(
            "Legacy credentials cannot manage sessions; sign in again first"
        )
    return session


def _resolve_region_code(province: str, city: str, fallback: str = "") -> str:
    if city:
        city_row = (
            Region.objects.filter(name=city)
            .order_by("level")
            .only("code")
            .first()
        )
        if city_row:
            return city_row.code
    if province:
        province_row = (
            Region.objects.filter(name=province)
            .order_by("level")
            .only("code")
            .first()
        )
        if province_row:
            return province_row.code
    return fallback or ""


class WechatLoginView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = WechatLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = code2session(serializer.validated_data["code"])
        openid = session["openid"]

        defaults = {
            "nickname": serializer.validated_data.get("nickname") or "",
            "avatar": serializer.validated_data.get("avatar") or "",
            "province": serializer.validated_data.get("province") or "",
            "city": serializer.validated_data.get("city") or "",
            "region_code": serializer.validated_data.get("region_code") or "",
            "latitude": serializer.validated_data.get("latitude"),
            "longitude": serializer.validated_data.get("longitude"),
            "is_verified": True,
        }
        user, created = LocalUser.objects.get_or_create(openid=openid, defaults=defaults)
        if not created:
            changed = False
            for field in (
                "nickname",
                "avatar",
                "province",
                "city",
                "region_code",
                "latitude",
                "longitude",
            ):
                value = serializer.validated_data.get(field)
                if value is not None and value != "":
                    setattr(user, field, value)
                    changed = True
            if changed:
                user.save()

        credentials = create_auth_session(
            user,
            device_label=serializer.validated_data.get("device_label", ""),
        )
        data = _login_credential_payload(credentials, user)
        return api_success(data=data, message="login success", status_code=status.HTTP_200_OK)


class PhoneLoginView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        password = serializer.validated_data["password"]

        user = LocalUser.objects.filter(phone=phone).first()
        if not user or not user.password_hash:
            raise ValidationError({"detail": "invalid phone or password"})
        if not check_password(password, user.password_hash):
            raise ValidationError({"detail": "invalid phone or password"})

        credentials = create_auth_session(
            user,
            device_label=serializer.validated_data.get("device_label", ""),
        )
        data = _login_credential_payload(credentials, user)
        return api_success(data=data, message="login success", status_code=status.HTTP_200_OK)


class MeView(APIView):
    def get(self, request):
        user = get_current_user(request, required=True)
        return api_success(data=LocalUserReadSerializer(user).data)


class RegionUpdateView(APIView):
    def put(self, request):
        user = get_current_user(request, required=True)
        serializer = UserRegionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        now = timezone.now()
        if user.last_region_update and (now - user.last_region_update) < timedelta(days=30):
            remaining_days = 30 - (now - user.last_region_update).days
            raise ValidationError(
                {"detail": f"Region update is on cooldown. Try again in {remaining_days} days."}
            )

        latitude = validated.get("latitude")
        longitude = validated.get("longitude")
        province = (validated.get("province") or "").strip()
        city = (validated.get("city") or "").strip()
        region_code = (validated.get("region_code") or "").strip()

        if latitude is not None and longitude is not None:
            try:
                geo = reverse_geocode(float(latitude), float(longitude))
            except Exception as exc:
                raise ValidationError({"detail": "Failed to resolve location from coordinates"}) from exc
            province = (geo.get("province") or province).strip()
            city = (geo.get("city") or city).strip()

        if not province or not city:
            raise ValidationError({"detail": "province/city is required"})

        user.region_code = _resolve_region_code(province, city, fallback=region_code or user.region_code or "")
        user.province = province
        user.city = city
        user.last_region_update = now
        update_fields = ["region_code", "province", "city", "last_region_update"]
        if latitude is not None and longitude is not None:
            user.latitude = latitude
            user.longitude = longitude
            update_fields.extend(["latitude", "longitude"])
        user.save(update_fields=update_fields)
        
        # Trigger recommendation preference sync
        sync_user_preference_task.delay(user.id)

        return api_success(data=LocalUserReadSerializer(user).data, message="region updated")


class SessionRefreshView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = RefreshSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credentials = refresh_auth_session(serializer.validated_data["refresh_token"])
        return api_success(
            data=_session_credential_payload(credentials),
            message="session refreshed",
        )


class SessionLogoutView(APIView):
    def post(self, request):
        user = get_current_user(request, required=True)
        session = _current_auth_session(request)
        now = timezone.now()
        AuthSession.objects.filter(
            id=session.id,
            user_id=user.id,
            revoked_at__isnull=True,
        ).update(revoked_at=now, updated_at=now)
        return api_success(data={"session_id": session.id}, message="logout success")


class SessionListView(APIView):
    def get(self, request):
        user = get_current_user(request, required=True)
        current_session = _current_auth_session(request)
        sessions = AuthSession.objects.filter(user_id=user.id).order_by("-created_at")
        return api_success(
            data=AuthSessionReadSerializer(
                sessions,
                many=True,
                context={
                    "current_session_id": current_session.id
                },
            ).data
        )


class SessionRevokeView(APIView):
    def post(self, request, session_id: int):
        user = get_current_user(request, required=True)
        _current_auth_session(request)
        session = AuthSession.objects.filter(id=session_id, user_id=user.id).first()
        if session is None:
            raise NotFound("Session not found")
        if session.revoked_at is None:
            session.revoked_at = timezone.now()
            session.save(update_fields=["revoked_at", "updated_at"])
        return api_success(data={"session_id": session.id}, message="session revoked")


class SessionRevokeOthersView(APIView):
    def post(self, request):
        user = get_current_user(request, required=True)
        current_session = _current_auth_session(request)
        now = timezone.now()
        revoked_count = (
            AuthSession.objects.filter(user_id=user.id, revoked_at__isnull=True)
            .exclude(id=current_session.id)
            .update(revoked_at=now, updated_at=now)
        )
        return api_success(
            data={"revoked_count": revoked_count},
            message="other sessions revoked",
        )
