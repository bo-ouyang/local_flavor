from rest_framework import serializers

from interactions.models import FlavorTag


class FlavorTagReadSerializer(serializers.ModelSerializer):
    is_voted = serializers.SerializerMethodField()

    class Meta:
        model = FlavorTag
        fields = ["tag_name", "vote_count", "is_voted"]

    def get_is_voted(self, obj):
        voted_tag_ids = self.context.get("voted_tag_ids", set())
        return obj.id in voted_tag_ids


class CommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=500)
    parent_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate_content(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("content cannot be empty")
        return cleaned


class CommentListQuerySerializer(serializers.Serializer):
    root_limit = serializers.IntegerField(min_value=1, max_value=200, required=False, default=50)
