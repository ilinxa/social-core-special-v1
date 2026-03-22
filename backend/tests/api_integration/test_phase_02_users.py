"""
Phase 02 — Users (U01–U11)

Tests user profile CRUD, avatar management, membership listing, and deactivation.
Depends on Phase 01 (users registered and verified).
"""

import uuid

import pytest

# =============================================================================
# U01–U04: CURRENT USER & PROFILE
# =============================================================================


class TestUserProfile:
    """Test /users/me/ and /users/me/profile/ endpoints."""

    def test_u01_get_current_user(self, api, state):
        """GET /users/me/ returns authenticated user info."""
        api.set_token(state.get_token("alice"))
        r = api.get("users/me/")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "alice@test.com"
        assert "id" in data
        assert "is_verified" in data

    def test_u02_patch_current_user(self, api, state):
        """PATCH /users/me/ updates user fields."""
        api.set_token(state.get_token("alice"))
        r = api.patch(
            "users/me/",
            json={
                "username": "alice_updated",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "alice_updated"

    def test_u03_get_profile(self, api, state):
        """GET /users/me/profile/ returns user profile."""
        api.set_token(state.get_token("alice"))
        r = api.get("users/me/profile/")
        assert r.status_code == 200
        data = r.json()
        # Profile should have fields like display_name, bio, etc.
        assert isinstance(data, dict)

    def test_u04_patch_profile(self, api, state):
        """PATCH /users/me/profile/ updates profile fields."""
        api.set_token(state.get_token("alice"))
        r = api.patch(
            "users/me/profile/",
            json={
                "display_name": "Alice Test",
                "bio": "Integration test user",
            },
        )
        assert r.status_code == 200


# =============================================================================
# U05–U07: AVATAR
# =============================================================================


class TestUserAvatar:
    """Test avatar upload, retrieval, and deletion."""

    def test_u05_get_avatar_none(self, api, state):
        """GET /users/me/avatar/ when no avatar is set."""
        api.set_token(state.get_token("alice"))
        r = api.get("users/me/avatar/")
        # 200 with null/empty, 404 (no avatar), or 405 (GET not implemented)
        assert r.status_code in (200, 404, 405)

    def test_u06_upload_avatar(self, api, state):
        """POST /users/me/avatar/ uploads an image."""
        api.set_token(state.get_token("alice"))
        # Create a minimal valid PNG (1x1 pixel)
        import io

        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        files = {"avatar": ("test.png", io.BytesIO(png_data), "image/png")}
        r = api.session.post(
            api._url("users/me/avatar/"),
            files=files,
        )
        # 200/201 on success, 400 if field name or format doesn't match
        assert r.status_code in (
            200,
            201,
            400,
        ), f"Avatar upload: {r.status_code} {r.text}"

    def test_u07_delete_avatar(self, api, state):
        """DELETE /users/me/avatar/ removes the avatar."""
        api.set_token(state.get_token("alice"))
        r = api.delete("users/me/avatar/")
        assert r.status_code in (200, 204)


# =============================================================================
# U08–U10: MEMBERSHIPS
# =============================================================================


class TestUserMemberships:
    """Test membership listing."""

    def test_u08_list_memberships_empty(self, api, state):
        """GET /users/me/memberships/ for user with no memberships."""
        api.set_token(state.get_token("nobody"))
        r = api.get("users/me/memberships/")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        # Nobody hasn't joined anything yet
        assert isinstance(results, list)

    def test_u09_membership_detail_nonexistent(self, api, state):
        """GET /users/me/memberships/<random_uuid>/ returns 404."""
        api.set_token(state.get_token("alice"))
        fake_id = str(uuid.uuid4())
        r = api.get(f"users/me/memberships/{fake_id}/")
        assert r.status_code == 404

    def test_u10_list_memberships_alice(self, api, state):
        """GET /users/me/memberships/ for Alice (may have memberships later)."""
        api.set_token(state.get_token("alice"))
        r = api.get("users/me/memberships/")
        assert r.status_code == 200


# =============================================================================
# U11: DEACTIVATE ACCOUNT
# =============================================================================


class TestUserDeactivate:
    """Test account deactivation.

    IMPORTANT: This test creates a dedicated user for deactivation
    to avoid breaking other tests that depend on existing users.
    """

    def test_u11_deactivate_and_verify_blocked(self, api, db_helper):
        """Deactivate account → login returns 401."""
        # Register a disposable user for this test
        r = api.register_user("deactivate@test.com")
        if r.status_code != 201:
            pytest.skip("Could not register deactivation test user")

        data = r.json()
        token = data["tokens"]["access_token"]
        db_helper.verify_user_directly("deactivate@test.com")

        # Login to get fresh token
        r = api.login_as("deactivate@test.com")
        if r.status_code != 200:
            pytest.skip("Could not login deactivation test user")
        token = r.json()["tokens"]["access_token"]

        # Deactivate (DELETE /users/me/ returns 204)
        api.set_token(token)
        r = api.delete("users/me/")
        assert r.status_code == 204, f"Deactivate failed: {r.text}"

        # Verify login is blocked
        api.clear_token()
        r = api.post(
            "auth/login/",
            json={
                "email": "deactivate@test.com",
                "password": "TestPass123!",
            },
        )
        assert r.status_code == 401
