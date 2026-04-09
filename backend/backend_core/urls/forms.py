"""
Form builder URL routes — templates, responses, library.

Gated by systems.forms in the coordinator.
"""

from django.urls import include, path

urlpatterns = [
    path("api/v1/forms/", include("apps.forms.api.urls", namespace="forms")),
]
