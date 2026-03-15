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


def _extract_token(scope) -> str | None:
    """Extract token from Authorization header first, then query string fallback."""
    headers = dict(scope.get("headers", []))
    auth_header = headers.get(b"authorization", b"").decode("utf-8", errors="ignore")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip() or None
    query_string = (scope.get("query_string") or b"").decode("utf-8", errors="ignore")
    if query_string:
        token = parse_qs(query_string).get("token", [None])[0]
        if token:
            return token.strip() or None
    return None


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        close_old_connections()
        token = _extract_token(scope)
        local_user = await _get_user_by_token(token)
        scope["local_user"] = local_user
        scope["user"] = AnonymousUser()
        return await super().__call__(scope, receive, send)
