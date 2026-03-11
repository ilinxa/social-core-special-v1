# apps/organization/tests/platform/test_services.py
"""
Tests for Platform services.
"""

import pytest

from apps.core.exceptions import ConflictError
from apps.organization.platform.models import PlatformAccount, PlatformProfile
from apps.organization.platform.services import (
    PlatformAccountService,
    PlatformProfileService,
)


@pytest.mark.django_db
class TestPlatformAccountService:
    """Tests for PlatformAccountService."""

    def test_configure_new_platform(self, db, superuser):
        """Test initial platform configuration."""
        # Delete existing platform first
        PlatformAccount.objects.all().delete()

        platform = PlatformAccountService.configure(
            name="My Platform",
            settings={"key": "value"},
            actor=superuser,
        )

        assert platform.is_configured is True
        assert platform.settings == {"key": "value"}
        assert platform.profile.name == "My Platform"

    def test_configure_unconfigured_platform(self, platform_account, superuser):
        """Test configuring an existing but unconfigured platform."""
        platform_account.is_configured = False
        platform_account.save()

        platform = PlatformAccountService.configure(
            name="Configured Platform",
            actor=superuser,
        )

        assert platform.is_configured is True
        assert platform.profile.name == "Configured Platform"

    def test_configure_already_configured_raises_error(self, configured_platform, superuser):
        """Test that configuring an already configured platform raises error."""
        with pytest.raises(ConflictError) as exc_info:
            PlatformAccountService.configure(
                name="Another Name",
                actor=superuser,
            )

        assert "already configured" in str(exc_info.value.message)

    def test_update_settings(self, platform_account, superuser):
        """Test updating platform settings."""
        platform_account.settings = {"existing": "value"}
        platform_account.save()

        platform = PlatformAccountService.update_settings(
            settings={"new_key": "new_value"},
            actor=superuser,
        )

        # Should merge, not replace
        assert platform.settings["existing"] == "value"
        assert platform.settings["new_key"] == "new_value"

    def test_update_settings_overwrites_existing_keys(self, platform_account, superuser):
        """Test that updating settings overwrites existing keys."""
        platform_account.settings = {"key": "old_value"}
        platform_account.save()

        platform = PlatformAccountService.update_settings(
            settings={"key": "new_value"},
            actor=superuser,
        )

        assert platform.settings["key"] == "new_value"


@pytest.mark.django_db
class TestPlatformProfileService:
    """Tests for PlatformProfileService."""

    def test_update_profile_name(self, platform_profile, superuser):
        """Test updating profile name."""
        profile = PlatformProfileService.update(
            name="New Platform Name",
            actor=superuser,
        )

        assert profile.name == "New Platform Name"

    def test_update_profile_partial(self, platform_profile, superuser):
        """Test partial profile update (only provided fields change)."""
        original_description = platform_profile.description
        original_email = platform_profile.contact_email

        profile = PlatformProfileService.update(
            tagline="New tagline",
            actor=superuser,
        )

        assert profile.tagline == "New tagline"
        assert profile.description == original_description
        assert profile.contact_email == original_email

    def test_update_profile_colors(self, platform_profile, superuser):
        """Test updating profile colors."""
        profile = PlatformProfileService.update(
            primary_color="#FF0000",
            secondary_color="#00FF00",
            actor=superuser,
        )

        assert profile.primary_color == "#FF0000"
        assert profile.secondary_color == "#00FF00"

    def test_update_profile_social_links(self, platform_profile, superuser):
        """Test updating social links."""
        social_links = {
            "twitter": "https://twitter.com/test",
            "facebook": "https://facebook.com/test",
        }

        profile = PlatformProfileService.update(
            social_links=social_links,
            actor=superuser,
        )

        assert profile.social_links == social_links

    def test_update_profile_contact_info(self, platform_profile, superuser):
        """Test updating contact information."""
        profile = PlatformProfileService.update(
            contact_email="new@example.com",
            contact_phone="+9876543210",
            address="456 New Street",
            actor=superuser,
        )

        assert profile.contact_email == "new@example.com"
        assert profile.contact_phone == "+9876543210"
        assert profile.address == "456 New Street"

    def test_update_profile_updates_platform_updated_by(self, platform_profile, superuser):
        """Test that updating profile also updates platform.updated_by."""
        platform = platform_profile.platform
        original_updated_by = platform.updated_by

        PlatformProfileService.update(
            name="Updated Name",
            actor=superuser,
        )

        platform.refresh_from_db()
        assert platform.updated_by == superuser
