

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack



os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_core.settings.production")
# Initialize Django ASGI application early to ensure AppRegistry is populated
django_asgi_app = get_asgi_application()
from backend_core.routing import websocket_urlpatterns  # Import after Django 

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})