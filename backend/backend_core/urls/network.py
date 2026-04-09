"""
Network URL routes — follow and connection management.

Gated by systems.network in the coordinator.
"""

from django.urls import include, path

urlpatterns = [
    path("api/v1/network/", include("apps.network.urls", namespace="network")),
]
