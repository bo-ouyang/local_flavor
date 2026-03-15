from rest_framework import serializers

from users.models import LocalUser


class LocalUserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalUser
        fields = [
            "id",
            "nickname",
            "avatar",
            "is_verified",
            "region_code",
            "province",
            "city",
            "last_region_update",
            "created_at",
        ]


class UserRegionUpdateSerializer(serializers.Serializer):
    region_code = serializers.CharField(required=False, allow_blank=True, max_length=20)
    province = serializers.CharField(required=False, allow_blank=True, max_length=64)
    city = serializers.CharField(required=False, allow_blank=True, max_length=64)
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)

    def validate(self, attrs):
        province = (attrs.get("province") or "").strip()
        city = (attrs.get("city") or "").strip()
        has_manual_region = bool(province and city)
        has_coordinates = attrs.get("latitude") is not None and attrs.get("longitude") is not None
        if not has_manual_region and not has_coordinates:
            raise serializers.ValidationError(
                "provide province/city or latitude/longitude"
            )
        return attrs


class WechatLoginSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=1, max_length=256)
    nickname = serializers.CharField(required=False, allow_blank=True, max_length=64)
    avatar = serializers.CharField(required=False, allow_blank=True, max_length=255)
    province = serializers.CharField(required=False, allow_blank=True, max_length=64)
    city = serializers.CharField(required=False, allow_blank=True, max_length=64)
    region_code = serializers.CharField(required=False, allow_blank=True, max_length=20)
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)


class PhoneLoginSerializer(serializers.Serializer):
    phone = serializers.RegexField(regex=r"^1\d{10}$", max_length=20)
    password = serializers.CharField(min_length=6, max_length=64)
