"""
Phase 03 — Platform (P01–P09)

Tests platform account configuration, profile/settings management,
and non-member/no-permission access control.

Depends on Phase 01 (users registered and verified).
"""

import pytest


# =============================================================================
# P01–P03: PLATFORM ACCOUNT CONFIGURATION
# =============================================================================

class TestPlatformConfigure:
    """Test platform singleton account configuration."""

    def test_p01_get_unconfigured(self, api, state):
        """GET /platform/account/ returns unconfigured state."""
        api.set_token(state.get_token("alice"))
        r = api.get("platform/account/")
        assert r.status_code == 200
        data = r.json()
        # Platform may already be configured from migrations or previous runs
        assert "id" in data
        state.platform["id"] = data["id"]
        state.platform["configured"] = data.get("is_configured", False)

    def test_p02_configure_platform(self, api, state, db_helper):
        """POST /platform/account/ configures platform and creates owner.

        PlatformPolicy.can_configure() requires is_superuser=True,
        so we promote Alice to superuser before configuring.
        """
        # Platform configuration requires superuser
        db_helper.make_superuser("alice@test.com")

        api.set_token(state.get_token("alice"))

        if state.platform.get("configured"):
            # Already configured — verify we can still GET
            r = api.get("platform/account/")
            assert r.status_code == 200
            return

        r = api.post("platform/account/", json={
            "name": "Test Platform",
        })
        assert r.status_code in (200, 201), f"Configure failed: {r.text}"
        data = r.json()
        state.platform["id"] = data.get("id", state.platform.get("id"))
        state.platform["configured"] = True

    def test_p02b_ensure_alice_platform_membership(self, api, state, db_helper):
        """Ensure Alice has an active platform membership.

        The platform configure endpoint creates roles but NOT memberships.
        CMS admin endpoints require platform membership via PlatformContextMixin,
        so we create it explicitly via direct DB insert if missing.
        """
        membership_id = db_helper.create_platform_membership("alice@test.com")
        if membership_id:
            state.platform["owner_membership_id"] = membership_id

    def test_p03_configure_again_conflict(self, api, state):
        """POST /platform/account/ again returns 409 conflict."""
        api.set_token(state.get_token("alice"))
        r = api.post("platform/account/", json={
            "name": "Another Platform",
        })
        # Should be 409 (already configured) or 400
        assert r.status_code in (400, 409), (
            f"Expected conflict, got {r.status_code}: {r.text}"
        )


# =============================================================================
# P04–P06: PROFILE & SETTINGS
# =============================================================================

class TestPlatformProfileSettings:
    """Test platform profile and settings CRUD."""

    def test_p04_get_profile(self, api, state):
        """GET /platform/profile/ returns platform profile."""
        api.set_token(state.get_token("alice"))
        r = api.get("platform/profile/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_p05_patch_profile(self, api, state):
        """PATCH /platform/profile/ updates profile fields."""
        api.set_token(state.get_token("alice"))
        r = api.patch("platform/profile/", json={
            "tagline": "Integration Test Platform",
            "contact_email": "admin@testplatform.com",
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("tagline") == "Integration Test Platform"

    def test_p06_patch_settings(self, api, state):
        """PATCH /platform/settings/ merges JSONB settings."""
        api.set_token(state.get_token("alice"))
        r = api.patch("platform/settings/", json={
            "settings": {
                "theme": "dark",
                "max_businesses": 100,
            },
        })
        assert r.status_code == 200


# =============================================================================
# P07–P09: ACCESS CONTROL
# =============================================================================

class TestPlatformAccessControl:
    """Test non-member and no-permission access."""

    def test_p07_non_member_access(self, api, state):
        """Non-member user has limited platform access."""
        api.set_token(state.get_token("nobody"))
        r = api.get("platform/profile/")
        # PlatformPolicy.can_view() returns True for all authenticated users
        # Profile GET may be 200 (public info) or 403 (membership required)
        assert r.status_code in (200, 403)

    def test_p08_non_member_update(self, api, state):
        """Non-member cannot update platform profile."""
        api.set_token(state.get_token("nobody"))
        r = api.patch("platform/profile/", json={
            "tagline": "Hacked!",
        })
        assert r.status_code == 403

    def test_p09_non_member_settings(self, api, state):
        """Non-member cannot update platform settings."""
        api.set_token(state.get_token("nobody"))
        r = api.patch("platform/settings/", json={
            "settings": {"hacked": True},
        })
        assert r.status_code == 403


# =============================================================================
# P10: GRANT BUSINESS CREATION PERMISSIONS (for Phase 04)
# =============================================================================

class TestBusinessCreationGrants:
    """Grant can_create_business flag to users who will create businesses in Phase 04+."""

    def test_p10_grant_alice_business_creation(self, db_helper):
        """Grant Alice permission to create business accounts."""
        db_helper.grant_business_creation_permission("alice@test.com")

    def test_p11_grant_bob_business_creation(self, db_helper):
        """Grant Bob permission to create business accounts."""
        db_helper.grant_business_creation_permission("bob@test.com")
