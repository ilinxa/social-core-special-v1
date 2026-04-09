# apps/organization/tests/business/test_policies.py
"""
Tests for BusinessPolicy RBAC-based authorization.

Authorization is fully RBAC-based (Decision 3 — gconsole Phase 1).
No is_staff/is_superuser bypass exists. All governance access requires
global-scoped permissions via platform membership.
"""

import pytest

from apps.core.constants import AccountType
from apps.organization.business.policies import BusinessPolicy
from apps.organization.tests.factories import BusinessProfileFactory, UserFactory
from apps.rbac.selectors import RoleSelector
from apps.rbac.services import RBACService

# =============================================================================
# FIXTURES — Governance actors (platform membership with global permissions)
# =============================================================================


@pytest.fixture
def platform_with_rbac(platform_account):
    """Ensure platform account has RBAC roles initialized."""
    from apps.rbac.models import Role

    exists = Role.objects.filter(
        account_type=AccountType.PLATFORM,
        account_id=platform_account.id,
    ).exists()
    if not exists:
        RBACService.initialize_platform_account(platform_id=platform_account.id)
    return platform_account


@pytest.fixture
def global_moderator_user(db, platform_with_rbac):
    """
    Create a user with Global Moderator role (level 5) on the platform.

    Global Moderator has all global_only scoped permissions including:
    can_suspend_business, can_view_businesses, can_edit_business,
    can_edit_profile, can_approve_verification_request, etc.
    """
    from apps.rbac.models import Role

    moderator = UserFactory(username="globmod", email="globmod@example.com")
    mod_role = Role.objects.get(
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
        name="Global Moderator",
    )
    RBACService.create_membership(
        user=moderator,
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
        role_id=mod_role.id,
        created_by=moderator,
    )
    return moderator


@pytest.fixture
def platform_admin_user(db, platform_with_rbac):
    """
    Create a user with Platform Admin role (level 2).

    Platform Admin has platform_only scoped permissions but NOT global_only.
    Should NOT have governance access.
    """
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
class TestBusinessPolicyCanCreate:
    """Tests for can_create policy — requires can_create_business flag or global perm."""

    def test_user_with_flag_can_create(self, user):
        user.can_create_business = True
        user.save(update_fields=["can_create_business"])
        assert BusinessPolicy.can_create(user=user) is True

    def test_user_without_flag_cannot_create(self, user):
        assert BusinessPolicy.can_create(user=user) is False

    def test_global_moderator_can_create_without_flag(self, global_moderator_user):
        """Governance actor with can_approve_business_creation can create."""
        assert BusinessPolicy.can_create(user=global_moderator_user) is True

    def test_platform_admin_cannot_create_without_flag(self, platform_admin_user):
        """Platform admin (platform_only scope) cannot bypass the flag."""
        assert BusinessPolicy.can_create(user=platform_admin_user) is False

    def test_anonymous_user_cannot_create(self):
        from django.contrib.auth.models import AnonymousUser

        assert BusinessPolicy.can_create(user=AnonymousUser()) is False


@pytest.mark.django_db
class TestBusinessPolicyCanUpdate:
    """Tests for can_update policy (requires can_edit_business permission)."""

    def test_owner_can_update(self, user, business_with_profile):
        """Owner has can_edit_business via Owner role."""
        assert (
            BusinessPolicy.can_update(
                user=user,
                business=business_with_profile,
            )
            is True
        )

    def test_member_without_permission_cannot_update(
        self,
        member_user,
        business_with_profile,
    ):
        """Base member has no permissions, cannot update."""
        assert (
            BusinessPolicy.can_update(
                user=member_user,
                business=business_with_profile,
            )
            is False
        )

    def test_non_member_cannot_update(self, non_member_user, business_with_profile):
        assert (
            BusinessPolicy.can_update(
                user=non_member_user,
                business=business_with_profile,
            )
            is False
        )

    def test_global_moderator_can_update(
        self, global_moderator_user, business_with_profile
    ):
        """Governance actor with global can_edit_business can update any business."""
        assert (
            BusinessPolicy.can_update(
                user=global_moderator_user,
                business=business_with_profile,
            )
            is True
        )

    def test_platform_admin_cannot_update(
        self, platform_admin_user, business_with_profile
    ):
        """Platform admin without global scope cannot update businesses."""
        assert (
            BusinessPolicy.can_update(
                user=platform_admin_user,
                business=business_with_profile,
            )
            is False
        )


