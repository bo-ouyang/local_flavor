import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.conf import settings  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402


django_asgi_app = get_asgi_application()

if getattr(settings, "CHAT_ENABLE_WS", False):
    from channels.routing import ProtocolTypeRouter, URLRouter

    from config.routing import websocket_urlpatterns
    from messaging.ws_auth import TokenAuthMiddleware, WebSocketOriginAuthValidator

    application = ProtocolTypeRouter(
        {
            "http": django_asgi_app,
            "websocket": WebSocketOriginAuthValidator(
                TokenAuthMiddleware(URLRouter(websocket_urlpatterns))
            ),
        }
    )
else:
    application = django_asgi_app
