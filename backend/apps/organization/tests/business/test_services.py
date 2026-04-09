# apps/organization/tests/business/test_services.py
"""
Tests for Business services.
"""

import pytest

from apps.core.constants import BusinessStatus, VerificationStatus
from apps.core.exceptions import ConflictError, ValidationError
from apps.organization.business.models import BusinessSlugHistory
from apps.organization.business.services import (
    BusinessAccountService,
    BusinessProfileService,
)


@pytest.mark.django_db
class TestBusinessAccountService:
    """Tests for BusinessAccountService."""

    def test_create_business(self, user):
        """Test creating a new business."""
        business = BusinessAccountService.create_business(
            owner=user,
            legal_name="Test Company",
            country="US",
        )

        assert business.legal_name == "Test Company"
        assert business.country == "US"
        assert business.slug == "test-company"
        assert business.status == BusinessStatus.ACTIVE
        assert business.created_by == user
        assert business.profile is not None

    def test_create_business_with_custom_slug(self, user):
        """Test creating business with custom slug."""
        business = BusinessAccountService.create_business(
            owner=user,
            legal_name="Test Company",
            country="US",
            slug="custom-slug",
        )

        assert business.slug == "custom-slug"

    def test_create_business_with_display_name(self, user):
        """Test creating business with custom display name."""
        business = BusinessAccountService.create_business(
            owner=user,
            legal_name="Test Company Legal Name",
            country="US",
            display_name="Test Co",
        )

        assert business.profile.display_name == "Test Co"

    @pytest.mark.parametrize("reserved_slug", ["sites", "templates", "media", "api-keys", "businesses", "dashboard"])
    def test_create_business_reserved_slug_raises_error(self, user, reserved_slug):
        """Test that creating business with a reserved slug raises ConflictError."""
        with pytest.raises(ConflictError) as exc_info:
            BusinessAccountService.create_business(
                owner=user,
                legal_name="Reserved Slug Co",
                country="US",
                slug=reserved_slug,
            )

        assert "reserved" in str(exc_info.value.message)
        assert exc_info.value.conflict_type == "slug_reserved"

    def test_create_business_duplicate_slug_raises_error(
        self, business_account_factory, user
    ):
        """Test that creating business with existing slug raises error."""
        business_account_factory(slug="taken-slug", created_by=user)

        with pytest.raises(ConflictError) as exc_info:
            BusinessAccountService.create_business(
                owner=user,
                legal_name="Another Company",
                country="US",
                slug="taken-slug",
            )

        assert "not available" in str(exc_info.value.message)

    def test_create_business_historical_slug_raises_error(
        self, business_slug_history_factory, business_account, user
    ):
        """Test that creating business with historical slug raises error."""
        business_slug_history_factory(
            business=business_account,
            old_slug="historical-slug",
        )

        with pytest.raises(ConflictError):
            BusinessAccountService.create_business(
                owner=user,
                legal_name="New Company",
                country="US",
                slug="historical-slug",
            )

    def test_update_business(self, business_account, user):
        """Test updating business fields."""
        business = BusinessAccountService.update(
            business=business_account,
            legal_name="Updated Name",
            country="GB",
            actor=user,
        )

        assert business.legal_name == "Updated Name"
        assert business.country == "GB"

    def test_update_business_settings_merge(self, business_account, user):
        """Test that settings are merged, not replaced."""
        business_account.settings = {"existing": "value"}
        business_account.save()

        business = BusinessAccountService.update(
            business=business_account,
            settings={"new_key": "new_value"},
            actor=user,
        )

        assert business.settings["existing"] == "value"
        assert business.settings["new_key"] == "new_value"

    def test_update_slug(self, business_account, user):
        """Test changing business slug."""
        old_slug = business_account.slug

        business = BusinessAccountService.update_slug(
            business=business_account,
            new_slug="new-slug",
            actor=user,
        )

        assert business.slug == "new-slug"
        # Old slug should be in history
        assert BusinessSlugHistory.objects.filter(
            business=business_account,
            old_slug=old_slug,
        ).exists()

    def test_update_slug_same_slug_raises_error(self, business_account, user):
        """Test that changing to same slug raises error."""
        with pytest.raises(ValidationError):
            BusinessAccountService.update_slug(
                business=business_account,
                new_slug=business_account.slug,
                actor=user,
            )

    def test_update_slug_taken_slug_raises_error(
        self, business_account, business_account_factory, user
    ):
        """Test that changing to taken slug raises error."""
        other_business = business_account_factory(slug="taken-slug", created_by=user)

        with pytest.raises(ConflictError):
            BusinessAccountService.update_slug(
                business=business_account,
                new_slug="taken-slug",
                actor=user,
            )

    def test_suspend_business(self, business_account, user):
        """Test suspending a business."""
        business = BusinessAccountService.suspend(
            business=business_account,
            reason="Violation of terms",
            actor=user,
        )

        assert business.status == BusinessStatus.SUSPENDED

    def test_reactivate_business(self, suspended_business, user):
        """Test reactivating a suspended business."""
        business = BusinessAccountService.reactivate(
            business=suspended_business,
            actor=user,
        )

        assert business.status == BusinessStatus.ACTIVE

    def test_reactivate_non_suspended_raises_error(self, business_account, user):
        """Test that reactivating non-suspended business raises error."""
        business_account.status = BusinessStatus.ACTIVE
        business_account.save()

        with pytest.raises(ValidationError):
            BusinessAccountService.reactivate(
                business=business_account,
                actor=user,
            )

    def test_archive_business(self, business_account, user):
        """Test archiving a business."""
        business = BusinessAccountService.archive(
            business=business_account,
            actor=user,
        )

        assert business.status == BusinessStatus.ARCHIVED

    def test_soft_delete_business(self, business_account, user):
        """Test soft deleting a business."""
        business = BusinessAccountService.soft_delete(
            business=business_account,
            actor=user,
        )

        assert business.is_deleted is True
        assert business.status == BusinessStatus.DELETED

    def test_update_verification_status_verified(self, business_account, user):
        """Test updating verification status to verified."""
        business = BusinessAccountService.update_verification_status(
            business=business_account,
            status=VerificationStatus.VERIFIED,
            actor=user,
        )

        assert business.verification_status == VerificationStatus.VERIFIED
        assert business.verified_at is not None
        assert business.verified_by == user

    def test_update_verification_status_rejected(self, business_account, user):
        """Test updating verification status to rejected."""
        business = BusinessAccountService.update_verification_status(
            business=business_account,
            status=VerificationStatus.REJECTED,
            actor=user,
        )

        assert business.verification_status == VerificationStatus.REJECTED


