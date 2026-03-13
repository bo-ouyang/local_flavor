from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from messaging.models import ConversationMember
from messaging.realtime import _group_name


@database_sync_to_async
def _member_exists(conversation_id: int, user_id: int) -> bool:
    return ConversationMember.objects.filter(
        conversation_id=conversation_id, user_id=user_id
    ).exists()


class ConversationConsumer(AsyncJsonWebsocketConsumer):
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
        event = content.get("event")
        if event == "ping":
            await self.send_json({"event": "pong"})

    async def chat_event(self, event):
        payload = event.get("payload") or {}
        await self.send_json(payload)
