"""
CMS URL routes — admin API + business API + public (API-key authenticated) API.

Gated by systems.cms in the coordinator.
"""

from django.urls import include, path

urlpatterns = [
    # CMS Admin API (platform-scoped: sites, pages, templates, media, API keys)
    path("api/v1/cms/admin/", include("apps.cms.api.urls", namespace="cms")),
    # CMS Business API (business-scoped: catalog, library, sites, pages, media, keys)
    path(
        "api/v1/cms/business/",
        include("apps.cms.api.urls_business", namespace="cms-business"),
    ),
    # CMS Public API (read-only, API key authenticated)
    path(
        "api/v1/cms/public/",
        include("apps.cms.api.urls_public", namespace="cms-public"),
    ),
]