@pytest.mark.django_db
class TestBusinessProfileService:
    """Tests for BusinessProfileService."""

    def test_update_profile(self, business_with_profile, user):
        """Test updating business profile."""
        profile = BusinessProfileService.update(
            profile=business_with_profile.profile,
            display_name="New Display Name",
            tagline="New tagline",
            actor=user,
        )

        assert profile.display_name == "New Display Name"
        assert profile.tagline == "New tagline"

    def test_update_profile_partial(self, business_with_profile, user):
        """Test partial profile update."""
        original_display_name = business_with_profile.profile.display_name

        profile = BusinessProfileService.update(
            profile=business_with_profile.profile,
            description="Updated description only",
            actor=user,
        )

        assert profile.display_name == original_display_name
        assert profile.description == "Updated description only"

    def test_update_profile_visibility(self, business_with_profile, user):
        """Test updating profile visibility."""
        profile = BusinessProfileService.update(
            profile=business_with_profile.profile,
            is_public=False,
            actor=user,
        )

        assert profile.is_public is False

    def test_update_profile_updates_business_updated_by(
        self, business_with_profile, user
    ):
        """Test that updating profile updates business.updated_by."""
        original_updated_by = business_with_profile.updated_by

        BusinessProfileService.update(
            profile=business_with_profile.profile,
            description="Some update",
            actor=user,
        )

        business_with_profile.refresh_from_db()
        assert business_with_profile.updated_by == user
