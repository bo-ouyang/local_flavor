from django.contrib import admin

from messaging.models import ChatMessage, Conversation, ConversationMember, Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "sender_id", "receiver_id", "item_id", "created_at","content")
    search_fields = ("content",)
    list_filter = ("created_at",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "participant_low_id",
        "participant_high_id",
        "context_key",
        "item_id",
        "last_seq",
        "last_message_type",
        "last_message_at",
    )
    search_fields = ("context_key", "last_message_preview")
    list_filter = ("last_message_type", "created_at")


@admin.register(ConversationMember)
class ConversationMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation_id", "user_id", "last_read_seq", "unread_count", "updated_at")
    list_filter = ("updated_at",)
    search_fields = ("conversation_id", "user_id")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation_id", "seq", "sender_id", "msg_type", "item_id", "created_at")
    list_filter = ("msg_type", "created_at")
    search_fields = ("content", "client_msg_id")
