from __future__ import annotations

import hashlib
import json
from typing import Mapping

from django.core.cache import cache


def _to_plain_params(params: Mapping | dict | None) -> dict:
    if not params:
        return {}
    plain = {}
    for key in sorted(params.keys()):
        value = params.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                continue
        plain[str(key)] = value
    return plain


def build_cache_key(prefix: str, params: Mapping | dict | None = None, version: int | None = None) -> str:
    payload = json.dumps(_to_plain_params(params), sort_keys=True, ensure_ascii=True, default=str)
    digest = hashlib.md5(payload.encode("utf-8")).hexdigest()
    if version is None:
        return f"{prefix}:{digest}"
    return f"{prefix}:v{version}:{digest}"


def get_namespace_version(namespace: str) -> int:
    key = f"cache:version:{namespace}"
    current = cache.get(key)
    if current is None:
        cache.set(key, 1, timeout=None)
        return 1
    try:
        return int(current)
    except (TypeError, ValueError):
        cache.set(key, 1, timeout=None)
        return 1


def cache_get(key: str):
    try:
        return cache.get(key)
    except Exception:
        return None


def cache_set(key: str, value, timeout: int | None = None) -> bool:
    try:
        cache.set(key, value, timeout=timeout)
        return True
    except Exception:
        return False


def bump_namespace_version(namespace: str) -> int:
    key = f"cache:version:{namespace}"
    if cache.get(key) is None:
        cache.set(key, 1, timeout=None)
    try:
        return cache.incr(key)
    except Exception:
        current = get_namespace_version(namespace) + 1
        cache.set(key, current, timeout=None)
        return current
