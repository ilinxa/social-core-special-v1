"""
Development-only URL routes — API schema, docs, profiling, media serving.

Gated by settings.DEBUG in the coordinator.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# API schema and docs
urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if "silk" in settings.INSTALLED_APPS:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
