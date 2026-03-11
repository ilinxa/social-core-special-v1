# apps/organization/tests/business/test_selectors.py
"""
Tests for BusinessAccountSelector RBAC-based queries.
"""

import pytest

from apps.organization.business.selectors import BusinessAccountSelector


@pytest.mark.django_db
class TestBusinessAccountSelectorListByOwner:
    """Tests for list_by_owner (RBAC ownership)."""

    def test_returns_owned_businesses(self, user, business_with_profile):
        """User with owner membership sees their business."""
        result = BusinessAccountSelector.list_by_owner(user=user)
        assert business_with_profile in result

    def test_excludes_member_businesses(self, member_user, business_with_profile):
        """User with Base Member role is not an owner."""
        result = BusinessAccountSelector.list_by_owner(user=member_user)
        assert business_with_profile not in result

    def test_returns_empty_for_non_member(self, non_member_user):
        """User with no memberships sees nothing."""
        result = BusinessAccountSelector.list_by_owner(user=non_member_user)
        assert result.count() == 0

    def test_excludes_deleted_businesses(self, user, business_with_profile):
        """Soft-deleted businesses are excluded."""
        business_with_profile.is_deleted = True
        business_with_profile.save(update_fields=["is_deleted"])

        result = BusinessAccountSelector.list_by_owner(user=user)
        assert business_with_profile not in result


@pytest.mark.django_db
class TestBusinessAccountSelectorListByMember:
    """Tests for list_by_member (RBAC membership)."""

    def test_returns_businesses_for_member(self, member_user, business_with_profile):
        """User with any active membership sees the business."""
        result = BusinessAccountSelector.list_by_member(user=member_user)
        assert business_with_profile in result

    def test_includes_owned_businesses(self, user, business_with_profile):
        """Owner memberships are included."""
        result = BusinessAccountSelector.list_by_member(user=user)
        assert business_with_profile in result

    def test_returns_empty_for_non_member(self, non_member_user):
        """User with no memberships sees nothing."""
        result = BusinessAccountSelector.list_by_member(user=non_member_user)
        assert result.count() == 0

    def test_excludes_deleted_businesses(self, user, business_with_profile):
        """Soft-deleted businesses are excluded even if user is a member."""
        business_with_profile.is_deleted = True
        business_with_profile.save(update_fields=["is_deleted"])

        result = BusinessAccountSelector.list_by_member(user=user)
        assert business_with_profile not in result
