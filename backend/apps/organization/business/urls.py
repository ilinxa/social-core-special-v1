# apps/organization/business/urls.py
"""
Business URL Configuration.

URL patterns:
    /api/v1/business/                       GET, POST
    /api/v1/business/my/                    GET
    /api/v1/business/id/<uuid>/             GET
    /api/v1/business/<slug>/                GET, PATCH, DELETE
    /api/v1/business/<slug>/profile/        GET, PATCH
    /api/v1/business/<slug>/slug/           PATCH
    /api/v1/business/<slug>/suspend/        POST
    /api/v1/business/<slug>/reactivate/     POST
    /api/v1/business/<slug>/archive/        POST

    RBAC (roles and members):
    /api/v1/business/<slug>/roles/          GET, POST
    /api/v1/business/<slug>/roles/{id}/     GET, PATCH, DELETE
    /api/v1/business/<slug>/roles/{id}/permissions/     POST, DELETE
    /api/v1/business/<slug>/members/        GET
    /api/v1/business/<slug>/members/leave/  POST
    /api/v1/business/<slug>/members/{id}/   GET
    /api/v1/business/<slug>/members/{id}/role/      PATCH
    /api/v1/business/<slug>/members/{id}/suspend/   POST
    /api/v1/business/<slug>/members/{id}/remove/    POST
    /api/v1/business/<slug>/members/{id}/ban/       POST
"""

from django.urls import path

from apps.organization.business.views import (
    BusinessArchiveView,
    BusinessByIdView,
    BusinessDetailView,
    BusinessListCreateView,
    BusinessProfileView,
    BusinessProfileVisibilityView,
    BusinessReactivateView,
    BusinessSlugUpdateView,
    BusinessSuspendView,
    MyBusinessListView,
)
from apps.rbac import views as rbac_views

app_name = "business"

urlpatterns = [
    # List and create
    path("", BusinessListCreateView.as_view(), name="list-create"),
    # User's businesses
    path("my/", MyBusinessListView.as_view(), name="my-list"),
    # By UUID
    path("id/<uuid:business_id>/", BusinessByIdView.as_view(), name="detail-by-id"),
    # By slug - actions
    path("<slug:slug>/slug/", BusinessSlugUpdateView.as_view(), name="slug-update"),
    path("<slug:slug>/profile/", BusinessProfileView.as_view(), name="profile"),
    path("<slug:slug>/profile/visibility/", BusinessProfileVisibilityView.as_view(), name="profile-visibility"),
    path("<slug:slug>/suspend/", BusinessSuspendView.as_view(), name="suspend"),
    path("<slug:slug>/reactivate/", BusinessReactivateView.as_view(), name="reactivate"),
    path("<slug:slug>/archive/", BusinessArchiveView.as_view(), name="archive"),

    # RBAC - Roles
    path("<slug:business_slug>/roles/", rbac_views.BusinessRoleListView.as_view(), name="role-list"),
    path("<slug:business_slug>/roles/<uuid:role_id>/", rbac_views.BusinessRoleDetailView.as_view(), name="role-detail"),
    path("<slug:business_slug>/roles/<uuid:role_id>/permissions/", rbac_views.BusinessRolePermissionView.as_view(), name="role-permissions"),

    # RBAC - Members
    path("<slug:business_slug>/members/", rbac_views.BusinessMemberListView.as_view(), name="member-list"),
    path("<slug:business_slug>/members/leave/", rbac_views.BusinessMemberLeaveView.as_view(), name="member-leave"),
    path("<slug:business_slug>/members/<uuid:membership_id>/", rbac_views.BusinessMemberDetailView.as_view(), name="member-detail"),
    path("<slug:business_slug>/members/<uuid:membership_id>/role/", rbac_views.BusinessMemberRoleView.as_view(), name="member-role"),
    path("<slug:business_slug>/members/<uuid:membership_id>/suspend/", rbac_views.BusinessMemberSuspendView.as_view(), name="member-suspend"),
    path("<slug:business_slug>/members/<uuid:membership_id>/remove/", rbac_views.BusinessMemberRemoveView.as_view(), name="member-remove"),
    path("<slug:business_slug>/members/<uuid:membership_id>/ban/", rbac_views.BusinessMemberBanView.as_view(), name="member-ban"),
    path("<slug:business_slug>/members/<uuid:membership_id>/reactivate/", rbac_views.BusinessMemberReactivateView.as_view(), name="member-reactivate"),

    # By slug - detail (must be last to avoid matching action paths)
    path("<slug:slug>/", BusinessDetailView.as_view(), name="detail"),
]
