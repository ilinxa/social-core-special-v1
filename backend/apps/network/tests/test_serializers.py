# apps/network/tests/test_serializers.py
"""
Tests for network serializer helper functions.

Covers exception handling and fallback behavior in:
- _resolve_followee_name()
- _resolve_followee_slug()
- _resolve_account_name()
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from apps.network.serializers import (
    _resolve_account_name,
    _resolve_followee_name,
    _resolve_followee_slug,
)

# =============================================================================
# _resolve_followee_name
# =============================================================================


@pytest.mark.django_db
class TestResolveFolloweeName:

    def test_business_returns_display_name(self, business):
        """Returns display name from business profile."""
        result = _resolve_followee_name("business", business.id)
        assert result  # non-empty string

    def test_unknown_type_returns_empty(self):
        """Unknown followee type returns empty string."""
        result = _resolve_followee_name("unknown_type", uuid4())
        assert result == ""

    def test_nonexistent_id_returns_empty(self):
        """Nonexistent business ID returns empty string."""
        result = _resolve_followee_name("business", uuid4())
        assert result == ""

    def test_exception_returns_empty_and_logs(self):
        """Exception in DB query returns empty string and logs warning."""
        with patch("apps.network.serializers.logger") as mock_logger:
            with patch(
                "apps.organization.business.models.BusinessAccount.objects"
            ) as mock_qs:
                mock_qs.select_related.side_effect = RuntimeError("DB error")
                result = _resolve_followee_name("business", uuid4())
                assert result == ""
                mock_logger.warning.assert_called_once()


# =============================================================================
# _resolve_followee_slug
# =============================================================================


@pytest.mark.django_db
class TestResolveFolloweeSlug:

    def test_business_returns_slug(self, business):
        """Returns slug for an existing business."""
        result = _resolve_followee_slug("business", business.id)
        assert result == business.slug

    def test_platform_returns_empty(self, platform):
        """Platform followee has no slug — returns empty string."""
        result = _resolve_followee_slug("platform", platform.id)
        assert result == ""

    def test_nonexistent_returns_empty(self):
        """Nonexistent business ID returns empty string."""
        result = _resolve_followee_slug("business", uuid4())
        assert result == ""

    def test_exception_returns_empty_and_logs(self):
        """Exception in DB query returns empty string and logs warning."""
        with patch("apps.network.serializers.logger") as mock_logger:
            with patch(
                "apps.organization.business.models.BusinessAccount.objects"
            ) as mock_qs:
                mock_qs.filter.side_effect = RuntimeError("DB error")
                result = _resolve_followee_slug("business", uuid4())
                assert result == ""
                mock_logger.warning.assert_called_once()


# =============================================================================
# _resolve_account_name
# =============================================================================


@pytest.mark.django_db
class TestResolveAccountName:

    def test_business_returns_name(self, business):
        """Returns display name for business account."""
        result = _resolve_account_name("business", business.id)
        assert result  # non-empty

    def test_unknown_type_returns_empty(self):
        """Unknown account type returns empty string."""
        result = _resolve_account_name("unknown_type", uuid4())
        assert result == ""

    def test_nonexistent_returns_empty(self):
        """Nonexistent account ID returns empty string."""
        result = _resolve_account_name("business", uuid4())
        assert result == ""

    def test_exception_returns_empty_and_logs(self):
        """Exception in DB query returns empty string and logs warning."""
        with patch("apps.network.serializers.logger") as mock_logger:
            with patch(
                "apps.organization.business.models.BusinessAccount.objects"
            ) as mock_qs:
                mock_qs.select_related.side_effect = RuntimeError("DB error")
                result = _resolve_account_name("business", uuid4())
                assert result == ""
                mock_logger.warning.assert_called_once()
