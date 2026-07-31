from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.utils import timezone

from core.auth import legacy_tokens_allowed, resolve_auth_token


@database_sync_to_async
def _get_user_by_token(token: str | None):
    resolution = resolve_auth_token(token)
    return resolution.user if resolution else None


@database_sync_to_async
def _get_auth_context_by_token(token: str | None):
    resolution = resolve_auth_token(token)
    if resolution is None:
        return None, None
    session_id = resolution.session.id if resolution.session else None
    return resolution.user, session_id


def ws_query_tokens_allowed() -> bool:
    return bool(getattr(settings, "AUTH_WS_QUERY_TOKEN_ENABLED", False)) and (
        legacy_tokens_allowed(timezone.now())
    )


def _extract_auth(scope) -> tuple[str | None, str | None]:
    """Extract token and its transport source, preferring Authorization."""
    headers = dict(scope.get("headers", []))
    auth_header = headers.get(b"authorization", b"").decode("utf-8", errors="ignore")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip() or None, "header"
    if not ws_query_tokens_allowed():
        return None, None
    query_string = (scope.get("query_string") or b"").decode("utf-8", errors="ignore")
    if query_string:
        token = parse_qs(query_string).get("token", [None])[0]
        if token:
            return token.strip() or None, "query"
    return None, None


def _extract_token(scope) -> str | None:
    return _extract_auth(scope)[0]


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        close_old_connections()
        token, auth_source = _extract_auth(scope)
        local_user, auth_session_id = await _get_auth_context_by_token(token)
        scope["local_user"] = local_user
        scope["auth_session_id"] = auth_session_id
        scope["auth_token"] = token
        scope["auth_source"] = auth_source
        scope["user"] = AnonymousUser()
        return await super().__call__(scope, receive, send)
