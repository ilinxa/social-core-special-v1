"""
Tests for FG Module Gates — Phase 3.

Verifies that disabling a feature path via deployment config returns
HTTP 403 with code ``feature_disabled`` and the correct feature path
in ``details.feature``.

Each test class covers one feature gate. The "enabled" case is not tested
here — existing 4000+ tests cover normal behavior with all features on
(via the session-scoped _enable_all_features fixture).
"""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory


def _assert_feature_disabled(response, feature_path):
    """Assert response is 403 with feature_disabled code and correct path."""
    assert response.status_code == 403
    assert response.data["error"]["code"] == "feature_disabled"
    assert response.data["error"]["details"]["feature"] == feature_path


# =============================================================================
# Network
# =============================================================================


@pytest.mark.django_db
class TestNetworkUserGate:
    """user.network.enabled → 13 network user-scoped views."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"user": {"network": {"enabled": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/network/following/")
        _assert_feature_disabled(response, "user.network.enabled")


@pytest.mark.django_db
class TestNetworkBusinessGate:
    """business.network.enabled → 6 network business-scoped views."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"business": {"network": {"enabled": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/network/business/any-slug/followers/")
        _assert_feature_disabled(response, "business.network.enabled")


# =============================================================================
# Business
# =============================================================================


@pytest.mark.django_db
class TestBusinessMembersGate:
    """business.members.enabled → BusinessListCreateView POST."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"business": {"members": {"enabled": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory(can_create_business=True))
        response = client.post(
            "/api/v1/business/",
            data={"legal_name": "Test", "country": "US"},
            format="json",
        )
        _assert_feature_disabled(response, "business.members.enabled")

    def test_get_still_works_when_members_disabled(self, feature_config_override):
        """GET /api/v1/business/ should work even with members disabled (list vs create)."""
        feature_config_override({"business": {"members": {"enabled": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/business/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestBusinessProfileVisibilityGate:
    """business.profile_visibility → BusinessProfileVisibilityView."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"business": {"profile_visibility": False}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/business/any-slug/profile/visibility/")
        _assert_feature_disabled(response, "business.profile_visibility")


# =============================================================================
# Platform
# =============================================================================


@pytest.mark.django_db
class TestPlatformMembersGate:
    """platform.members.enabled → PlatformAccountView POST."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"platform": {"members": {"enabled": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory(is_superuser=True))
        response = client.post(
            "/api/v1/platform/account/", data={"name": "Test Platform"}, format="json"
        )
        _assert_feature_disabled(response, "platform.members.enabled")

    def test_get_still_works_when_members_disabled(self, feature_config_override):
        """GET /api/v1/platform/account/ should work with members disabled."""
        from apps.organization.tests.factories import PlatformAccountFactory

        PlatformAccountFactory()
        feature_config_override({"platform": {"members": {"enabled": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/platform/account/")
        assert response.status_code == 200


# =============================================================================
# Forms
# =============================================================================


@pytest.mark.django_db
class TestFormsUserGate:
    """user.forms → SystemFormTemplateView."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"user": {"forms": False}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/forms/templates/system/any-slug/")
        _assert_feature_disabled(response, "user.forms")


@pytest.mark.django_db
class TestFormsBusinessGate:
    """business.forms.enabled → FormViewMixin (via FormTemplateListView)."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"business": {"forms": {"enabled": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        fake_id = uuid4()
        response = client.get(f"/api/v1/forms/business/{fake_id}/templates/")
        _assert_feature_disabled(response, "business.forms.enabled")


@pytest.mark.django_db
class TestFormsPlatformGate:
    """platform.forms → FormViewMixin (via FormTemplateListView)."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"platform": {"forms": False}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        fake_id = uuid4()
        response = client.get(f"/api/v1/forms/platform/{fake_id}/templates/")
        _assert_feature_disabled(response, "platform.forms")


# =============================================================================
# CMS
# =============================================================================


@pytest.mark.django_db
class TestCmsPlatformGate:
    """platform.cms → 17 CMS admin views."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"platform": {"cms": False}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/cms/admin/sites/")
        _assert_feature_disabled(response, "platform.cms")


@pytest.mark.django_db
class TestCmsBusinessGate:
    """business.cms.enabled → All business CMS views."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"business": {"cms": {"enabled": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/cms/business/any-slug/catalog/sections/")
        _assert_feature_disabled(response, "business.cms.enabled")


# =============================================================================
# Explore
# =============================================================================


@pytest.mark.django_db
class TestExploreGate:
    """user.explore.can_explore → ExploreUserSearchView."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"user": {"explore": {"can_explore": False}}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/explore/users/")
        _assert_feature_disabled(response, "user.explore.can_explore")


# =============================================================================
# Users
# =============================================================================


@pytest.mark.django_db
class TestUserProfileVisibilityGate:
    """user.profile_visibility → UserProfileVisibilityView."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"user": {"profile_visibility": False}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/users/me/profile/visibility/")
        _assert_feature_disabled(response, "user.profile_visibility")


@pytest.mark.django_db
class TestUserCanCreateBusinessGate:
    """user.can_create_business → ApprovedBusinessCreatorsListView."""

    def test_disabled_returns_403(self, feature_config_override):
        feature_config_override({"user": {"can_create_business": False}})
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        response = client.get("/api/v1/platform/approved-creators/")
        _assert_feature_disabled(response, "user.can_create_business")
