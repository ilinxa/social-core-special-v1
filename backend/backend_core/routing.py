# backend_core/routing.py

from django.urls import path

from apps.core.feature_config import feature_config

websocket_urlpatterns = []

if feature_config.is_system_enabled("chat"):
    from apps.chat.consumers import ChatConsumer

    websocket_urlpatterns = [
        path("ws/chat/", ChatConsumer.as_asgi()),
    ]
