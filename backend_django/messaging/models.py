from django.db import models

from items.models import Item
from users.models import LocalUser


class Message(models.Model):
    sender = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="received_messages"
    )
    item = models.ForeignKey(
        Item, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages"
        indexes = [
            models.Index(fields=["sender", "receiver", "created_at"]),
            models.Index(fields=["receiver", "created_at"]),
            models.Index(fields=["item", "created_at"]),
        ]


class Conversation(models.Model):
    CONTEXT_GLOBAL = "global"

    participant_low = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="conversations_as_low"
    )
    participant_high = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="conversations_as_high"
    )
    item = models.ForeignKey(
        Item,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations",
    )
    context_key = models.CharField(max_length=64, default=CONTEXT_GLOBAL)

    last_seq = models.BigIntegerField(default=0)
    last_message_type = models.CharField(max_length=20, default="text")
    last_message_preview = models.CharField(max_length=255, blank=True, default="")
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_conversations"
        constraints = [
            models.UniqueConstraint(
                fields=["participant_low", "participant_high", "context_key"],
                name="chat_conv_pair_context_unique",
            )
        ]
        indexes = [
            models.Index(fields=["participant_low", "last_message_at"]),
            models.Index(fields=["participant_high", "last_message_at"]),
            models.Index(fields=["context_key", "last_message_at"]),
        ]


class ConversationMember(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="conversation_memberships"
    )
    last_read_seq = models.BigIntegerField(default=0)
    unread_count = models.IntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_conversation_members"
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="chat_conv_member_unique",
            )
        ]
        indexes = [
            models.Index(fields=["user", "updated_at"]),
            models.Index(fields=["conversation", "user"]),
        ]


class ChatMessage(models.Model):
    MSG_TYPE_TEXT = "text"
    MSG_TYPE_ITEM_CARD = "item_card"
    MSG_TYPE_SYSTEM = "system"
    MSG_TYPE_IMAGE = "image"

    MSG_TYPE_CHOICES = (
        (MSG_TYPE_TEXT, "Text"),
        (MSG_TYPE_ITEM_CARD, "ItemCard"),
        (MSG_TYPE_SYSTEM, "System"),
        (MSG_TYPE_IMAGE, "Image"),
    )

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        LocalUser, on_delete=models.CASCADE, related_name="chat_messages"
    )
    item = models.ForeignKey(
        Item,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chat_messages",
    )
    seq = models.BigIntegerField()
    msg_type = models.CharField(max_length=20, choices=MSG_TYPE_CHOICES, default=MSG_TYPE_TEXT)
    content = models.TextField(blank=True, default="")
    client_msg_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_messages"
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "seq"],
                name="chat_message_conv_seq_unique",
            ),
            models.UniqueConstraint(
                fields=["sender", "client_msg_id"],
                name="chat_message_sender_client_unique",
                condition=~models.Q(client_msg_id=""),
            ),
        ]
        indexes = [
            models.Index(fields=["conversation", "seq"]),
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["item", "created_at"]),
        ]
