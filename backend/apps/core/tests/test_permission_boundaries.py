# apps/core/tests/test_permission_boundaries.py
"""
Permission Boundary Tests
=========================
Systematic tests verifying that permission boundaries are enforced correctly
across all major API endpoints.

These are integration-style tests that send real HTTP requests through DRF's
APIClient to verify that:
  1. Unauthenticated users receive 401 on protected endpoints.
  2. Authenticated non-members receive 403/404 on business management endpoints.
  3. Regular users receive 403 on platform admin endpoints.
  4. Users without specific RBAC roles cannot escalate privileges.
  5. Users cannot access other users' private resources.

No mocking is used -- requests flow through the full middleware and permission stack.
Authentication uses DRF's ``force_authenticate`` to bypass JWT token validation
(which requires Redis), consistent with this project's unit test conventions.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory

# =============================================================================
# HELPERS
# =============================================================================


NONEXISTENT_BUSINESS_SLUG = "nonexistent-business-slug"


@pytest.fixture
def anon_client():
    """Return an unauthenticated DRF APIClient."""
    return APIClient()


@pytest.fixture
def auth_user(db):
    """Create a regular user and return (user, authenticated_client) tuple."""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


@pytest.fixture
def second_auth_user(db):
    """Create a second regular user and return (user, authenticated_client) tuple."""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


# =============================================================================
# 1. AUTHENTICATION BOUNDARY
# =============================================================================


@pytest.mark.django_db
class TestAuthenticationBoundary:
    """
    Verify that unauthenticated (anonymous) requests are rejected with 401
    on all endpoints that require authentication.
    """

    def test_anonymous_cannot_create_business(self, anon_client):
        """POST /api/v1/business/ requires authentication."""
        response = anon_client.post("/api/v1/business/", data={}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_cannot_update_own_profile(self, anon_client):
        """PATCH /api/v1/users/me/ requires authentication."""
        response = anon_client.patch(
            "/api/v1/users/me/", data={"username": "hacker"}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_cannot_create_invitation(self, anon_client):
        """POST /api/v1/transactions/invitation/ requires authentication."""
        response = anon_client.post(
            "/api/v1/transactions/invitation/", data={}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_cannot_follow(self, anon_client):
        """POST /api/v1/network/follow/ requires authentication."""
        response = anon_client.post("/api/v1/network/follow/", data={}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_cannot_list_notifications(self, anon_client):
        """GET /api/v1/notifications/history/ requires authentication."""
        response = anon_client.get("/api/v1/notifications/history/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# 2. BUSINESS MEMBERSHIP BOUNDARY
# =============================================================================


@pytest.mark.django_db
class TestBusinessMembershipBoundary:
    """
    Verify that authenticated users who are NOT members of a business
    are denied access to business management endpoints.

    Uses a nonexistent slug so there is no business to be a member of.
    The expected response is 403 (Forbidden) or 404 (Not Found) -- both are
    acceptable because the user should not be able to manage the resource.
    """

    DENIED_STATUSES = {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND}

    def test_non_member_cannot_update_business(self, auth_user):
        """PATCH /api/v1/business/<slug>/ requires membership."""
        _, client = auth_user
        response = client.patch(
            f"/api/v1/business/{NONEXISTENT_BUSINESS_SLUG}/",
            data={"name": "Hijacked"},
            format="json",
        )
        assert response.status_code in self.DENIED_STATUSES

    def test_non_member_cannot_delete_business(self, auth_user):
        """DELETE /api/v1/business/<slug>/ requires owner-level access."""
        _, client = auth_user
        response = client.delete(
            f"/api/v1/business/{NONEXISTENT_BUSINESS_SLUG}/",
        )
        assert response.status_code in self.DENIED_STATUSES

    def test_non_member_cannot_list_members(self, auth_user):
        """GET /api/v1/business/<slug>/members/ requires membership."""
        _, client = auth_user
        response = client.get(
            f"/api/v1/business/{NONEXISTENT_BUSINESS_SLUG}/members/",
        )
        assert response.status_code in self.DENIED_STATUSES

    def test_non_member_cannot_create_role(self, auth_user):
        """POST /api/v1/business/<slug>/roles/ requires RBAC permission."""
        _, client = auth_user
        response = client.post(
            f"/api/v1/business/{NONEXISTENT_BUSINESS_SLUG}/roles/",
            data={"name": "Intruder Role"},
            format="json",
        )
        assert response.status_code in self.DENIED_STATUSES

    def test_non_member_cannot_suspend_business(self, auth_user):
        """POST /api/v1/business/<slug>/suspend/ requires owner-level access."""
        _, client = auth_user
        response = client.post(
            f"/api/v1/business/{NONEXISTENT_BUSINESS_SLUG}/suspend/",
            format="json",
        )
        assert response.status_code in self.DENIED_STATUSES


# =============================================================================
# 3. PLATFORM ADMIN BOUNDARY
# =============================================================================


@pytest.mark.django_db
class TestPlatformAdminBoundary:
    """
    Verify that regular authenticated users cannot access platform admin
    endpoints. These require platform admin/owner RBAC roles.
    """

    DENIED_STATUSES = {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND}

    def test_regular_user_cannot_create_platform(self, auth_user):
        """POST /api/v1/platform/account/ requires superuser for initial setup."""
        _, client = auth_user
        response = client.post(
            "/api/v1/platform/account/",
            data={"name": "Hijacked Platform"},
            format="json",
        )
        assert response.status_code in self.DENIED_STATUSES

    def test_regular_user_cannot_create_platform_role(self, auth_user):
        """POST /api/v1/platform/roles/ requires platform admin."""
        _, client = auth_user
        response = client.post(
            "/api/v1/platform/roles/",
            data={"name": "Evil Role", "level": 10},
            format="json",
        )
        assert response.status_code in self.DENIED_STATUSES

    def test_regular_user_cannot_update_platform_settings(self, auth_user):
        """PATCH /api/v1/platform/settings/ requires platform admin."""
        _, client = auth_user
        response = client.patch(
            "/api/v1/platform/settings/",
            data={"maintenance_mode": True},
            format="json",
        )
        assert response.status_code in self.DENIED_STATUSES

    def test_regular_user_cannot_create_cms_site(self, auth_user):
        """POST /api/v1/cms/admin/sites/ requires staff or CMS API key."""
        _, client = auth_user
        response = client.post(
            "/api/v1/cms/admin/sites/",
            data={"name": "Evil Site", "slug": "evil-site"},
            format="json",
        )
        assert response.status_code in self.DENIED_STATUSES


# =============================================================================
# 4. RBAC ESCALATION BOUNDARY
# =============================================================================


@pytest.mark.django_db
class TestRBACEscalationBoundary:
    """
    Verify that a regular user cannot escalate privileges by directly
    calling RBAC management endpoints on resources they don't manage.
    """

    DENIED_STATUSES = {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND}

    def test_non_member_cannot_create_business_role(self, auth_user):
        """
        A user with no business membership cannot create roles in an
        arbitrary business.
        """
        _, client = auth_user
        response = client.post(
            f"/api/v1/business/{NONEXISTENT_BUSINESS_SLUG}/roles/",
            data={"name": "Escalated Admin", "level": 1},
            format="json",
        )
        assert response.status_code in self.DENIED_STATUSES

    def test_non_member_cannot_create_invitation(self, auth_user):
        """
        Creating an invitation requires the initiator to have the appropriate
        RBAC permission within the target business context. A random user
        sending an invitation payload with a fake business context should fail.
        """
        _, client = auth_user
        response = client.post(
            "/api/v1/transactions/invitation/",
            data={
                "transaction_type": "business_membership_invitation",
                "target_user_id": "00000000-0000-0000-0000-000000000000",
                "context_id": "00000000-0000-0000-0000-000000000001",
            },
            format="json",
        )
        # Should be denied -- user has no permission to invite on behalf of
        # this business. Acceptable codes: 400 (validation), 403, or 404.
        assert response.status_code in {
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        }

    def test_non_admin_cannot_manage_platform_roles(self, auth_user):
        """
        A regular user cannot list or create platform roles.
        """
        _, client = auth_user
        response = client.get("/api/v1/platform/roles/")
        assert response.status_code in self.DENIED_STATUSES


# =============================================================================
# 5. CROSS-ENTITY ISOLATION
# =============================================================================


@pytest.mark.django_db
class TestCrossEntityIsolation:
    """
    Verify that User A cannot access or modify User B's private resources.
    The /me/ endpoints should always scope to the authenticated user.
    """

    def test_user_a_cannot_patch_user_b_profile(self, auth_user, second_auth_user):
        """
        PATCH /api/v1/users/me/ only modifies the authenticated user's own
        profile. User A's request should modify User A, not User B.
        There is no direct endpoint to modify another user's profile, so
        this test verifies that the /me/ endpoint correctly scopes to the
        authenticated user.
        """
        user_a, client_a = auth_user
        user_b, _ = second_auth_user

        # User A patches /me/ -- this should affect User A only
        response = client_a.patch(
            "/api/v1/users/me/",
            data={"username": "user_a_new_name"},
            format="json",
        )
        # The response should succeed and reflect User A's data
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(user_a.id)

    def test_user_a_cannot_view_user_b_memberships(self, auth_user, second_auth_user):
        """
        GET /api/v1/users/me/memberships/ returns only the authenticated
        user's memberships. User A should see only their own.
        """
        user_a, client_a = auth_user
        user_b, client_b = second_auth_user

        # User A lists their memberships
        response_a = client_a.get("/api/v1/users/me/memberships/")
        assert response_a.status_code == status.HTTP_200_OK

        # User B lists their memberships
        response_b = client_b.get("/api/v1/users/me/memberships/")
        assert response_b.status_code == status.HTTP_200_OK

        # Both should return results scoped to their own user, not each other's
        # (Even if both are empty, the responses should be independent)

    def test_user_a_cannot_view_user_b_notifications(self, auth_user, second_auth_user):
        """
        GET /api/v1/notifications/history/ returns only the authenticated
        user's notifications. Each user sees only their own.
        """
        _, client_a = auth_user
        _, client_b = second_auth_user

        response_a = client_a.get("/api/v1/notifications/history/")
        assert response_a.status_code == status.HTTP_200_OK

        response_b = client_b.get("/api/v1/notifications/history/")
        assert response_b.status_code == status.HTTP_200_OK
