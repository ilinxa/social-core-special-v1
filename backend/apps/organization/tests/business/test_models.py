# apps/organization/tests/business/test_models.py
"""
Tests for Business models.
"""

import pytest
from django.db import IntegrityError

from apps.core.constants import BusinessStatus, VerificationStatus
from apps.organization.business.models import (
    BusinessAccount,
    BusinessProfile,
    BusinessSlugHistory,
)


@pytest.mark.django_db
class TestBusinessAccountModel:
    """Tests for BusinessAccount model."""

    def test_business_account_creation(self, business_account):
        """Test business account can be created."""
        assert business_account.id is not None
        assert business_account.slug is not None
        assert business_account.legal_name is not None

    def test_business_account_slug_unique(self, business_account_factory, user):
        """Test that business slugs must be unique."""
        business_account_factory(slug="unique-slug", created_by=user)

        with pytest.raises(IntegrityError):
            business_account_factory(slug="unique-slug", created_by=user)

    def test_business_account_auto_slug(self, db, user):
        """Test that slug is auto-generated from legal_name if not provided."""
        business = BusinessAccount.objects.create(
            legal_name="My Test Business",
            country="US",
            created_by=user,
            updated_by=user,
        )

        assert business.slug == "my-test-business"

    def test_business_account_str(self, business_account):
        """Test string representation."""
        assert business_account.legal_name in str(business_account)
        assert business_account.slug in str(business_account)

    def test_business_account_default_status(self, db, user):
        """Test default status values."""
        business = BusinessAccount.objects.create(
            legal_name="Test Business",
            slug="test-business-default",
            country="US",
            created_by=user,
            updated_by=user,
        )

        assert business.status == BusinessStatus.PENDING
        assert business.verification_status == VerificationStatus.UNVERIFIED

    def test_business_account_soft_delete(self, business_account, user):
        """Test soft delete functionality."""
        business_id = business_account.id

        business_account.soft_delete(user=user)

        # Should not be in default queryset
        assert not BusinessAccount.objects.filter(id=business_id).exists()

        # Should be in all_objects queryset
        assert BusinessAccount.all_objects.filter(id=business_id).exists()

        # Check soft delete fields
        deleted_business = BusinessAccount.all_objects.get(id=business_id)
        assert deleted_business.is_deleted is True
        assert deleted_business.deleted_at is not None
        assert deleted_business.deleted_by == user

    def test_business_account_restore(self, business_account, user):
        """Test restore from soft delete."""
        business_account.soft_delete(user=user)
        business_account.restore()

        business_account.refresh_from_db()
        assert business_account.is_deleted is False
        assert business_account.deleted_at is None
        assert business_account.deleted_by is None

    def test_business_account_manager_active(self, business_account_factory, user):
        """Test active() manager method."""
        active = business_account_factory(status=BusinessStatus.ACTIVE, created_by=user)
        business_account_factory(status=BusinessStatus.SUSPENDED, created_by=user)
        business_account_factory(status=BusinessStatus.PENDING, created_by=user)

        active_businesses = BusinessAccount.objects.active()
        assert active in active_businesses
        assert active_businesses.count() == 1

    def test_business_account_manager_verified(self, business_account_factory, user):
        """Test verified() manager method."""
        verified = business_account_factory(
            status=BusinessStatus.ACTIVE,
            verification_status=VerificationStatus.VERIFIED,
            created_by=user,
        )
        business_account_factory(
            status=BusinessStatus.ACTIVE,
            verification_status=VerificationStatus.UNVERIFIED,
            created_by=user,
        )

        verified_businesses = BusinessAccount.objects.verified()
        assert verified in verified_businesses
        assert verified_businesses.count() == 1


@pytest.mark.django_db
class TestBusinessProfileModel:
    """Tests for BusinessProfile model."""

    def test_business_profile_creation(self, business_profile_factory, business_account):
        """Test business profile can be created."""
        profile = business_profile_factory(business=business_account)
        assert profile.business == business_account

    def test_business_profile_one_to_one(self, business_with_profile):
        """Test one-to-one relationship."""
        assert business_with_profile.profile is not None
        assert business_with_profile.profile.business == business_with_profile

    def test_business_profile_str(self, business_with_profile):
        """Test string representation."""
        profile = business_with_profile.profile
        assert profile.display_name in str(profile)

    def test_business_profile_default_public(self, business_profile_factory, business_account):
        """Test default is_public value."""
        profile = business_profile_factory(business=business_account)
        assert profile.is_public is True

    def test_business_profile_cascade_delete(self, business_with_profile):
        """Test profile is deleted when business is deleted (hard delete)."""
        business_id = business_with_profile.id
        profile_pk = business_with_profile.profile.pk

        # Hard delete (bypassing soft delete)
        BusinessAccount.all_objects.filter(id=business_id).delete()

        assert not BusinessProfile.objects.filter(pk=profile_pk).exists()


@pytest.mark.django_db
class TestBusinessSlugHistoryModel:
    """Tests for BusinessSlugHistory model."""

    def test_slug_history_creation(self, business_slug_history_factory, business_account):
        """Test slug history can be created."""
        history = business_slug_history_factory(
            business=business_account,
            old_slug="old-slug-test",
        )

        assert history.old_slug == "old-slug-test"
        assert history.business == business_account

    def test_slug_history_unique_old_slug(self, business_slug_history_factory, business_account):
        """Test that old_slug must be globally unique."""
        business_slug_history_factory(business=business_account, old_slug="used-slug")

        with pytest.raises(IntegrityError):
            business_slug_history_factory(business=business_account, old_slug="used-slug")

    def test_slug_history_str(self, business_slug_history_factory, business_account):
        """Test string representation."""
        history = business_slug_history_factory(
            business=business_account,
            old_slug="old-test-slug",
        )

        result = str(history)
        assert "old-test-slug" in result
        assert business_account.slug in result
