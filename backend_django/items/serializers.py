from rest_framework import serializers

from interactions.models import FlavorTag
from interactions.serializers import FlavorTagReadSerializer
from items.models import Item
from system_config.models import SystemOption
from users.serializers import LocalUserReadSerializer


OPTION_FIELD_TYPE_MAP = {
    "category": "Category",
    "season": "Season",
    "shelf_life": "ShelfLife",
    "portability": "Portability",
}


class ItemCreateSerializer(serializers.ModelSerializer):
    title = serializers.CharField(min_length=2, max_length=128)
    images = serializers.ListField(
        child=serializers.CharField(max_length=500), min_length=1
    )
    initial_tags = serializers.ListField(
        child=serializers.CharField(max_length=64), required=False, default=list
    )

    class Meta:
        model = Item
        fields = [
            "title",
            "description",
            "eat_method",
            "images",
            "category",
            "season",
            "shelf_life",
            "portability",
            "province",
            "city",
            "region_code",
            "initial_tags",
        ]

    def validate_images(self, value):
        cleaned = []
        for img in value:
            if not isinstance(img, str):
                raise serializers.ValidationError("images must be string list")
            url = img.strip()
            if not url:
                continue
            if not (url.startswith("http://") or url.startswith("https://") or url.startswith("/static/")):
                raise serializers.ValidationError("image url must start with http(s):// or /static/")
            cleaned.append(url)
        if not cleaned:
            raise serializers.ValidationError("at least one valid image is required")
        return cleaned

    def validate(self, attrs):
        errors = {}
        for field_name, option_type in OPTION_FIELD_TYPE_MAP.items():
            value = attrs.get(field_name)
            if value is None:
                continue
            exists = SystemOption.objects.filter(type=option_type, value=value).exists()
            if not exists:
                errors[field_name] = f"invalid option `{value}`, configure it in admin SystemOption({option_type})"
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class ItemReadSerializer(serializers.ModelSerializer):
    publisher = LocalUserReadSerializer(source="user", read_only=True)
    flavor_tags = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(read_only=True)
    audit_status = serializers.CharField(read_only=True)
    audit_reason = serializers.CharField(read_only=True)

    class Meta:
        model = Item
        fields = [
            "id",
            "title",
            "description",
            "eat_method",
            "images",
            "category",
            "season",
            "shelf_life",
            "portability",
            "province",
            "city",
            "region_code",
            "created_at",
            "user_id",
            "publisher",
            "flavor_tags",
            "audit_status",
            "audit_reason",
        ]

    def get_flavor_tags(self, obj):
        voted_tag_ids = self.context.get("voted_tag_ids", set())
        if hasattr(obj, "_prefetched_objects_cache") and "flavor_tags" in obj._prefetched_objects_cache:
            tags = obj.flavor_tags.all()
        else:
            tags = FlavorTag.objects.filter(item=obj).all()
        return FlavorTagReadSerializer(
            tags, many=True, context={"voted_tag_ids": voted_tag_ids}
        ).data


class FlavorVotePayloadSerializer(serializers.Serializer):
    tag_name = serializers.CharField(min_length=1, max_length=64)


class ItemListQuerySerializer(serializers.Serializer):
    skip = serializers.IntegerField(min_value=0, required=False, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=100, required=False, default=10)
    region_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    category = serializers.CharField(max_length=32, required=False, allow_blank=True)
    season = serializers.CharField(max_length=32, required=False, allow_blank=True)
    publisher_id = serializers.IntegerField(min_value=1, required=False)
    current_season_only = serializers.BooleanField(required=False, default=False)
    q = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_category(self, value):
        if value and not SystemOption.objects.filter(type="Category", value=value).exists():
            raise serializers.ValidationError("invalid category filter")
        return value

    def validate_season(self, value):
        if value and not SystemOption.objects.filter(type="Season", value=value).exists():
            raise serializers.ValidationError("invalid season filter")
        return value

    def validate_q(self, value):
        return value.strip()


class ItemTodayByRegionQuerySerializer(serializers.Serializer):
    region_limit = serializers.IntegerField(min_value=1, max_value=100, required=False, default=8)
    item_limit = serializers.IntegerField(min_value=1, max_value=20, required=False, default=3)