@pytest.mark.django_db
class TestBusinessPolicyCanUpdateSlug:
    """Tests for can_update_slug policy (owner only)."""

    def test_owner_can_update_slug(self, user, business_with_profile):
        assert (
            BusinessPolicy.can_update_slug(
                user=user,
                business=business_with_profile,
            )
            is True
        )

    def test_member_cannot_update_slug(self, member_user, business_with_profile):
        assert (
            BusinessPolicy.can_update_slug(
                user=member_user,
                business=business_with_profile,
            )
            is False
        )

    def test_non_member_cannot_update_slug(
        self, non_member_user, business_with_profile
    ):
        assert (
            BusinessPolicy.can_update_slug(
                user=non_member_user,
                business=business_with_profile,
            )
            is False
        )

    def test_global_moderator_cannot_update_slug(
        self, global_moderator_user, business_with_profile
    ):
        """Governance actors cannot change slugs — business identity decision."""
        assert (
            BusinessPolicy.can_update_slug(
                user=global_moderator_user,
                business=business_with_profile,
            )
            is False
        )


@pytest.mark.django_db
class TestBusinessPolicyCanDelete:
    """Tests for can_delete policy (owner only)."""

    def test_owner_can_delete(self, user, business_with_profile):
        assert (
            BusinessPolicy.can_delete(
                user=user,
                business=business_with_profile,
            )
            is True
        )

    def test_member_cannot_delete(self, member_user, business_with_profile):
        assert (
            BusinessPolicy.can_delete(
                user=member_user,
                business=business_with_profile,
            )
            is False
        )

    def test_non_member_cannot_delete(self, non_member_user, business_with_profile):
        assert (
            BusinessPolicy.can_delete(
                user=non_member_user,
                business=business_with_profile,
            )
            is False
        )

    def test_global_moderator_cannot_delete(
        self, global_moderator_user, business_with_profile
    ):
        """Governance actors cannot soft-delete — owner only. Force-delete via /admin."""
        assert (
            BusinessPolicy.can_delete(
                user=global_moderator_user,
                business=business_with_profile,
            )
            is False
        )


@pytest.mark.django_db
class TestBusinessPolicyCanArchive:
    """Tests for can_archive policy (owner OR governance)."""

    def test_owner_can_archive(self, user, business_with_profile):
        assert (
            BusinessPolicy.can_archive(
                user=user,
                business=business_with_profile,
            )
            is True
        )

    def test_member_cannot_archive(self, member_user, business_with_profile):
        assert (
            BusinessPolicy.can_archive(
                user=member_user,
                business=business_with_profile,
            )
            is False
        )

    def test_non_member_cannot_archive(self, non_member_user, business_with_profile):
        assert (
            BusinessPolicy.can_archive(
                user=non_member_user,
                business=business_with_profile,
            )
            is False
        )

    def test_global_moderator_can_archive(
        self, global_moderator_user, business_with_profile
    ):
        """Governance actor with can_suspend_business can archive."""
        assert (
            BusinessPolicy.can_archive(
                user=global_moderator_user,
                business=business_with_profile,
            )
            is True
        )


@pytest.mark.django_db
class TestBusinessPolicyCanUpdateProfile:
    """Tests for can_update_profile policy (requires can_edit_profile permission)."""

    def test_owner_can_update_profile(self, user, business_with_profile):
        """Owner has can_edit_profile via Owner role."""
        assert (
            BusinessPolicy.can_update_profile(
                user=user,
                business=business_with_profile,
            )
            is True
        )

    def test_member_without_permission_cannot_update_profile(
        self,
        member_user,
        business_with_profile,
    ):
        assert (
            BusinessPolicy.can_update_profile(
                user=member_user,
                business=business_with_profile,
            )
            is False
        )

    def test_global_moderator_can_update_profile(
        self, global_moderator_user, business_with_profile
    ):
        """Governance actor with global can_edit_profile can update any profile."""
        assert (
            BusinessPolicy.can_update_profile(
                user=global_moderator_user,
                business=business_with_profile,
            )
            is True
        )


