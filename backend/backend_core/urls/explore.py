"""
Explore URL routes — search and discovery.

Gated by systems.explore in the coordinator.
"""

from django.urls import include, path

urlpatterns = [
    path("api/v1/explore/", include("apps.explore.urls", namespace="explore")),
]
