from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from core.auth import resolve_auth_token
from messaging.models import ConversationMember
from messaging.realtime import _group_name
from messaging.ws_auth import ws_query_tokens_allowed


@database_sync_to_async
def _member_exists(conversation_id: int, user_id: int) -> bool:
    return ConversationMember.objects.filter(
        conversation_id=conversation_id, user_id=user_id
    ).exists()


@database_sync_to_async
def _authentication_still_valid(
    token: str | None,
    expected_user_id: int,
    expected_session_id: int | None,
    auth_source: str | None,
) -> bool:
    if auth_source == "query" and not ws_query_tokens_allowed():
        return False
    resolution = resolve_auth_token(token)
    if resolution is None or resolution.user.id != expected_user_id:
        return False
    resolved_session_id = resolution.session.id if resolution.session else None
    return resolved_session_id == expected_session_id


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    async def _ensure_authentication_active(self) -> bool:
        active = await _authentication_still_valid(
            self.scope.get("auth_token"),
            self.local_user.id,
            self.scope.get("auth_session_id"),
            self.scope.get("auth_source"),
        )
        if not active:
            await self.close(code=4401)
            return False
        return True

    async def connect(self):
        local_user = self.scope.get("local_user")
        if not local_user:
            await self.close(code=4401)
            return

        self.local_user = local_user
        self.conversation_id = int(self.scope["url_route"]["kwargs"]["conversation_id"])
        self.group_name = _group_name(self.conversation_id)

        allowed = await _member_exists(self.conversation_id, self.local_user.id)
        if not allowed:
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json(
            {
                "event": "ws.connected",
                "conversation_id": self.conversation_id,
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if not await self._ensure_authentication_active():
            return
        event = content.get("event")
        if event == "ping":
            await self.send_json({"event": "pong"})

    async def chat_event(self, event):
        if not await self._ensure_authentication_active():
            return
        payload = event.get("payload") or {}
        await self.send_json(payload)
