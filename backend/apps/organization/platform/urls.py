# apps/organization/platform/urls.py
"""
Platform URL Configuration.

URL patterns:
    /api/v1/platform/account/     GET, POST
    /api/v1/platform/profile/     GET, PATCH
    /api/v1/platform/settings/    PATCH

    RBAC (roles and members):
    /api/v1/platform/roles/       GET, POST
    /api/v1/platform/roles/{id}/  GET, PATCH, DELETE
    /api/v1/platform/members/     GET
    /api/v1/platform/members/leave/     POST
    /api/v1/platform/members/{id}/      GET
    /api/v1/platform/members/{id}/role/     PATCH
    /api/v1/platform/members/{id}/suspend/  POST
    /api/v1/platform/members/{id}/remove/   POST
    /api/v1/platform/members/{id}/ban/      POST
"""

from django.urls import path

from apps.organization.platform.views import (
    PlatformAccountView,
    PlatformProfileView,
    PlatformSettingsView,
)
from apps.rbac.urls import platform_urlpatterns
from apps.users.views import ApprovedBusinessCreatorsListView

app_name = "platform"

urlpatterns = [
    path("account/", PlatformAccountView.as_view(), name="account"),
    path("profile/", PlatformProfileView.as_view(), name="profile"),
    path("settings/", PlatformSettingsView.as_view(), name="settings"),
    path("approved-creators/", ApprovedBusinessCreatorsListView.as_view(), name="approved-creators"),
] + platform_urlpatterns
