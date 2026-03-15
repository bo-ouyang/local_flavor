from datetime import timedelta

from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from core.auth import get_current_user
from core.auth import issue_token
from core.geolocation import reverse_geocode
from core.responses import api_success
from core.throttles import LoginRateThrottle
from core.wechat import code2session
from users.models import LocalUser, Region
from users.serializers import (
    LocalUserReadSerializer,
    PhoneLoginSerializer,
    UserRegionUpdateSerializer,
    WechatLoginSerializer,
)
from items.tasks import sync_user_preference_task


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

        token = issue_token(openid)
        data = {
            "access_token": token,
            "token_type": "bearer",
            "user": LocalUserReadSerializer(user).data,
        }
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

        token = issue_token(user.openid)
        data = {
            "access_token": token,
            "token_type": "bearer",
            "user": LocalUserReadSerializer(user).data,
        }
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
