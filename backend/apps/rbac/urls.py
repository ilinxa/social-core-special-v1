# apps/rbac/urls.py
"""
RBAC URL Configuration

Three URL sets:
1. Business context: /api/v1/business/{slug}/
2. Platform context: /api/v1/platform/
3. User context: /api/v1/me/memberships/
"""

from django.urls import path

from apps.rbac import views

app_name = "rbac"


# Business context URLs - to be included at /api/v1/business/<business_slug>/
business_urlpatterns = [
    # Roles
    path("roles/", views.BusinessRoleListView.as_view(), name="business-role-list"),
    path("roles/<uuid:role_id>/", views.BusinessRoleDetailView.as_view(), name="business-role-detail"),
    path("roles/<uuid:role_id>/permissions/", views.BusinessRolePermissionView.as_view(), name="business-role-permissions"),

    # Members
    path("members/", views.BusinessMemberListView.as_view(), name="business-member-list"),
    path("members/leave/", views.BusinessMemberLeaveView.as_view(), name="business-member-leave"),
    path("members/<uuid:membership_id>/", views.BusinessMemberDetailView.as_view(), name="business-member-detail"),
    path("members/<uuid:membership_id>/role/", views.BusinessMemberRoleView.as_view(), name="business-member-role"),
    path("members/<uuid:membership_id>/suspend/", views.BusinessMemberSuspendView.as_view(), name="business-member-suspend"),
    path("members/<uuid:membership_id>/remove/", views.BusinessMemberRemoveView.as_view(), name="business-member-remove"),
    path("members/<uuid:membership_id>/ban/", views.BusinessMemberBanView.as_view(), name="business-member-ban"),
    path("members/<uuid:membership_id>/reactivate/", views.BusinessMemberReactivateView.as_view(), name="business-member-reactivate"),
]

# Platform context URLs - to be included at /api/v1/platform/
platform_urlpatterns = [
    # Roles
    path("roles/", views.PlatformRoleListView.as_view(), name="platform-role-list"),
    path("roles/<uuid:role_id>/", views.PlatformRoleDetailView.as_view(), name="platform-role-detail"),
    path("roles/<uuid:role_id>/permissions/", views.PlatformRolePermissionView.as_view(), name="platform-role-permissions"),

    # Members
    path("members/", views.PlatformMemberListView.as_view(), name="platform-member-list"),
    path("members/leave/", views.PlatformMemberLeaveView.as_view(), name="platform-member-leave"),
    path("members/<uuid:membership_id>/", views.PlatformMemberDetailView.as_view(), name="platform-member-detail"),
    path("members/<uuid:membership_id>/role/", views.PlatformMemberRoleView.as_view(), name="platform-member-role"),
    path("members/<uuid:membership_id>/suspend/", views.PlatformMemberSuspendView.as_view(), name="platform-member-suspend"),
    path("members/<uuid:membership_id>/remove/", views.PlatformMemberRemoveView.as_view(), name="platform-member-remove"),
    path("members/<uuid:membership_id>/ban/", views.PlatformMemberBanView.as_view(), name="platform-member-ban"),
    path("members/<uuid:membership_id>/reactivate/", views.PlatformMemberReactivateView.as_view(), name="platform-member-reactivate"),
]

# User context URLs - to be included at /api/v1/me/
user_urlpatterns = [
    path("memberships/", views.MyMembershipsListView.as_view(), name="my-memberships"),
    path("memberships/<uuid:membership_id>/", views.MyMembershipDetailView.as_view(), name="my-membership-detail"),
]

# Shared URLs (permissions list)
shared_urlpatterns = [
    path("permissions/", views.PermissionListView.as_view(), name="permission-list"),
]

# Main urlpatterns - for registration at app level
urlpatterns = shared_urlpatterns
