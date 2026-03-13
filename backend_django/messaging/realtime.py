from __future__ import annotations

import logging
import time
from typing import Any

from django.conf import settings

logger = logging.getLogger("app")

_PUSH_BACKOFF_SECONDS = 60
_WARN_INTERVAL_SECONDS = 30
_push_disabled_until = 0.0
_last_warn_at = 0.0
_last_warn_msg = ""


def _group_name(conversation_id: int) -> str:
    return f"chat.conversation.{conversation_id}"


def _warn_limited(message: str) -> None:
    global _last_warn_at, _last_warn_msg
    now = time.time()
    if message == _last_warn_msg and (now - _last_warn_at) < _WARN_INTERVAL_SECONDS:
        return
    _last_warn_at = now
    _last_warn_msg = message
    logger.warning(message)


def _push_group_event(conversation_id: int, payload: dict[str, Any]) -> None:
    global _push_disabled_until
    if not getattr(settings, "CHAT_ENABLE_WS", False):
        return
    if time.time() < _push_disabled_until:
        return
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
    except Exception:
        return

    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            _group_name(conversation_id),
            {
                "type": "chat_event",
                "payload": payload,
            },
        )
    except Exception as exc:
        # Realtime push failures must not break REST APIs.
        err_text = str(exc)
        if "Authentication required" in err_text:
            _push_disabled_until = time.time() + _PUSH_BACKOFF_SECONDS
            _warn_limited(
                "chat realtime push disabled for 60s: redis auth failed. "
                "Check CHAT_REDIS_PASSWORD / CHAT_REDIS_URL."
            )
            return
        _warn_limited(f"chat realtime push skipped: {err_text}")


def emit_message_created(conversation_id: int, message: dict[str, Any]) -> None:
    _push_group_event(
        conversation_id,
        {
            "event": "message.created",
            "conversation_id": conversation_id,
            "message": message,
        },
    )


def emit_conversation_read(conversation_id: int, user_id: int, seq: int) -> None:
    _push_group_event(
        conversation_id,
        {
            "event": "conversation.read",
            "conversation_id": conversation_id,
            "user_id": user_id,
            "seq": seq,
        },
    )
