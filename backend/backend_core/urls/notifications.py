"""
Notification URL routes — preferences, history, scopes, types.

Gated by systems.notifications in the coordinator.
"""

from django.urls import include, path

urlpatterns = [
    path(
        "api/v1/notifications/",
        include("apps.notifications.urls", namespace="notifications"),
    ),
]
