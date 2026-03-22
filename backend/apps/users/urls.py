"""
User URL Configuration
======================
URL patterns for the users app.

URL patterns:
    /api/v1/users/me/                   GET, PATCH       (authenticated)
    /api/v1/users/me/profile/           GET, PATCH       (authenticated)
    /api/v1/users/me/avatar/            GET, POST, DELETE (authenticated)
    /api/v1/users/me/memberships/       GET              (authenticated)
    /api/v1/users/me/memberships/{id}/  GET              (authenticated)
    /api/v1/users/check-username/       GET              (authenticated)
    /api/v1/users/<username>/           GET              (authenticated, public profile)
"""

from django.urls import path

from apps.rbac import views as rbac_views
from apps.users import views

app_name = "users"

urlpatterns = [
    # Current user endpoints
    path("me/", views.CurrentUserView.as_view(), name="me"),
    path("me/profile/", views.ProfileView.as_view(), name="profile"),
    path("me/avatar/", views.AvatarView.as_view(), name="avatar"),
    path("me/cover-image/", views.CoverImageView.as_view(), name="cover-image"),
    path(
        "me/profile/visibility/",
        views.UserProfileVisibilityView.as_view(),
        name="profile-visibility",
    ),
    # RBAC memberships (user's own memberships)
    path(
        "me/memberships/",
        rbac_views.MyMembershipsListView.as_view(),
        name="my-memberships",
    ),
    path(
        "me/memberships/<uuid:membership_id>/",
        rbac_views.MyMembershipDetailView.as_view(),
        name="my-membership-detail",
    ),
    # Username availability check
    path("check-username/", views.CheckUsernameView.as_view(), name="check-username"),
    # Public user profile (must be LAST — catches any username slug)
    path("<str:username>/", views.UserPublicDetailView.as_view(), name="public-detail"),
]
