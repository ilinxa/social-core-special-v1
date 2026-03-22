# apps/organization/tests/platform/test_policies.py
"""
Tests for PlatformPolicy RBAC-based authorization.
"""

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.core.constants import AccountType
from apps.organization.platform.policies import PlatformPolicy
from apps.organization.tests.factories import UserFactory
from apps.rbac.selectors import RoleSelector
from apps.rbac.services import RBACService

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def platform_with_rbac(platform_account):
    """
    Ensure platform account has RBAC roles initialized.

    Platform roles are normally created by a data migration, but in
    test DB they may not exist. This fixture ensures they're present.
    """
    from apps.rbac.models import Role

    # Check if roles already exist
    exists = Role.objects.filter(
        account_type=AccountType.PLATFORM,
        account_id=platform_account.id,
    ).exists()
    if not exists:
        RBACService.initialize_platform_account(platform_id=platform_account.id)
    return platform_account


@pytest.fixture
def platform_owner_user(db, platform_with_rbac):
    """Create a user with Platform Owner role membership."""
    owner = UserFactory(username="platowner", email="platowner@example.com")
    owner_role = RoleSelector.get_owner_role(
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
    )
    RBACService.create_membership(
        user=owner,
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
        role_id=owner_role.id,
        created_by=owner,
    )
    return owner


@pytest.fixture
def platform_admin_user(db, platform_with_rbac):
    """Create a user with Platform Admin role membership."""
    from apps.rbac.models import Role

    admin = UserFactory(username="platadmin", email="platadmin@example.com")
    admin_role = Role.objects.get(
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
        name="Platform Admin",
    )
    RBACService.create_membership(
        user=admin,
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
        role_id=admin_role.id,
        created_by=admin,
    )
    return admin


# =============================================================================
# TESTS
# =============================================================================


@pytest.mark.django_db
class TestPlatformPolicyCanView:
    """Tests for can_view policy — publicly viewable by anyone."""

    def test_authenticated_user_can_view(self, user):
        assert PlatformPolicy.can_view(user=user) is True

    def test_anonymous_user_can_view(self):
        assert PlatformPolicy.can_view(user=AnonymousUser()) is True


@pytest.mark.django_db
class TestPlatformPolicyCanConfigure:
    """Tests for can_configure policy — superuser only."""

    def test_superuser_can_configure(self, superuser):
        assert PlatformPolicy.can_configure(user=superuser) is True

    def test_staff_cannot_configure(self, staff_user):
        assert PlatformPolicy.can_configure(user=staff_user) is False

    def test_regular_user_cannot_configure(self, user):
        assert PlatformPolicy.can_configure(user=user) is False


@pytest.mark.django_db
class TestPlatformPolicyCanUpdateProfile:
    """Tests for can_update_profile — staff/superuser OR RBAC permission."""

    def test_staff_can_update_profile(self, staff_user):
        assert PlatformPolicy.can_update_profile(user=staff_user) is True

    def test_superuser_can_update_profile(self, superuser):
        assert PlatformPolicy.can_update_profile(user=superuser) is True

    def test_platform_owner_can_update_profile(self, platform_owner_user):
        """Platform Owner has all permissions via RBAC."""
        assert PlatformPolicy.can_update_profile(user=platform_owner_user) is True

    def test_platform_admin_can_update_profile(self, platform_admin_user):
        """Platform Admin has can_edit_profile via platform_only scope."""
        assert PlatformPolicy.can_update_profile(user=platform_admin_user) is True

    def test_non_member_cannot_update_profile(
        self, non_member_user, platform_with_rbac
    ):
        """User with no platform membership cannot update profile."""
        assert PlatformPolicy.can_update_profile(user=non_member_user) is False

    def test_anonymous_cannot_update_profile(self):
        assert PlatformPolicy.can_update_profile(user=AnonymousUser()) is False


@pytest.mark.django_db
class TestPlatformPolicyCanUpdateSettings:
    """Tests for can_update_settings — superuser OR RBAC permission."""

    def test_superuser_can_update_settings(self, superuser):
        assert PlatformPolicy.can_update_settings(user=superuser) is True

    def test_platform_owner_can_update_settings(self, platform_owner_user):
        """Platform Owner has all permissions via RBAC."""
        assert PlatformPolicy.can_update_settings(user=platform_owner_user) is True

    def test_staff_cannot_update_settings_without_rbac(
        self, staff_user, platform_with_rbac
    ):
        """Staff without RBAC membership cannot update settings."""
        assert PlatformPolicy.can_update_settings(user=staff_user) is False

    def test_platform_admin_can_update_settings(self, platform_admin_user):
        """Platform Admin has can_edit_business via platform_only scope (migration 0005)."""
        assert PlatformPolicy.can_update_settings(user=platform_admin_user) is True

    def test_non_member_cannot_update_settings(
        self, non_member_user, platform_with_rbac
    ):
        assert PlatformPolicy.can_update_settings(user=non_member_user) is False


@pytest.mark.django_db
class TestPlatformPolicyGetViewerPermissions:
    """Tests for get_viewer_permissions aggregation."""

    def test_owner_gets_all_permissions(self, platform_owner_user):
        """Platform Owner should see all permissions as True."""
        perms = PlatformPolicy.get_viewer_permissions(user=platform_owner_user)

        assert perms["can_view"] is True
        assert perms["can_edit_profile"] is True
        assert perms["can_edit_settings"] is True

    def test_admin_gets_edit_permissions(self, platform_admin_user):
        """Platform Admin can view, edit profile, and edit settings (migration 0005)."""
        perms = PlatformPolicy.get_viewer_permissions(user=platform_admin_user)

        assert perms["can_view"] is True
        assert perms["can_edit_profile"] is True
        assert perms["can_edit_settings"] is True

    def test_non_member_gets_view_only(self, non_member_user, platform_with_rbac):
        """Non-member can view but not edit."""
        perms = PlatformPolicy.get_viewer_permissions(user=non_member_user)

        assert perms["can_view"] is True
        assert perms["can_edit_profile"] is False
        assert perms["can_edit_settings"] is False

    def test_anonymous_gets_view_only(self):
        """Anonymous user can view but not edit."""
        perms = PlatformPolicy.get_viewer_permissions(user=AnonymousUser())

        assert perms["can_view"] is True
        assert perms["can_edit_profile"] is False
        assert perms["can_edit_settings"] is False
