from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from rest_framework.exceptions import NotAuthenticated, NotFound

from users.models import LocalUser


_signer = TimestampSigner(salt="local-flavor-auth")
_token_ttl_seconds = int(getattr(settings, "AUTH_TOKEN_TTL_SECONDS", 30 * 24 * 3600))


def extract_bearer_token(request) -> Optional[str]:
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def issue_token(openid: str) -> str:
    return _signer.sign(openid)


def resolve_openid_from_token(token: str) -> Optional[str]:
    if not token or ":" not in token:
        return None
    try:
        return str(_signer.unsign(token, max_age=_token_ttl_seconds))
    except (BadSignature, SignatureExpired):
        return None


def get_current_user(request, required: bool = True) -> Optional[LocalUser]:
    token = extract_bearer_token(request)
    if not token:
        if required:
            raise NotAuthenticated("Authentication credentials were not provided.")
        return None

    openid = resolve_openid_from_token(token)
    if not openid:
        if required:
            raise NotAuthenticated("Invalid or expired token")
        return None

    user = LocalUser.objects.filter(openid=openid).first()
    if user:
        return user
    if required:
        raise NotFound("User not found")
    return None
