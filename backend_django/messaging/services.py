from __future__ import annotations

from django.db import transaction
from django.db.models import F

from messaging.models import ChatMessage, Conversation, ConversationMember
from messaging.realtime import emit_message_created
from messaging.serializers import MessageReadSerializer
from messaging.views import _build_preview, _ensure_direct_conversation, _ensure_members
from users.models import LocalUser


SYSTEM_OPENID = "system_notice_bot"
SYSTEM_NICKNAME = "系统通知"
SYSTEM_AVATAR = "/static/defaults/system-notice.png"


def get_or_create_system_user() -> LocalUser:
    user, created = LocalUser.objects.get_or_create(
        openid=SYSTEM_OPENID,
        defaults={
            "nickname": SYSTEM_NICKNAME,
            "avatar": SYSTEM_AVATAR,
            "is_verified": True,
        },
    )
    if created:
        return user

    update_fields = []
    if user.nickname != SYSTEM_NICKNAME:
        user.nickname = SYSTEM_NICKNAME
        update_fields.append("nickname")
    if not user.avatar:
        user.avatar = SYSTEM_AVATAR
        update_fields.append("avatar")
    if not user.is_verified:
        user.is_verified = True
        update_fields.append("is_verified")
    if update_fields:
        user.save(update_fields=update_fields)
    return user


def send_system_notice(user_id: int, content: str, item_id: int | None = None) -> dict | None:
    target = LocalUser.objects.filter(id=user_id).first()
    if not target or not content.strip():
        return None

    system_user = get_or_create_system_user()
    if system_user.id == user_id:
        return None

    conversation = _ensure_direct_conversation(system_user.id, user_id, item_id)

    with transaction.atomic():
        conv = Conversation.objects.select_for_update().get(id=conversation.id)
        next_seq = conv.last_seq + 1
        msg = ChatMessage.objects.create(
            conversation_id=conv.id,
            sender_id=system_user.id,
            item_id=item_id,
            seq=next_seq,
            msg_type=ChatMessage.MSG_TYPE_SYSTEM,
            content=content.strip(),
        )
        preview = _build_preview(ChatMessage.MSG_TYPE_SYSTEM, msg.content, None)

        conv.last_seq = next_seq
        conv.last_message_type = ChatMessage.MSG_TYPE_SYSTEM
        conv.last_message_preview = preview
        conv.last_message_at = msg.created_at
        conv.save(
            update_fields=[
                "last_seq",
                "last_message_type",
                "last_message_preview",
                "last_message_at",
                "updated_at",
            ]
        )

        _ensure_members(conv.id, [conv.participant_low_id, conv.participant_high_id])
        ConversationMember.objects.filter(
            conversation_id=conv.id, user_id=system_user.id
        ).update(last_read_seq=next_seq, unread_count=0)
        ConversationMember.objects.filter(conversation_id=conv.id, user_id=user_id).update(
            unread_count=F("unread_count") + 1
        )

    msg = ChatMessage.objects.select_related("sender", "item").get(id=msg.id)
    payload = MessageReadSerializer(msg).data
    emit_message_created(conv.id, payload)
    return payload
