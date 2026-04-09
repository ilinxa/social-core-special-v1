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


@pytest.mark.django_db
class TestBusinessAccountSelectorListAll:
    """Tests for list_all (governance view)."""

    def test_returns_all_businesses(self, business_with_profile):
        result = BusinessAccountSelector.list_all()
        assert business_with_profile in result

    def test_excludes_deleted_by_default(self, business_with_profile):
        business_with_profile.is_deleted = True
        business_with_profile.save(update_fields=["is_deleted"])
        result = BusinessAccountSelector.list_all()
        assert business_with_profile not in result

    def test_includes_deleted_when_requested(self, business_with_profile):
        business_with_profile.is_deleted = True
        business_with_profile.save(update_fields=["is_deleted"])
        result = BusinessAccountSelector.list_all(include_deleted=True)
        assert business_with_profile in result

    def test_includes_suspended_businesses(self, suspended_business):
        result = BusinessAccountSelector.list_all()
        assert suspended_business in result


@pytest.mark.django_db
class TestBusinessAccountSelectorListFiltered:
    """Tests for list_filtered (governance view)."""

    def test_filter_by_status(self, business_with_profile, suspended_business):
        result = BusinessAccountSelector.list_filtered(status="active")
        assert business_with_profile in result
        assert suspended_business not in result

    def test_filter_by_country(self, business_with_profile):
        result = BusinessAccountSelector.list_filtered(
            country=business_with_profile.country
        )
        assert business_with_profile in result

    def test_filter_by_search(self, business_with_profile):
        result = BusinessAccountSelector.list_filtered(
            search=business_with_profile.legal_name[:5]
        )
        assert business_with_profile in result

    def test_no_filters_returns_all(self, business_with_profile, suspended_business):
        result = BusinessAccountSelector.list_filtered()
        assert business_with_profile in result
        assert suspended_business in result

    def test_combined_filters(self, business_with_profile):
        result = BusinessAccountSelector.list_filtered(
            status="active",
            country=business_with_profile.country,
        )
        assert business_with_profile in result
