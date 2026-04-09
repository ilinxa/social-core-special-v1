# apps/organization/tests/platform/test_views.py
"""
Tests for Platform views/API endpoints.
"""

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestPlatformAccountView:
    """Tests for PlatformAccountView endpoints."""

    def test_get_platform_account_authenticated(
        self, authenticated_client, platform_account, platform_profile
    ):
        """Test getting platform account as authenticated user."""
        response = authenticated_client.get("/api/v1/platform/account/")

        assert response.status_code == 200
        assert "id" in response.data
        assert "is_configured" in response.data
        assert "profile" in response.data

    def test_get_platform_account_unauthenticated(self, api_client, platform_account):
        """Test that unauthenticated users can access platform account (public)."""
        response = api_client.get("/api/v1/platform/account/")

        assert response.status_code == 200

    def test_configure_platform_as_superuser(self, admin_client, db):
        """Test configuring platform as superuser."""
        # Delete existing platform
        from apps.organization.platform.models import PlatformAccount

        PlatformAccount.objects.all().delete()

        response = admin_client.post(
            "/api/v1/platform/account/",
            {"name": "New Platform", "settings": {"key": "value"}},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["is_configured"] is True
        assert response.data["profile"]["name"] == "New Platform"

    def test_configure_platform_as_regular_user_forbidden(
        self, authenticated_client, platform_account
    ):
        """Test that regular users cannot configure platform."""
        response = authenticated_client.post(
            "/api/v1/platform/account/",
            {"name": "New Platform"},
            format="json",
        )

        assert response.status_code == 403

    def test_configure_already_configured_platform(
        self, admin_client, configured_platform
    ):
        """Test that configuring already configured platform fails."""
        response = admin_client.post(
            "/api/v1/platform/account/",
            {"name": "New Platform"},
            format="json",
        )

        assert response.status_code == 409


@pytest.mark.django_db
class TestPlatformAccountViewPermissions:
    """Tests for _permissions injection in platform account GET responses."""

    def test_get_response_includes_permissions(
        self,
        authenticated_client,
        platform_account,
        platform_profile,
    ):
        """GET account response includes _permissions dict."""
        response = authenticated_client.get("/api/v1/platform/account/")

        assert response.status_code == 200
        assert "_permissions" in response.data
        assert isinstance(response.data["_permissions"], dict)

    def test_regular_user_gets_view_only_permissions(
        self,
        authenticated_client,
        platform_account,
        platform_profile,
    ):
        """Regular authenticated user can view but not edit."""
        response = authenticated_client.get("/api/v1/platform/account/")

        perms = response.data["_permissions"]
        assert perms["can_view"] is True
        assert perms["can_edit_profile"] is False
        assert perms["can_edit_settings"] is False

    def test_platform_admin_gets_edit_permissions(
        self,
        platform_admin_client,
        platform_account,
        platform_profile,
    ):
        """Platform Admin (RBAC) can edit profile and settings."""
        response = platform_admin_client.get("/api/v1/platform/account/")

        perms = response.data["_permissions"]
        assert perms["can_view"] is True
        assert perms["can_edit_profile"] is True
        assert perms["can_edit_settings"] is True

    def test_platform_owner_gets_all_permissions(
        self,
        platform_owner_client,
        platform_account,
        platform_profile,
    ):
        """Platform Owner (RBAC) gets all permissions."""
        response = platform_owner_client.get("/api/v1/platform/account/")

        perms = response.data["_permissions"]
        assert perms["can_view"] is True
        assert perms["can_edit_profile"] is True
        assert perms["can_edit_settings"] is True

    def test_post_response_excludes_permissions(self, admin_client, db):
        """POST (configure) response does NOT include _permissions."""
        from apps.organization.platform.models import PlatformAccount

        PlatformAccount.objects.all().delete()

        response = admin_client.post(
            "/api/v1/platform/account/",
            {"name": "Test Platform"},
            format="json",
        )

        assert response.status_code == 201
        assert "_permissions" not in response.data


@pytest.mark.django_db
class TestPlatformProfileViewPermissions:
    """Tests for _permissions injection in platform profile GET responses."""

    def test_get_profile_includes_permissions(
        self,
        authenticated_client,
        platform_profile,
    ):
        """GET profile response includes _permissions dict."""
        response = authenticated_client.get("/api/v1/platform/profile/")

        assert response.status_code == 200
        assert "_permissions" in response.data

    def test_patch_profile_excludes_permissions(
        self,
        platform_admin_client,
        platform_profile,
    ):
        """PATCH profile response does NOT include _permissions."""
        response = platform_admin_client.patch(
            "/api/v1/platform/profile/",
            {"tagline": "Updated"},
            format="json",
        )

        assert response.status_code == 200
        assert "_permissions" not in response.data


@pytest.mark.django_db
class TestPlatformProfileView:
    """Tests for PlatformProfileView endpoints."""

    def test_get_platform_profile(self, authenticated_client, platform_profile):
        """Test getting platform profile."""
        response = authenticated_client.get("/api/v1/platform/profile/")

        assert response.status_code == 200
        assert "name" in response.data
        assert "tagline" in response.data

    def test_update_platform_profile_as_admin(
        self, platform_admin_client, platform_profile
    ):
        """Test updating platform profile as Platform Admin (RBAC)."""
        response = platform_admin_client.patch(
            "/api/v1/platform/profile/",
            {"name": "Updated Platform", "tagline": "New tagline"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["name"] == "Updated Platform"
        assert response.data["tagline"] == "New tagline"

    def test_update_platform_profile_as_regular_user_forbidden(
        self, authenticated_client, platform_profile
    ):
        """Test that regular users cannot update platform profile."""
        response = authenticated_client.patch(
            "/api/v1/platform/profile/",
            {"name": "Hacked Platform"},
            format="json",
        )

        assert response.status_code == 403

    def test_update_platform_profile_partial(
        self, platform_admin_client, platform_profile
    ):
        """Test partial profile update as Platform Admin (RBAC)."""
        original_name = platform_profile.name

        response = platform_admin_client.patch(
            "/api/v1/platform/profile/",
            {"tagline": "Only tagline changed"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["name"] == original_name
        assert response.data["tagline"] == "Only tagline changed"


@pytest.mark.django_db
class TestPlatformSettingsView:
    """Tests for PlatformSettingsView endpoints."""

    def test_update_settings_as_owner(self, platform_owner_client, platform_account):
        """Test updating platform settings as Platform Owner (RBAC)."""
        response = platform_owner_client.patch(
            "/api/v1/platform/settings/",
            {"settings": {"new_feature": True}},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["settings"]["new_feature"] is True

    def test_update_settings_as_staff_forbidden(self, staff_client, platform_account):
        """Test that staff cannot update platform settings."""
        response = staff_client.patch(
            "/api/v1/platform/settings/",
            {"settings": {"hacked": True}},
            format="json",
        )

        assert response.status_code == 403

    def test_update_settings_as_regular_user_forbidden(
        self, authenticated_client, platform_account
    ):
        """Test that regular users cannot update platform settings."""
        response = authenticated_client.patch(
            "/api/v1/platform/settings/",
            {"settings": {"hacked": True}},
            format="json",
        )

        assert response.status_code == 403

    def test_update_settings_merges_existing(
        self, platform_owner_client, platform_account
    ):
        """Test that settings are merged, not replaced."""
        # Set initial settings
        platform_account.settings = {"existing": "value"}
        platform_account.save()

        response = platform_owner_client.patch(
            "/api/v1/platform/settings/",
            {"settings": {"new": "setting"}},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["settings"]["existing"] == "value"
        assert response.data["settings"]["new"] == "setting"


@pytest.mark.django_db
class TestPlatformAccountViewAnonymous:
    """Tests for anonymous (unauthenticated) access to PlatformAccountView."""

    def test_anonymous_get_returns_200(
        self, api_client, platform_account, platform_profile
    ):
        """Anonymous GET to /api/v1/platform/account/ returns 200 when platform exists."""
        response = api_client.get("/api/v1/platform/account/")

        assert response.status_code == 200
        assert "id" in response.data
        assert "is_configured" in response.data

    def test_anonymous_get_returns_permissions(
        self,
        api_client,
        platform_account,
        platform_profile,
    ):
        """Anonymous GET returns _permissions with can_view=True and all others False."""
        response = api_client.get("/api/v1/platform/account/")

        assert response.status_code == 200
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_view"] is True
        assert perms["can_edit_profile"] is False
        assert perms["can_edit_settings"] is False

    def test_anonymous_post_returns_403(self, api_client, platform_account):
        """Anonymous POST to /api/v1/platform/account/ returns 403 (configure requires superuser)."""
        response = api_client.post(
            "/api/v1/platform/account/",
            {"name": "Hacked Platform"},
            format="json",
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestPlatformRelationshipInjection:
    """Tests for _relationship injection on platform account detail."""

    def test_anonymous_get_no_relationship(
        self,
        api_client,
        platform_account,
        platform_profile,
    ):
        """Anonymous GET does NOT include _relationship."""
        response = api_client.get("/api/v1/platform/account/")
        assert response.status_code == 200
        assert "_relationship" not in response.data

    def test_authenticated_non_member_gets_null_relationship(
        self,
        authenticated_client,
        platform_account,
        platform_profile,
    ):
        """Authenticated non-member GET includes _relationship with null values."""
        response = authenticated_client.get("/api/v1/platform/account/")
        assert response.status_code == 200
        assert "_relationship" in response.data
        rel = response.data["_relationship"]
        assert rel["membership_status"] is None
        assert rel["active_transaction"] is None

    def test_platform_member_gets_relationship_with_status(
        self,
        api_client,
        platform_account,
        platform_profile,
        another_user,
    ):
        """Platform member GET includes _relationship with membership_status."""
        from apps.core.constants import AccountType, MembershipStatus
        from apps.rbac.models import Membership, Role

        # Create a platform membership for another_user
        owner_role = Role.objects.filter(
            account_type=AccountType.PLATFORM,
            account_id=platform_account.id,
            name="Platform Owner",
        ).first()
        if not owner_role:
            owner_role = Role.objects.create(
                name="Platform Owner",
                account_type=AccountType.PLATFORM,
                account_id=platform_account.id,
                level=0,
                is_system_role=True,
            )
        Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform_account.id,
            role=owner_role,
            is_owner=True,
            status=MembershipStatus.ACTIVE,
        )

        api_client.force_authenticate(user=another_user)
        response = api_client.get("/api/v1/platform/account/")

        assert response.status_code == 200
        assert "_relationship" in response.data
        rel = response.data["_relationship"]
        assert rel["membership_status"] == "active"

    def test_non_member_relationship_includes_follow_fields(
        self,
        authenticated_client,
        platform_account,
        platform_profile,
    ):
        """Authenticated non-member relationship includes follow fields."""
        response = authenticated_client.get("/api/v1/platform/account/")
        assert response.status_code == 200
        rel = response.data["_relationship"]
        assert rel["follow_status"] is None
        assert rel["follow_id"] is None
        assert rel["active_follow_transaction"] is None

    def test_active_follow_shows_follow_id(
        self,
        api_client,
        platform_account,
        platform_profile,
    ):
        """Following the platform populates follow_id in _relationship."""
        from apps.network.tests.factories import FollowFactory
        from apps.users.tests.factories import UserFactory

        follower = UserFactory()
        follow = FollowFactory(
            follower=follower,
            followee_type="platform",
            followee_id=platform_account.id,
        )

        api_client.force_authenticate(user=follower)
        response = api_client.get("/api/v1/platform/account/")
        assert response.status_code == 200
        rel = response.data["_relationship"]
        assert rel["follow_status"] == "active"
        assert rel["follow_id"] == str(follow.id)

    def test_update_settings_open_member_request(
        self,
        platform_owner_client,
        platform_account,
    ):
        """Platform Owner can update open_member_request setting."""
        response = platform_owner_client.patch(
            "/api/v1/platform/settings/",
            {"open_member_request": False},
            format="json",
        )

        assert response.status_code == 200
        platform_account.refresh_from_db()
        assert platform_account.open_member_request is False

    def test_non_member_update_settings_denied(
        self,
        authenticated_client,
        platform_account,
    ):
        """Non-superuser cannot update platform settings."""
        response = authenticated_client.patch(
            "/api/v1/platform/settings/",
            {"open_member_request": False},
            format="json",
        )

        assert response.status_code == 403
