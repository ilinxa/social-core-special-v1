"""
Always-on URL routes — Layer 0 foundation.

These routes are included in every deployment regardless of feature config:
- Health probes (liveness + readiness)
- Admin console
- Auth, users, email, RBAC
"""

import os

from django.contrib import admin
from django.urls import include, path

from backend_core.health import health_check, readiness_check

urlpatterns = [
    # Health probes (no auth, skipped by logging middleware)
    path("health/", health_check, name="health-check"),
    path("ready/", readiness_check, name="readiness-check"),
    path(os.getenv("ADMIN_URL_PATH", "management-console") + "/", admin.site.urls),
    # Email webhooks (for AWS SES/SNS notifications)
    path("api/v1/email/", include("apps.email.urls", namespace="email")),
    # Authentication API (login, register, OAuth, etc.)
    path("api/v1/auth/", include("apps.auth.urls", namespace="authentication")),
    # Users API (current user, profile, avatar, memberships)
    path("api/v1/users/", include("apps.users.urls", namespace="users")),
    # RBAC shared endpoints (permissions list)
    path("api/v1/rbac/", include("apps.rbac.urls", namespace="rbac")),
]
