# apps/organization/tests/platform/test_models.py
"""
Tests for Platform models.
"""

import pytest
from django.db import IntegrityError

from apps.organization.platform.models import PlatformAccount, PlatformProfile


@pytest.mark.django_db
class TestPlatformAccountModel:
    """Tests for PlatformAccount model."""

    def test_platform_account_singleton_constraint(self, platform_account):
        """Test that only one PlatformAccount can exist (singleton)."""
        # Try to create a second platform account
        with pytest.raises(IntegrityError):
            PlatformAccount.objects.create(
                singleton_key=1,  # Same key - should fail
                is_configured=True,
            )

    def test_platform_account_singleton_key_always_one(self, db):
        """Test that singleton_key is always set to 1 on save."""
        # Delete existing platform account first
        PlatformAccount.objects.all().delete()

        platform = PlatformAccount(singleton_key=999, is_configured=False)
        platform.save()

        # Should be forced to 1
        assert platform.singleton_key == 1

    def test_platform_account_str(self, platform_account):
        """Test string representation."""
        assert str(platform_account.id) in str(platform_account)
        assert "Platform Account" in str(platform_account)

    def test_platform_account_default_values(self, db):
        """Test default field values."""
        # Delete existing platform account first
        PlatformAccount.objects.all().delete()

        platform = PlatformAccount.objects.create()

        assert platform.is_configured is False
        assert platform.settings == {}
        assert platform.singleton_key == 1

    def test_platform_account_settings_json(self, platform_account):
        """Test that settings field stores JSON properly."""
        platform_account.settings = {
            "feature_flags": {"new_feature": True},
            "limits": {"max_businesses": 1000},
        }
        platform_account.save()

        platform_account.refresh_from_db()
        assert platform_account.settings["feature_flags"]["new_feature"] is True
        assert platform_account.settings["limits"]["max_businesses"] == 1000


@pytest.mark.django_db
class TestPlatformProfileModel:
    """Tests for PlatformProfile model."""

    def test_platform_profile_creation(self, platform_profile):
        """Test platform profile can be created."""
        assert platform_profile.name is not None
        assert platform_profile.platform is not None

    def test_platform_profile_one_to_one(self, platform_account, platform_profile):
        """Test one-to-one relationship with PlatformAccount."""
        # Profile should be accessible from account
        assert platform_account.profile == platform_profile

        # Account should be accessible from profile
        assert platform_profile.platform == platform_account

    def test_platform_profile_str(self, platform_profile):
        """Test string representation."""
        assert platform_profile.name in str(platform_profile)

    def test_platform_profile_default_colors(self, db):
        """Test default color values."""
        # Delete existing platform and profile to test fresh creation
        PlatformAccount.objects.all().delete()

        platform = PlatformAccount.objects.create()
        profile = PlatformProfile.objects.create(
            platform=platform,
            name="Test Platform",
        )
        assert profile.primary_color == "#000000"
        assert profile.secondary_color == "#ffffff"

    def test_platform_profile_social_links(self, platform_profile):
        """Test social links JSON field."""
        platform_profile.social_links = {
            "twitter": "https://twitter.com/platform",
            "linkedin": "https://linkedin.com/company/platform",
        }
        platform_profile.save()

        platform_profile.refresh_from_db()
        assert "twitter" in platform_profile.social_links
        assert "linkedin" in platform_profile.social_links

    def test_platform_profile_cascade_delete(self, db):
        """Test profile is deleted when platform account is deleted."""
        # Note: This is a dangerous operation, testing on fresh instances
        PlatformAccount.objects.all().delete()

        platform = PlatformAccount.objects.create()
        profile = PlatformProfile.objects.create(platform=platform, name="Test")

        profile_id = profile.pk
        platform.delete()

        assert not PlatformProfile.objects.filter(pk=profile_id).exists()
