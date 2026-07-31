import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _load_env_file(
    file_path: Path,
    *,
    required: bool = False,
    strict: bool = False,
) -> None:
    if not file_path.exists():
        if required:
            raise RuntimeError(f"Explicit DJANGO_ENV_FILE does not exist: {file_path}")
        return
    if not file_path.is_file():
        raise RuntimeError(f"DJANGO_ENV_FILE must be a regular file: {file_path}")
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"Unable to read DJANGO_ENV_FILE: {file_path}") from exc
    for line_number, line in enumerate(lines, start=1):
        row = line.strip()
        if not row or row.startswith("#"):
            continue
        if "=" not in row:
            if strict:
                raise RuntimeError(
                    f"Invalid env row at {file_path}:{line_number}"
                )
            continue
        key, value = row.split("=", 1)
        key = key.strip()
        if strict and not key:
            raise RuntimeError(f"Empty env key at {file_path}:{line_number}")
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_django_env_aliases = {"prod": "pro", "production": "pro"}


def _parse_django_env(raw_value: str) -> str:
    raw = (raw_value or "").strip().lower()
    normalized = _django_env_aliases.get(raw, raw)
    if normalized not in {"dev", "pro"}:
        raise RuntimeError(f"Unsupported DJANGO_ENV: {raw}")
    return normalized


_django_env_process_value = os.getenv("DJANGO_ENV")
_initial_django_env = _parse_django_env(_django_env_process_value or "dev")
_explicit_env_file = os.getenv("DJANGO_ENV_FILE")
_load_env_file_raw = os.getenv("DJANGO_LOAD_ENV_FILE", "1")
if _load_env_file_raw not in {"0", "1"}:
    raise RuntimeError("DJANGO_LOAD_ENV_FILE must be exactly 0 or 1")
if _load_env_file_raw == "1":
    _env_file = Path(
        _explicit_env_file or str(BASE_DIR / f"env.{_initial_django_env}")
    )
    _load_env_file(
        _env_file,
        required=bool(_explicit_env_file),
        strict=bool(_explicit_env_file),
    )
DJANGO_ENV = _parse_django_env(os.getenv("DJANGO_ENV", _initial_django_env))
if not _explicit_env_file and DJANGO_ENV != _initial_django_env:
    raise RuntimeError(
        "A default env file cannot switch DJANGO_ENV; use an explicit "
        "DJANGO_ENV_FILE or set DJANGO_ENV in the process environment"
    )

_secret_key = os.getenv("DJANGO_SECRET_KEY", "")
if not _secret_key:
    if DJANGO_ENV == "pro":
        raise RuntimeError("DJANGO_SECRET_KEY must be set in production")
    _secret_key = "dev-only-insecure-key-do-not-use-in-production"
SECRET_KEY = _secret_key

DEBUG = os.getenv("DJANGO_DEBUG", "1" if DJANGO_ENV == "dev" else "0") == "1"
if DEBUG and DJANGO_ENV == "pro":
    raise RuntimeError("DEBUG must not be enabled in production (DJANGO_ENV=pro)")

_allowed_hosts_raw = os.getenv("DJANGO_ALLOWED_HOSTS", "" if DJANGO_ENV == "pro" else "*")
if DJANGO_ENV == "pro" and (not _allowed_hosts_raw or _allowed_hosts_raw == "*"):
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be explicitly set in production")
ALLOWED_HOSTS = _allowed_hosts_raw.split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "users",
    "items",
    "exchange",
    "interactions",
    "messaging",
    "system_config",
    "stats",
    "uploads",
    "community",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.SimpleCorsMiddleware",
    "core.middleware.RequestLogMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()
