"""
Chat URL routes — conversations, messages.

Gated by systems.chat in the coordinator.
"""

from django.urls import include, path

urlpatterns = [
    path("api/v1/chat/", include("apps.chat.urls", namespace="chat")),
]
