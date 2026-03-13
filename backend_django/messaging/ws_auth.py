from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections

from core.auth import resolve_openid_from_token
from users.models import LocalUser


@database_sync_to_async
def _get_user_by_token(token: str | None):
    if not token:
        return None
    openid = resolve_openid_from_token(token)
    if not openid:
        return None
    return LocalUser.objects.filter(openid=openid).first()


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        close_old_connections()
        query_string = scope.get("query_string", b"").decode("utf-8")
        query = parse_qs(query_string)
        token = (query.get("token") or [None])[0]
        local_user = await _get_user_by_token(token)
        scope["local_user"] = local_user
        scope["user"] = AnonymousUser()
        return await super().__call__(scope, receive, send)
