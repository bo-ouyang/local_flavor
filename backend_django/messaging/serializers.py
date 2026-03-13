from rest_framework import serializers

from items.models import Item
from messaging.models import ChatMessage
from users.serializers import LocalUserReadSerializer


class ItemCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ["id", "title", "images", "category"]


class MessageCreateSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(min_value=1, required=False)
    receiver_id = serializers.IntegerField(min_value=1, required=False)
    content = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    item_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    msg_type = serializers.ChoiceField(
        choices=[
            ChatMessage.MSG_TYPE_TEXT,
            ChatMessage.MSG_TYPE_ITEM_CARD,
            ChatMessage.MSG_TYPE_IMAGE,
            ChatMessage.MSG_TYPE_SYSTEM,
        ],
        default=ChatMessage.MSG_TYPE_TEXT,
    )
    client_msg_id = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def validate(self, attrs):
        conversation_id = attrs.get("conversation_id")
        receiver_id = attrs.get("receiver_id")
        if not conversation_id and not receiver_id:
            raise serializers.ValidationError("conversation_id or receiver_id is required")
        if conversation_id and receiver_id:
            raise serializers.ValidationError("conversation_id and receiver_id cannot both be provided")

        msg_type = attrs.get("msg_type", ChatMessage.MSG_TYPE_TEXT)
        content = (attrs.get("content") or "").strip()
        item_id = attrs.get("item_id")

        if msg_type == ChatMessage.MSG_TYPE_TEXT and not content:
            raise serializers.ValidationError({"content": "content cannot be empty"})
        if msg_type == ChatMessage.MSG_TYPE_ITEM_CARD and not item_id:
            raise serializers.ValidationError({"item_id": "item_id required for item_card message"})
        if msg_type == ChatMessage.MSG_TYPE_IMAGE and not content:
            raise serializers.ValidationError({"content": "image message content cannot be empty"})

        attrs["content"] = content
        return attrs


class MessageReadSerializer(serializers.ModelSerializer):
    sender = LocalUserReadSerializer(read_only=True)
    item = ItemCardSerializer(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "conversation_id",
            "seq",
            "sender_id",
            "msg_type",
            "content",
            "client_msg_id",
            "item_id",
            "created_at",
            "sender",
            "item",
        ]


class MessageHistoryQuerySerializer(serializers.Serializer):
    before_seq = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    limit = serializers.IntegerField(min_value=1, max_value=100, required=False, default=30)


class ConversationEnsureSerializer(serializers.Serializer):
    target_id = serializers.IntegerField(min_value=1)
    item_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class ConversationReadSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    item = ItemCardSerializer(allow_null=True)
    contact = LocalUserReadSerializer()
    unread_count = serializers.IntegerField()
    last_seq = serializers.IntegerField()
    last_message = serializers.DictField()


class ConversationReadAckSerializer(serializers.Serializer):
    seq = serializers.IntegerField(min_value=0, required=False)
