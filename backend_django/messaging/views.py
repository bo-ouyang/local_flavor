from __future__ import annotations

from typing import Optional, Tuple

from django.db import IntegrityError, transaction
from django.db.models import F
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.views import APIView

from core.auth import get_current_user
from core.responses import api_success
from items.models import Item
from messaging.models import ChatMessage, Conversation, ConversationMember
from messaging.realtime import emit_conversation_read, emit_message_created
from messaging.serializers import (
    ConversationEnsureSerializer,
    ConversationReadAckSerializer,
    ItemCardSerializer,
    MessageCreateSerializer,
    MessageHistoryQuerySerializer,
    MessageReadSerializer,
)
from users.models import LocalUser
from users.serializers import LocalUserReadSerializer


def _pair_ids(user_a_id: int, user_b_id: int) -> Tuple[int, int]:
    return (user_a_id, user_b_id) if user_a_id < user_b_id else (user_b_id, user_a_id)


def _build_context_key(item_id: Optional[int]) -> str:
    if item_id:
        return f"item:{item_id}"
    return Conversation.CONTEXT_GLOBAL


def _build_preview(msg_type: str, content: str, item: Optional[Item]) -> str:
    if msg_type == ChatMessage.MSG_TYPE_ITEM_CARD:
        if item:
            return f"[商品] {item.title}"
        return "[商品卡片]"
    if msg_type == ChatMessage.MSG_TYPE_IMAGE:
        return "[图片]"
    if msg_type == ChatMessage.MSG_TYPE_SYSTEM:
        return content[:80] or "[系统消息]"
    return content[:80]


def _ensure_members(conversation_id: int, user_ids: list[int]) -> None:
    existing = set(
        ConversationMember.objects.filter(
            conversation_id=conversation_id, user_id__in=user_ids
        ).values_list("user_id", flat=True)
    )
    create_rows = [
        ConversationMember(conversation_id=conversation_id, user_id=user_id)
        for user_id in user_ids
        if user_id not in existing
    ]
    if create_rows:
        ConversationMember.objects.bulk_create(create_rows, ignore_conflicts=True)


def _ensure_direct_conversation(user_a_id: int, user_b_id: int, item_id: Optional[int]) -> Conversation:
    if user_a_id == user_b_id:
        raise ValidationError({"detail": "Cannot chat with self"})

    low_id, high_id = _pair_ids(user_a_id, user_b_id)
    context_key = _build_context_key(item_id)
    defaults = {
        "item_id": item_id,
    }
    try:
        conversation, _created = Conversation.objects.get_or_create(
            participant_low_id=low_id,
            participant_high_id=high_id,
            context_key=context_key,
            defaults=defaults,
        )
    except IntegrityError:
        conversation = Conversation.objects.get(
            participant_low_id=low_id,
            participant_high_id=high_id,
            context_key=context_key,
        )

    if item_id and conversation.item_id != item_id:
        conversation.item_id = item_id
        conversation.save(update_fields=["item", "updated_at"])

    _ensure_members(conversation.id, [user_a_id, user_b_id])
    return conversation


def _get_conversation_member(conversation_id: int, user_id: int) -> ConversationMember:
    member = (
        ConversationMember.objects.select_related(
            "conversation",
            "conversation__item",
            "conversation__participant_low",
            "conversation__participant_high",
        )
        .filter(conversation_id=conversation_id, user_id=user_id)
        .first()
    )
    if not member:
        raise PermissionDenied("No permission for this conversation")
    return member


def _conversation_payload(member: ConversationMember) -> dict:
    conv = member.conversation
    contact = (
        conv.participant_high if conv.participant_low_id == member.user_id else conv.participant_low
    )
    return {
        "conversation_id": conv.id,
        "contact": LocalUserReadSerializer(contact).data,
        "item": ItemCardSerializer(conv.item).data if conv.item else None,
        "unread_count": member.unread_count,
        "last_seq": conv.last_seq,
        "last_message": {
            "seq": conv.last_seq,
            "msg_type": conv.last_message_type,
            "content": conv.last_message_preview,
            "created_at": conv.last_message_at,
        },
    }


class ConversationListView(APIView):
    def get(self, request):
        user = get_current_user(request, required=True)
        members = (
            ConversationMember.objects.filter(user_id=user.id)
            .select_related(
                "conversation",
                "conversation__item",
                "conversation__participant_low",
                "conversation__participant_high",
            )
            .order_by("-conversation__last_message_at", "-conversation__id")
        )
        result = [_conversation_payload(member) for member in members]
        return api_success(data=result)


class ConversationEnsureView(APIView):
    def post(self, request):
        user = get_current_user(request, required=True)
        serializer = ConversationEnsureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_id = serializer.validated_data["target_id"]
        if target_id == user.id:
            raise ValidationError({"detail": "Cannot chat with self"})

        target = LocalUser.objects.filter(id=target_id).first()
        if not target:
            raise NotFound("Target user not found")

        item_id = serializer.validated_data.get("item_id")
        if item_id and not Item.objects.filter(id=item_id).exists():
            raise NotFound("Item not found")

        conversation = _ensure_direct_conversation(user.id, target_id, item_id)
        member = _get_conversation_member(conversation.id, user.id)
        return api_success(data=_conversation_payload(member))