@pytest.mark.django_db
class TestBusinessPolicyCanViewProfile:
    """Tests for can_view_profile policy."""

    def test_public_profile_viewable_by_any_user(
        self,
        non_member_user,
        business_with_profile,
    ):
        """Public profiles are viewable by any authenticated user."""
        profile = business_with_profile.profile
        profile.is_public = True
        profile.save(update_fields=["is_public"])

        assert (
            BusinessPolicy.can_view_profile(
                user=non_member_user,
                business=business_with_profile,
                profile=profile,
            )
            is True
        )

    def test_private_profile_viewable_by_member(
        self,
        member_user,
        business_with_profile,
    ):
        """Private profiles are viewable by members."""
        profile = business_with_profile.profile
        profile.is_public = False
        profile.save(update_fields=["is_public"])

        assert (
            BusinessPolicy.can_view_profile(
                user=member_user,
                business=business_with_profile,
                profile=profile,
            )
            is True
        )

    def test_private_profile_not_viewable_by_non_member(
        self,
        non_member_user,
        business_with_profile,
    ):
        """Private profiles are not viewable by non-members."""
        profile = business_with_profile.profile
        profile.is_public = False
        profile.save(update_fields=["is_public"])

        assert (
            BusinessPolicy.can_view_profile(
                user=non_member_user,
                business=business_with_profile,
                profile=profile,
            )
            is False
        )

    def test_private_profile_viewable_by_global_moderator(
        self,
        global_moderator_user,
        business_with_profile,
    ):
        """Governance actors with can_view_businesses can view private profiles."""
        profile = business_with_profile.profile
        profile.is_public = False
        profile.save(update_fields=["is_public"])

        assert (
            BusinessPolicy.can_view_profile(
                user=global_moderator_user,
                business=business_with_profile,
                profile=profile,
            )
            is True
        )


@pytest.mark.django_db
class TestBusinessPolicyGetViewerPermissions:
    """Tests for get_viewer_permissions aggregation."""

    def test_owner_gets_all_permissions(self, user, business_with_profile):
        """Owner gets all permissions True."""
        perms = BusinessPolicy.get_viewer_permissions(
            user=user,
            business=business_with_profile,
        )

        assert perms["can_view"] is True
        assert perms["can_edit"] is True
        assert perms["can_edit_profile"] is True
        assert perms["can_delete"] is True
        assert perms["can_change_slug"] is True
        assert perms["can_archive"] is True

    def test_member_gets_view_only(self, member_user, business_with_profile):
        """Base Member (no permissions) gets only can_view."""
        perms = BusinessPolicy.get_viewer_permissions(
            user=member_user,
            business=business_with_profile,
        )

        assert perms["can_view"] is True
        assert perms["can_edit"] is False
        assert perms["can_edit_profile"] is False
        assert perms["can_delete"] is False
        assert perms["can_change_slug"] is False
        assert perms["can_archive"] is False

    def test_non_member_gets_view_only(self, non_member_user, business_with_profile):
        """Non-member gets can_view True (active business) but nothing else."""
        perms = BusinessPolicy.get_viewer_permissions(
            user=non_member_user,
            business=business_with_profile,
        )

        assert perms["can_view"] is True
        assert perms["can_edit"] is False
        assert perms["can_edit_profile"] is False
        assert perms["can_delete"] is False
        assert perms["can_change_slug"] is False
        assert perms["can_archive"] is False

    def test_global_moderator_gets_governance_permissions(
        self, global_moderator_user, business_with_profile
    ):
        """Global Moderator gets view, edit, edit_profile, archive but not owner-only."""
        perms = BusinessPolicy.get_viewer_permissions(
            user=global_moderator_user,
            business=business_with_profile,
        )

        assert perms["can_view"] is True
        assert perms["can_edit"] is True
        assert perms["can_edit_profile"] is True
        assert perms["can_delete"] is False  # owner only
        assert perms["can_change_slug"] is False  # owner only
        assert perms["can_archive"] is True  # governance can archive


@pytest.mark.django_db
class TestBusinessPolicyGovernanceOnly:
    """Tests for governance-only policies (suspend, reactivate, verify)."""

    def test_global_moderator_can_suspend(
        self, global_moderator_user, business_with_profile
    ):
        assert (
            BusinessPolicy.can_suspend(
                user=global_moderator_user,
                business=business_with_profile,
            )
            is True
        )

    def test_owner_cannot_suspend(self, user, business_with_profile):
        assert (
            BusinessPolicy.can_suspend(
                user=user,
                business=business_with_profile,
            )
            is False
        )

    def test_platform_admin_cannot_suspend(
        self, platform_admin_user, business_with_profile
    ):
        """Platform admin (platform_only scope) cannot suspend businesses."""
        assert (
            BusinessPolicy.can_suspend(
                user=platform_admin_user,
                business=business_with_profile,
            )
            is False
        )

    def test_global_moderator_can_reactivate(
        self, global_moderator_user, business_with_profile
    ):
        assert (
            BusinessPolicy.can_reactivate(
                user=global_moderator_user,
                business=business_with_profile,
            )
            is True
        )

    def test_global_moderator_can_verify(
        self, global_moderator_user, business_with_profile
    ):
        assert (
            BusinessPolicy.can_verify(
                user=global_moderator_user,
                business=business_with_profile,
            )
            is True
        )

    def test_non_member_cannot_suspend(self, non_member_user, business_with_profile):
        assert (
            BusinessPolicy.can_suspend(
                user=non_member_user,
                business=business_with_profile,
            )
            is False
        )
