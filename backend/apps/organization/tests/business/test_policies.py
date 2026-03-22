# apps/organization/tests/business/test_policies.py
"""
Tests for BusinessPolicy RBAC-based authorization.
"""

import pytest

from apps.organization.business.policies import BusinessPolicy
from apps.organization.tests.factories import BusinessProfileFactory


@pytest.mark.django_db
class TestBusinessPolicyCanCreate:
    """Tests for can_create policy — requires platform approval flag."""

    def test_user_with_flag_can_create(self, user):
        user.can_create_business = True
        user.save(update_fields=["can_create_business"])
        assert BusinessPolicy.can_create(user=user) is True

    def test_user_without_flag_cannot_create(self, user):
        assert BusinessPolicy.can_create(user=user) is False

    def test_staff_can_create_without_flag(self, staff_user):
        assert BusinessPolicy.can_create(user=staff_user) is True

    def test_superuser_can_create_without_flag(self, superuser):
        assert BusinessPolicy.can_create(user=superuser) is True

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

    def test_staff_can_update(self, staff_user, business_with_profile):
        assert (
            BusinessPolicy.can_update(
                user=staff_user,
                business=business_with_profile,
            )
            is True
        )

    def test_superuser_can_update(self, superuser, business_with_profile):
        assert (
            BusinessPolicy.can_update(
                user=superuser,
                business=business_with_profile,
            )
            is True
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

    def test_staff_cannot_update_slug(self, staff_user, business_with_profile):
        """Staff cannot change slug — business identity decision."""
        assert (
            BusinessPolicy.can_update_slug(
                user=staff_user,
                business=business_with_profile,
            )
            is False
        )


@pytest.mark.django_db
class TestBusinessPolicyCanDelete:
    """Tests for can_delete policy (owner or superuser)."""

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

    def test_superuser_can_delete(self, superuser, business_with_profile):
        assert (
            BusinessPolicy.can_delete(
                user=superuser,
                business=business_with_profile,
            )
            is True
        )

    def test_staff_cannot_delete(self, staff_user, business_with_profile):
        """Regular staff cannot delete businesses."""
        assert (
            BusinessPolicy.can_delete(
                user=staff_user,
                business=business_with_profile,
            )
            is False
        )


@pytest.mark.django_db
class TestBusinessPolicyCanArchive:
    """Tests for can_archive policy (owner only)."""

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

    def test_staff_can_update_profile(self, staff_user, business_with_profile):
        assert (
            BusinessPolicy.can_update_profile(
                user=staff_user,
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

    def test_private_profile_viewable_by_staff(
        self,
        staff_user,
        business_with_profile,
    ):
        """Staff can always view private profiles."""
        profile = business_with_profile.profile
        profile.is_public = False
        profile.save(update_fields=["is_public"])

        assert (
            BusinessPolicy.can_view_profile(
                user=staff_user,
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

    def test_staff_gets_view_and_edit(self, staff_user, business_with_profile):
        """Staff gets view, edit, edit_profile (but not owner-only actions)."""
        perms = BusinessPolicy.get_viewer_permissions(
            user=staff_user,
            business=business_with_profile,
        )

        assert perms["can_view"] is True
        assert perms["can_edit"] is True
        assert perms["can_edit_profile"] is True
        assert perms["can_delete"] is False  # superuser or owner only
        assert perms["can_change_slug"] is False  # owner only
        assert perms["can_archive"] is False  # owner only


@pytest.mark.django_db
class TestBusinessPolicyStaffOnly:
    """Tests for staff-only policies (suspend, reactivate, verify)."""

    def test_staff_can_suspend(self, staff_user, business_with_profile):
        assert (
            BusinessPolicy.can_suspend(
                user=staff_user,
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

    def test_staff_can_reactivate(self, staff_user, business_with_profile):
        assert (
            BusinessPolicy.can_reactivate(
                user=staff_user,
                business=business_with_profile,
            )
            is True
        )

    def test_staff_can_verify(self, staff_user, business_with_profile):
        assert (
            BusinessPolicy.can_verify(
                user=staff_user,
                business=business_with_profile,
            )
            is True
        )