class ConversationMessagesView(APIView):
    def get(self, request, conversation_id: int):
        user = get_current_user(request, required=True)
        member = _get_conversation_member(conversation_id, user.id)

        query_serializer = MessageHistoryQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        before_seq = query_serializer.validated_data.get("before_seq")
        limit = query_serializer.validated_data["limit"]

        messages_qs = (
            ChatMessage.objects.filter(conversation_id=conversation_id)
            .select_related("sender", "item")
            .order_by("-seq")
        )
        if before_seq:
            messages_qs = messages_qs.filter(seq__lt=before_seq)
        messages = list(messages_qs[:limit])
        messages.reverse()

        if messages:
            latest_seq = messages[-1].seq
            ConversationMember.objects.filter(id=member.id).update(
                last_read_seq=max(member.last_read_seq, latest_seq),
                unread_count=0,
            )

        return api_success(data=MessageReadSerializer(messages, many=True).data)


class ConversationReadAckView(APIView):
    def post(self, request, conversation_id: int):
        user = get_current_user(request, required=True)
        member = _get_conversation_member(conversation_id, user.id)

        serializer = ConversationReadAckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ack_seq = serializer.validated_data.get("seq", member.conversation.last_seq)
        if ack_seq < 0:
            ack_seq = 0
        if ack_seq > member.conversation.last_seq:
            ack_seq = member.conversation.last_seq

        ConversationMember.objects.filter(id=member.id).update(
            last_read_seq=max(member.last_read_seq, ack_seq),
            unread_count=0,
        )
        emit_conversation_read(conversation_id, user.id, ack_seq)
        return api_success(
            data={"conversation_id": conversation_id, "read_seq": ack_seq},
            message="read acknowledged",
        )


class MessageHistoryView(APIView):
    """
    Legacy endpoint for compatibility:
    GET /chat/<target_id>?limit=30&before_seq=100&item_id=123
    """

    def get(self, request, target_id: int):
        user = get_current_user(request, required=True)
        target = LocalUser.objects.filter(id=target_id).first()
        if not target:
            raise NotFound("Target user not found")

        raw_item_id = request.query_params.get("item_id")
        item_id: Optional[int] = None
        if raw_item_id not in (None, ""):
            try:
                item_id = int(raw_item_id)
            except ValueError as exc:
                raise ValidationError({"item_id": "item_id must be integer"}) from exc
            if not Item.objects.filter(id=item_id).exists():
                raise NotFound("Item not found")

        conversation = _ensure_direct_conversation(user.id, target_id, item_id)
        _member = _get_conversation_member(conversation.id, user.id)

        query_serializer = MessageHistoryQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        before_seq = query_serializer.validated_data.get("before_seq")
        limit = query_serializer.validated_data["limit"]

        messages_qs = (
            ChatMessage.objects.filter(conversation_id=conversation.id)
            .select_related("sender", "item")
            .order_by("-seq")
        )
        if before_seq:
            messages_qs = messages_qs.filter(seq__lt=before_seq)
        messages = list(messages_qs[:limit])  # Keep desc ordering for legacy clients.
        return api_success(data=MessageReadSerializer(messages, many=True).data)


class MessageCreateView(APIView):
    def post(self, request):
        user = get_current_user(request, required=True)
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation_id = serializer.validated_data.get("conversation_id")
        receiver_id = serializer.validated_data.get("receiver_id")
        item_id = serializer.validated_data.get("item_id")
        msg_type = serializer.validated_data.get("msg_type", ChatMessage.MSG_TYPE_TEXT)
        content = serializer.validated_data.get("content", "")
        client_msg_id = (serializer.validated_data.get("client_msg_id") or "").strip()

        item = None
        if item_id:
            item = Item.objects.filter(id=item_id).first()
            if not item:
                raise NotFound("Item not found")

        if client_msg_id:
            existed = (
                ChatMessage.objects.select_related("sender", "item")
                .filter(sender_id=user.id, client_msg_id=client_msg_id)
                .first()
            )
            if existed:
                return api_success(data=MessageReadSerializer(existed).data, message="duplicate ignored")

        if conversation_id:
            member = _get_conversation_member(conversation_id, user.id)
            conversation = member.conversation
        else:
            if receiver_id == user.id:
                raise ValidationError({"detail": "Cannot send message to self"})
            receiver = LocalUser.objects.filter(id=receiver_id).first()
            if not receiver:
                raise NotFound("Receiver not found")
            conversation = _ensure_direct_conversation(user.id, receiver_id, item_id)

        with transaction.atomic():
            conv = Conversation.objects.select_for_update().get(id=conversation.id)
            next_seq = conv.last_seq + 1

            msg = ChatMessage.objects.create(
                conversation_id=conv.id,
                sender_id=user.id,
                item=item,
                seq=next_seq,
                msg_type=msg_type,
                content=content,
                client_msg_id=client_msg_id,
            )
            preview = _build_preview(msg_type, content, item)

            conv.last_seq = next_seq
            conv.last_message_type = msg_type
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
                conversation_id=conv.id, user_id=user.id
            ).update(last_read_seq=next_seq, unread_count=0)
            ConversationMember.objects.filter(conversation_id=conv.id).exclude(
                user_id=user.id
            ).update(unread_count=F("unread_count") + 1)

        msg = ChatMessage.objects.select_related("sender", "item").get(id=msg.id)
        serialized = MessageReadSerializer(msg).data
        emit_message_created(conv.id, serialized)
        return api_success(
            data=serialized,
            message="message sent",
            status_code=status.HTTP_201_CREATED,
        )
