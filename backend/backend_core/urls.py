import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from backend_core.health import health_check, readiness_check

urlpatterns = [
    # Health probes (no auth, skipped by logging middleware)
    path("health/", health_check, name="health-check"),
    path("ready/", readiness_check, name="readiness-check"),
    path(os.getenv("ADMIN_URL_PATH", "management-console") + "/", admin.site.urls),
    # Email webhooks (for AWS SES/SNS notifications)
    path("api/v1/email/", include("apps.email.urls", namespace="email")),
    # Notifications API (preferences, history)
    path(
        "api/v1/notifications/",
        include("apps.notifications.urls", namespace="notifications"),
    ),
    # Authentication API (login, register, OAuth, etc.)
    path("api/v1/auth/", include("apps.auth.urls", namespace="authentication")),
    # Users API (current user, profile, avatar, memberships)
    path("api/v1/users/", include("apps.users.urls", namespace="users")),
    # Organization API (platform, business accounts, RBAC roles/members)
    path(
        "api/v1/platform/",
        include("apps.organization.platform.urls", namespace="platform"),
    ),
    path(
        "api/v1/business/",
        include("apps.organization.business.urls", namespace="business"),
    ),
    # RBAC shared endpoints (permissions list)
    path("api/v1/rbac/", include("apps.rbac.urls", namespace="rbac")),
    # Transaction API (invitations, requests, approvals)
    path(
        "api/v1/transactions/",
        include("apps.transaction.api.urls", namespace="transaction"),
    ),
    # Form Builder API (templates, responses, library)
    path("api/v1/forms/", include("apps.forms.api.urls", namespace="forms")),
    # CMS Admin API (sites, pages, templates, media, API keys)
    path("api/v1/cms/admin/", include("apps.cms.api.urls", namespace="cms")),
    # CMS Public API (read-only, API key authenticated)
    path(
        "api/v1/cms/public/",
        include("apps.cms.api.urls_public", namespace="cms-public"),
    ),
    # Explore API (search and discovery)
    path("api/v1/explore/", include("apps.explore.urls", namespace="explore")),
    # Network API (follow and connection management)
    path("api/v1/network/", include("apps.network.urls", namespace="network")),
    # Chat API (conversations, messages)
    path("api/v1/chat/", include("apps.chat.urls", namespace="chat")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # API schema and docs (development only — disabled in production)
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
