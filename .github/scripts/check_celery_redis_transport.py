from __future__ import annotations

import argparse
from importlib.metadata import metadata, version
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version
from redis import Redis


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend_django"


def _matching_requirement(
    distribution: str,
    dependency: str,
    *,
    extra: str = "",
    dependency_extra: str = "",
) -> Requirement:
    for raw_requirement in metadata(distribution).get_all("Requires-Dist") or []:
        requirement = Requirement(raw_requirement)
        if canonicalize_name(requirement.name) != canonicalize_name(dependency):
            continue
        if dependency_extra and dependency_extra not in requirement.extras:
            continue
        if requirement.marker and not requirement.marker.evaluate({"extra": extra}):
            continue
        return requirement
    raise RuntimeError(
        f"{distribution} does not expose an active {dependency} requirement"
    )


def _check_dependency_metadata() -> str:
    _matching_requirement(
        "celery", "kombu", extra="redis", dependency_extra="redis"
    )

    installed_redis = Version(version("redis"))
    for distribution in ("kombu", "channels-redis"):
        requirement = _matching_requirement(distribution, "redis", extra="redis")
        if installed_redis not in requirement.specifier:
            raise RuntimeError(
                f"redis {installed_redis} does not satisfy "
                f"{distribution} {requirement.specifier}"
            )
    return str(installed_redis)


def _require_redis_url(label: str, value: str | None) -> str:
    url = (value or "").strip()
    if urlparse(url).scheme not in {"redis", "rediss"}:
        raise RuntimeError(f"{label} must use a redis:// or rediss:// URL")
    return url


def _load_project_celery_app():
    sys.path.insert(0, str(BACKEND_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django

    django.setup()

    from config.celery import app

    if app.conf.task_always_eager:
        raise RuntimeError("Celery smoke check requires non-eager mode")

    broker_url = _require_redis_url("CELERY_BROKER_URL", app.conf.broker_url)
    result_backend = _require_redis_url(
        "CELERY_RESULT_BACKEND", app.conf.result_backend
    )

    connection = app.connection_for_write()
    try:
        if connection.transport.driver_name != "redis":
            raise RuntimeError("Celery did not load the Kombu Redis transport")
    finally:
        connection.release()

    if app.backend.__class__.__module__ != "celery.backends.redis":
        raise RuntimeError("Celery did not load the Redis result backend")

    return broker_url, result_backend


def _ping_redis_urls(urls: tuple[str, ...]) -> None:
    for url in dict.fromkeys(urls):
        client = Redis.from_url(url, socket_connect_timeout=3, socket_timeout=3)
        try:
            if client.ping() is not True:
                raise RuntimeError("Redis PING returned an unexpected response")
        except Exception as exc:
            raise RuntimeError("Redis PING failed") from exc
        finally:
            client.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the project's non-eager Celery Redis transport."
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        help="PING the configured Redis broker and result backend without writing data.",
    )
    args = parser.parse_args()

    redis_version = _check_dependency_metadata()
    redis_urls = _load_project_celery_app()
    if args.ping:
        _ping_redis_urls(redis_urls)

    network_status = "pinged" if args.ping else "skipped"
    print(f"Celery Redis transport smoke check passed (network={network_status})")
    print(f"redis-py={redis_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
