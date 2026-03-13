import json
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError


def code2session(code: str) -> dict:
    appid = getattr(settings, "WECHAT_APPID", "")
    secret = getattr(settings, "WECHAT_SECRET", "")
    timeout = int(getattr(settings, "WECHAT_API_TIMEOUT_SECONDS", 8))

    if not appid or not secret:
        raise APIException("WeChat appid/secret is not configured")

    query = urlencode(
        {
            "appid": appid,
            "secret": secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    url = f"https://api.weixin.qq.com/sns/jscode2session?{query}"

    try:
        with urlopen(url, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise APIException("WeChat login service unavailable") from exc

    if payload.get("errcode"):
        raise ValidationError(
            {"detail": f"WeChat auth failed: {payload.get('errmsg', 'unknown error')}"}
        )

    openid = payload.get("openid")
    if not openid:
        raise ValidationError({"detail": "WeChat response missing openid"})
    return payload