if DB_ENGINE == "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME", "local_flavor"),
            "USER": os.getenv("DB_USER", "root"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
elif DB_ENGINE in {"postgres", "postgresql", "pg"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "local_flavor"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/django-static/"
STATIC_ROOT = BASE_DIR / "django_static"

# Keep compatibility with the previous FastAPI static upload path.
MEDIA_URL = "/static/"
MEDIA_ROOT = BASE_DIR.parent / "static"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.auth.OpaqueSessionAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_RATE_ANON", "60/minute"),
        "user": os.getenv("THROTTLE_RATE_USER", "300/minute"),
        "login": os.getenv("THROTTLE_RATE_LOGIN", "10/minute"),
        "upload": os.getenv("THROTTLE_RATE_UPLOAD", "20/minute"),
    },
}

def _positive_decimal_env(name: str, default: str) -> int:
    raw = os.getenv(name, default)
    if not raw or any(char not in "0123456789" for char in raw):
        raise RuntimeError(f"{name} must be a positive decimal integer")
    value = int(raw)
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


def _binary_env(name: str, raw_value, default: str) -> bool:
    value = raw_value if raw_value is not None else default
    if value not in {"0", "1"}:
        raise RuntimeError(f"{name} must be exactly 0 or 1")
    return value == "1"


AUTH_TOKEN_TTL_SECONDS = _positive_decimal_env(
    "AUTH_TOKEN_TTL_SECONDS", str(30 * 24 * 3600)
)
AUTH_ACCESS_TOKEN_TTL_SECONDS = _positive_decimal_env(
    "AUTH_ACCESS_TOKEN_TTL_SECONDS", "900"
)
AUTH_REFRESH_TOKEN_TTL_SECONDS = _positive_decimal_env(
    "AUTH_REFRESH_TOKEN_TTL_SECONDS", str(30 * 24 * 3600)
)
AUTH_SESSION_LAST_SEEN_INTERVAL_SECONDS = _positive_decimal_env(
    "AUTH_SESSION_LAST_SEEN_INTERVAL_SECONDS", "300"
)
AUTH_LEGACY_MAX_WINDOW_SECONDS = _positive_decimal_env(
    "AUTH_LEGACY_MAX_WINDOW_SECONDS", str(90 * 24 * 3600)
)
if AUTH_LEGACY_MAX_WINDOW_SECONDS > 90 * 24 * 3600:
    raise RuntimeError("AUTH_LEGACY_MAX_WINDOW_SECONDS cannot exceed 90 days")
_legacy_enabled_raw = os.getenv("AUTH_LEGACY_TOKEN_ENABLED")
_ws_query_enabled_raw = os.getenv("AUTH_WS_QUERY_TOKEN_ENABLED")
if DJANGO_ENV == "pro" and (
    _legacy_enabled_raw is None or _ws_query_enabled_raw is None
):
    raise RuntimeError(
        "AUTH_LEGACY_TOKEN_ENABLED and AUTH_WS_QUERY_TOKEN_ENABLED "
        "must both be explicitly set in production"
    )
AUTH_LEGACY_TOKEN_ENABLED = _binary_env(
    "AUTH_LEGACY_TOKEN_ENABLED", _legacy_enabled_raw, "1"
)
AUTH_LEGACY_TOKEN_ACCEPT_UNTIL = os.getenv("AUTH_LEGACY_TOKEN_ACCEPT_UNTIL", "")
AUTH_WS_QUERY_TOKEN_ENABLED = _binary_env(
    "AUTH_WS_QUERY_TOKEN_ENABLED", _ws_query_enabled_raw, "1"
)

