# apps/organization/tests/platform/test_selectors.py
"""
Tests for Platform selectors.

Covers:
- PlatformAccountSelector: get, exists, is_configured
- PlatformProfileSelector: get
"""

import pytest

from apps.core.exceptions import NotFound
from apps.organization.platform.models import PlatformAccount
from apps.organization.platform.selectors import (
    PlatformAccountSelector,
    PlatformProfileSelector,
)


@pytest.mark.django_db
class TestPlatformAccountSelector:
    """Tests for PlatformAccountSelector."""

    def test_get_platform_account(self, platform_account, platform_profile):
        """get() returns the singleton platform account with profile."""
        result = PlatformAccountSelector.get()
        assert result.id == platform_account.id
        assert hasattr(result, "profile")

    def test_get_platform_account_not_found(self, db):
        """get() raises NotFound when no platform exists."""
        PlatformAccount.objects.all().delete()
        with pytest.raises(NotFound):
            PlatformAccountSelector.get()

    def test_platform_exists_true(self, platform_account):
        """exists() returns True when platform exists."""
        assert PlatformAccountSelector.exists() is True

    def test_platform_exists_false(self, db):
        """exists() returns False when no platform."""
        PlatformAccount.objects.all().delete()
        assert PlatformAccountSelector.exists() is False

    def test_platform_is_configured(self, configured_platform):
        """is_configured() returns True for configured platform."""
        assert PlatformAccountSelector.is_configured() is True

    def test_platform_is_not_configured(self, platform_account):
        """is_configured() returns False for unconfigured platform."""
        platform_account.is_configured = False
        platform_account.save(update_fields=["is_configured"])
        assert PlatformAccountSelector.is_configured() is False


@pytest.mark.django_db
class TestPlatformProfileSelector:
    """Tests for PlatformProfileSelector."""

    def test_get_platform_profile(self, platform_profile):
        """get() returns the platform profile."""
        result = PlatformProfileSelector.get()
        assert result.name == platform_profile.name
        assert result.platform_id == platform_profile.platform_id

    def test_get_platform_profile_not_found(self, db):
        """get() raises NotFound when no profile exists."""
        PlatformAccount.objects.all().delete()
        with pytest.raises(NotFound):
            PlatformProfileSelector.get()
