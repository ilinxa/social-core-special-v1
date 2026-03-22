import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_core.settings.production")
# Initialize Django ASGI application early to ensure AppRegistry is populated
django_asgi_app = get_asgi_application()
from apps.auth.middleware import JWTAuthMiddlewareStack  # noqa: E402
from backend_core.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