if DJANGO_ENV == "pro" and (AUTH_LEGACY_TOKEN_ENABLED or AUTH_WS_QUERY_TOKEN_ENABLED):
    if AUTH_WS_QUERY_TOKEN_ENABLED and not AUTH_LEGACY_TOKEN_ENABLED:
        raise RuntimeError(
            "AUTH_WS_QUERY_TOKEN_ENABLED requires AUTH_LEGACY_TOKEN_ENABLED in production"
        )
    try:
        _legacy_cutoff = datetime.fromisoformat(
            AUTH_LEGACY_TOKEN_ACCEPT_UNTIL.replace("Z", "+00:00")
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "AUTH_LEGACY_TOKEN_ACCEPT_UNTIL must be an aware UTC ISO-8601 timestamp"
        ) from exc
    if _legacy_cutoff.tzinfo is None or _legacy_cutoff.utcoffset() != timedelta(0):
        raise RuntimeError("AUTH_LEGACY_TOKEN_ACCEPT_UNTIL must use UTC")
    _legacy_now = datetime.now(timezone.utc)
    if _legacy_cutoff <= _legacy_now:
        raise RuntimeError("AUTH_LEGACY_TOKEN_ACCEPT_UNTIL must be in the future")
    if _legacy_cutoff > _legacy_now + timedelta(
        seconds=AUTH_LEGACY_MAX_WINDOW_SECONDS
    ):
        raise RuntimeError("legacy authentication migration window exceeds configured maximum")

WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")
WECHAT_API_TIMEOUT_SECONDS = int(os.getenv("WECHAT_API_TIMEOUT_SECONDS", "8"))

UPLOAD_MAX_FILE_MB = float(os.getenv("UPLOAD_MAX_FILE_MB", "5"))
UPLOAD_IMAGE_MAX_WIDTH = int(os.getenv("UPLOAD_IMAGE_MAX_WIDTH", "1280"))
UPLOAD_IMAGE_MAX_HEIGHT = int(os.getenv("UPLOAD_IMAGE_MAX_HEIGHT", "1280"))
UPLOAD_IMAGE_JPEG_QUALITY = int(os.getenv("UPLOAD_IMAGE_JPEG_QUALITY", "85"))
UPLOAD_ALLOWED_IMAGE_FORMATS = os.getenv("UPLOAD_ALLOWED_IMAGE_FORMATS", "JPEG,PNG,WEBP")

COMMENT_MAX_DEPTH = int(os.getenv("COMMENT_MAX_DEPTH", "8"))

CHAT_ENABLE_WS = os.getenv("CHAT_ENABLE_WS", "0") == "1"
CHAT_REDIS_URL = os.getenv("CHAT_REDIS_URL", "redis://127.0.0.1:6379/1")
CHAT_WS_HEARTBEAT_SECONDS = int(os.getenv("CHAT_WS_HEARTBEAT_SECONDS", "30"))

CHAT_REDIS_HOST = os.getenv("CHAT_REDIS_HOST", "127.0.0.1")
CHAT_REDIS_PORT = int(os.getenv("CHAT_REDIS_PORT", "6379"))
CHAT_REDIS_DB = int(os.getenv("CHAT_REDIS_DB", "1"))
CHAT_REDIS_USERNAME = os.getenv("CHAT_REDIS_USERNAME", "")
CHAT_REDIS_PASSWORD = os.getenv("CHAT_REDIS_PASSWORD", "")
CHAT_REDIS_USE_SSL = os.getenv("CHAT_REDIS_USE_SSL", "0") == "1"
CHAT_REDIS_SOCKET_CONNECT_TIMEOUT = float(
    os.getenv("CHAT_REDIS_SOCKET_CONNECT_TIMEOUT", "3")
)
CHAT_REDIS_SOCKET_TIMEOUT = float(os.getenv("CHAT_REDIS_SOCKET_TIMEOUT", "3"))
CHAT_REDIS_HEALTH_CHECK_INTERVAL = int(
    os.getenv("CHAT_REDIS_HEALTH_CHECK_INTERVAL", "30")
)


def _build_chat_redis_url() -> str:
    url = (CHAT_REDIS_URL or "").strip()
    if url:
        return url
    scheme = "rediss" if CHAT_REDIS_USE_SSL else "redis"
    auth_part = ""
    if CHAT_REDIS_USERNAME and CHAT_REDIS_PASSWORD:
        auth_part = f"{quote(CHAT_REDIS_USERNAME)}:{quote(CHAT_REDIS_PASSWORD)}@"
    elif CHAT_REDIS_PASSWORD:
        auth_part = f":{quote(CHAT_REDIS_PASSWORD)}@"
    return f"{scheme}://{auth_part}{CHAT_REDIS_HOST}:{CHAT_REDIS_PORT}/{CHAT_REDIS_DB}"

