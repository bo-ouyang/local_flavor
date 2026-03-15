from rest_framework import serializers

from community.models import CommunityComment, CommunityPost
from items.models import Item
from users.serializers import LocalUserReadSerializer


class CommunityItemCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ["id", "title", "images", "category", "province", "city", "region_code"]


class CommunityPostCreateSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(min_value=1)
    exchange_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    content = serializers.CharField(min_length=1, max_length=2000)
    images = serializers.ListField(
        child=serializers.CharField(max_length=500), required=False, default=list
    )

    def validate_content(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("content cannot be empty")
        return cleaned

    def validate_images(self, value):
        cleaned = []
        for img in value:
            if not isinstance(img, str):
                raise serializers.ValidationError("images must be string list")
            url = img.strip()
            if not url:
                continue
            if not (
                url.startswith("http://")
                or url.startswith("https://")
                or url.startswith("/static/")
            ):
                raise serializers.ValidationError(
                    "image url must start with http(s):// or /static/"
                )
            cleaned.append(url)
        if len(cleaned) > 9:
            raise serializers.ValidationError("max 9 images")
        return cleaned


class CommunityPostListQuerySerializer(serializers.Serializer):
    skip = serializers.IntegerField(min_value=0, required=False, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)
    q = serializers.CharField(required=False, allow_blank=True, max_length=100)
    sort = serializers.ChoiceField(choices=["latest", "hot"], required=False, default="latest")

    def validate_q(self, value):
        return value.strip()


class CommunityCommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=500)
    parent_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate_content(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("content cannot be empty")
        return cleaned


class CommunityCommentListQuerySerializer(serializers.Serializer):
    root_limit = serializers.IntegerField(min_value=1, max_value=200, required=False, default=100)


class CommunityPostReadSerializer(serializers.ModelSerializer):
    user = LocalUserReadSerializer(read_only=True)
    item = CommunityItemCardSerializer(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    can_comment = serializers.BooleanField(read_only=True)
    like_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)
    author_tag = serializers.CharField(read_only=True)
    exchange_hint = serializers.CharField(read_only=True)
    audit_status = serializers.CharField(read_only=True)
    audit_reason = serializers.CharField(read_only=True)

    class Meta:
        model = CommunityPost
        fields = [
            "id",
            "user_id",
            "item_id",
            "exchange_id",
            "content",
            "images",
            "created_at",
            "user",
            "item",
            "comment_count",
            "can_comment",
            "like_count",
            "is_liked",
            "author_tag",
            "exchange_hint",
            "audit_status",
            "audit_reason",
        ]


class CommunityCommentReadSerializer(serializers.ModelSerializer):
    user = LocalUserReadSerializer(read_only=True)

    class Meta:
        model = CommunityComment
        fields = [
            "id",
            "post_id",
            "user_id",
            "content",
            "created_at",
            "parent_id",
            "root_id",
            "depth",
            "audit_status",
            "audit_reason",
            "user",
        ]