if CHAT_ENABLE_WS:
    try:
        import channels  # noqa: F401
        import daphne  # noqa: F401

        if "daphne" not in INSTALLED_APPS:
            INSTALLED_APPS.insert(0, "daphne")
        if "channels" not in INSTALLED_APPS:
            INSTALLED_APPS.append("channels")
        redis_host = {
            "address": _build_chat_redis_url(),
            "socket_connect_timeout": CHAT_REDIS_SOCKET_CONNECT_TIMEOUT,
            "socket_timeout": CHAT_REDIS_SOCKET_TIMEOUT,
            "health_check_interval": CHAT_REDIS_HEALTH_CHECK_INTERVAL,
        }
        CHANNEL_LAYERS = {
            "default": {
                "BACKEND": "channels_redis.core.RedisChannelLayer",
                "CONFIG": {
                    "hosts": [redis_host],
                },
            }
        }
    except Exception:
        CHAT_ENABLE_WS = False

CACHE_BACKEND = os.getenv("CACHE_BACKEND", "locmem").lower()
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "300"))
CACHE_TTL_OPTIONS = int(os.getenv("CACHE_TTL_OPTIONS", "3600"))
CACHE_TTL_ITEMS_LIST = int(os.getenv("CACHE_TTL_ITEMS_LIST", "60"))
CACHE_TTL_ITEM_DETAIL = int(os.getenv("CACHE_TTL_ITEM_DETAIL", "60"))
CACHE_TTL_ITEMS_TODAY = int(os.getenv("CACHE_TTL_ITEMS_TODAY", "120"))
CACHE_TTL_COMMENTS = int(os.getenv("CACHE_TTL_COMMENTS", "30"))
CACHE_TTL_STATS_MAP = int(os.getenv("CACHE_TTL_STATS_MAP", "300"))
CACHE_TTL_STATS_MAP_DATA = int(os.getenv("CACHE_TTL_STATS_MAP_DATA", "86400"))
CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL", "")
CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "local_flavor")

if CACHE_BACKEND == "redis":
    if not CACHE_REDIS_URL:
        CACHE_REDIS_URL = _build_chat_redis_url()
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": CACHE_REDIS_URL,
            "TIMEOUT": CACHE_DEFAULT_TTL,
            "KEY_PREFIX": CACHE_KEY_PREFIX,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": f"{CACHE_KEY_PREFIX}_locmem",
            "TIMEOUT": CACHE_DEFAULT_TTL,
        }
    }

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", _build_chat_redis_url())
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "300"))
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "0") == "1"

COMMUNITY_AUDIT_BANNED_WORDS = [
    word.strip()
    for word in os.getenv("COMMUNITY_AUDIT_BANNED_WORDS", "").split(",")
    if word.strip()
]
ITEM_AUDIT_BANNED_WORDS = [
    word.strip()
    for word in os.getenv("ITEM_AUDIT_BANNED_WORDS", "").split(",")
    if word.strip()
]
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "0") == "1"
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "core.logging_filters.RequestIdFilter",
        },
    },
    "formatters": {
        "json": {
            "()": "core.logging_formatters.JsonLogFormatter",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_id"],
            "formatter": "json",
            "level": "INFO",
        },
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "filters": ["request_id"],
            "formatter": "json",
            "level": "INFO",
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "error.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "filters": ["request_id"],
            "formatter": "json",
            "level": "ERROR",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "app": {
            "handlers": ["console", "app_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "app.request": {
            "handlers": ["console", "app_file"],
            "level": "INFO",
            "propagate": False,
        },
        "app.exception": {
            "handlers": ["console", "app_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
