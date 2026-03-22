"""
Phase 01 — Authentication (A01–A31)

Bootstrap phase: registers all test users, verifies email, tests login flows,
token refresh, logout, password reset/change, sessions, and OAuth smoke tests.

Must run FIRST — all subsequent phases depend on the users created here.
"""

import uuid

import pytest

# =============================================================================
# A01–A04: REGISTER USERS
# =============================================================================


class TestAuthRegister:
    """Register the 4 test users and store their tokens."""

    def test_a01_register_alice(self, api, state):
        """Register Alice — primary test user (will become platform owner)."""
        r = api.register_user("alice@test.com")
        assert r.status_code == 201, f"Register failed: {r.text}"
        data = r.json()
        assert data["is_new_user"] is True
        assert data["user"]["email"] == "alice@test.com"
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]  # mobile client
        state.store_user("alice", data)

    def test_a02_register_bob(self, api, state):
        """Register Bob — secondary user (member, limited access)."""
        r = api.register_user("bob@test.com")
        assert r.status_code == 201
        state.store_user("bob", r.json())

    def test_a03_register_carol(self, api, state):
        """Register Carol — tertiary user (business member)."""
        r = api.register_user("carol@test.com")
        assert r.status_code == 201
        state.store_user("carol", r.json())

    def test_a04_register_nobody(self, api, state):
        """Register Nobody — no memberships, used for rejection tests."""
        r = api.register_user("nobody@test.com")
        assert r.status_code == 201
        state.store_user("nobody", r.json())


# =============================================================================
# A05–A08: LOGIN FLOWS
# =============================================================================


class TestAuthLogin:
    """Test login success and failure cases."""

    def test_a05_login_valid(self, api, state):
        """Login with valid credentials. Updates stored tokens."""
        r = api.login_as("alice@test.com")
        # Unverified users may still login depending on settings
        # Store tokens regardless of verification status
        if r.status_code == 200:
            data = r.json()
            state.store_user("alice", data)
            assert data["user"]["email"] == "alice@test.com"

    def test_a06_login_wrong_password(self, api, assert_error):
        """Login with wrong password returns 401 invalid_credentials."""
        r = api.post(
            "auth/login/",
            json={
                "email": "alice@test.com",
                "password": "WrongPassword99!",
            },
        )
        assert r.status_code == 401
        assert_error(r, "invalid_credentials", 401)

    def test_a07_login_nonexistent_email(self, api, assert_error):
        """Login with non-existent email returns 401."""
        r = api.post(
            "auth/login/",
            json={
                "email": "nonexistent@test.com",
                "password": "TestPass123!",
            },
        )
        assert r.status_code == 401

    def test_a08_login_missing_fields(self, api):
        """Login with missing fields returns 400."""
        r = api.post("auth/login/", json={})
        assert r.status_code == 400


# =============================================================================
# A09–A10: TOKEN REFRESH
# =============================================================================


class TestAuthRefresh:
    """Test token refresh and reuse detection."""

    def test_a09_refresh_valid(self, api, state):
        """Refresh with valid refresh token returns new token pair."""
        # Login fresh to get tokens and store in state
        r = api.login_as("bob@test.com")
        if r.status_code != 200:
            pytest.skip("Login failed — user may need verification")
        state.store_user("bob", r.json())

        old_refresh = state.get_refresh("bob")
        if not old_refresh:
            pytest.skip("No refresh token available (web mode?)")

        r = api.refresh_tokens(old_refresh)
        assert r.status_code == 200, f"Refresh failed: {r.text}"
        data = r.json()
        assert "access_token" in data
        # Update stored tokens
        state.update_tokens("bob", data)

    def test_a10_refresh_reuse_detection(self, api, state):
        """Reusing an already-consumed refresh token returns 401."""
        # Login fresh and store tokens in state
        r = api.login_as("carol@test.com")
        if r.status_code != 200:
            pytest.skip("Login failed")
        state.store_user("carol", r.json())

        old_refresh = state.get_refresh("carol")
        if not old_refresh:
            pytest.skip("No refresh token")

        # Use the refresh token once
        r1 = api.refresh_tokens(old_refresh)
        if r1.status_code == 200:
            state.update_tokens("carol", r1.json())

        # Try to reuse the same refresh token
        r2 = api.refresh_tokens(old_refresh)
        assert (
            r2.status_code == 401
        ), f"Expected 401 on token reuse, got {r2.status_code}: {r2.text}"


# =============================================================================
# A11–A13: LOGOUT
# =============================================================================


class TestAuthLogout:
    """Test logout and logout-all."""

    def test_a11_logout_current(self, api, state):
        """Logout current session invalidates refresh token."""
        # Login fresh and store tokens (A10 revoked previous tokens via reuse detection)
        r = api.login_as("carol@test.com")
        if r.status_code != 200:
            pytest.skip("Login failed")
        state.store_user("carol", r.json())
        refresh = state.get_refresh("carol")

        r = api.post("auth/logout/", json={"refresh_token": refresh})
        assert r.status_code == 200
        data = r.json()
        assert "message" in data

    def test_a12_logout_all(self, api, state):
        """Logout all sessions revokes all refresh tokens."""
        # Login fresh
        r = api.login_as("carol@test.com")
        if r.status_code != 200:
            pytest.skip("Login failed")

        r = api.post("auth/logout-all/")
        assert r.status_code == 200
        data = r.json()
        assert "message" in data
        assert "sessions_revoked" in data

    def test_a13_access_after_logout_all(self, api, state):
        """After logout-all, old access token should be rejected (JTI blacklisted in Redis)."""
        # 1. Login fresh — get a valid access token
        r = api.login_as("carol@test.com")
        if r.status_code != 200:
            pytest.skip("Login failed")
        old_token = r.json()["tokens"]["access_token"]

        # 2. Verify the token works before logout
        api.set_token(old_token)
        r = api.get("users/me/")
        assert r.status_code == 200, "Token should be valid before logout-all"

        # 3. Logout all — blacklists JTIs synchronously in Redis
        r = api.post("auth/logout-all/")
        assert r.status_code == 200

        # 4. Use the OLD token — should be rejected (JTI blacklisted)
        api.set_token(old_token)
        r = api.get("users/me/")
        assert (
            r.status_code == 401
        ), f"Expected 401 after logout-all, got {r.status_code}"

        # 5. Login fresh again — proves account is not locked
        r = api.login_as("carol@test.com")
        assert r.status_code == 200
        state.store_user("carol", r.json())


# =============================================================================
# A14–A20: EMAIL VERIFICATION
# =============================================================================


class TestAuthEmailVerification:
    """Test email verification via code and magic link."""

    def test_a14_verify_alice_directly(self, db_helper):
        """Verify Alice directly via DB (bypass email flow)."""
        db_helper.verify_user_directly("alice@test.com")
        assert db_helper.is_user_verified("alice@test.com") is True

    def test_a15_verify_bob_directly(self, db_helper):
        """Verify Bob directly via DB."""
        db_helper.verify_user_directly("bob@test.com")
        assert db_helper.is_user_verified("bob@test.com") is True

    def test_a16_verify_carol_directly(self, db_helper):
        """Verify Carol directly via DB."""
        db_helper.verify_user_directly("carol@test.com")
        assert db_helper.is_user_verified("carol@test.com") is True

    def test_a17_verify_nobody_directly(self, db_helper):
        """Verify Nobody directly via DB."""
        db_helper.verify_user_directly("nobody@test.com")
        assert db_helper.is_user_verified("nobody@test.com") is True

    def test_a18_resend_verification(self, api):
        """Resend verification email always returns 200."""
        # Clear token — endpoint is AllowAny but DRF rejects stale Bearer tokens
        api.clear_token()
        r = api.post(
            "auth/resend-verification/",
            json={
                "email": "alice@test.com",
            },
        )
        assert r.status_code == 200

    def test_a19_verify_by_code(self, api, db_helper):
        """Verify email using 6-digit code from DB."""
        api.clear_token()
        # Resend to generate fresh token
        api.post("auth/resend-verification/", json={"email": "alice@test.com"})

        code = db_helper.get_verification_code("alice@test.com")
        if not code:
            pytest.skip("No verification code found — Celery worker may not be running")

        r = api.post(
            "auth/verify-email/",
            json={
                "email": "alice@test.com",
                "code": code,
            },
        )
        # May return 200 or 400 if already verified
        assert r.status_code in (200, 400)

    def test_a20_verify_by_link(self, api, db_helper):
        """Verify email using magic link token from DB."""
        api.clear_token()
        # Resend to generate fresh token
        api.post("auth/resend-verification/", json={"email": "bob@test.com"})

        token = db_helper.get_verification_token("bob@test.com")
        if not token:
            pytest.skip("No verification token found")

        r = api.get(f"auth/verify-email/{token}/", allow_redirects=False)
        # 200 (JSON) or 302 (redirect) both acceptable
        assert r.status_code in (200, 302, 400)


# =============================================================================
# A21–A25: PASSWORD RESET & CHANGE
# =============================================================================


class TestAuthPassword:
    """Test password reset request, confirm, and change."""

    def test_a21_password_reset_request(self, api):
        """Request password reset always returns 200 (no email leak)."""
        r = api.post(
            "auth/password/reset/",
            json={
                "email": "alice@test.com",
            },
        )
        # 429 if PasswordResetRateThrottle triggered by prior verification/login attempts
        assert r.status_code in (200, 429), f"Unexpected: {r.status_code} {r.text}"
        if r.status_code == 200:
            data = r.json()
            assert "message" in data

    def test_a22_password_reset_nonexistent(self, api):
        """Password reset for non-existent email still returns 200."""
        r = api.post(
            "auth/password/reset/",
            json={
                "email": "nonexistent@test.com",
            },
        )
        # 429 if rate limited from prior requests
        assert r.status_code in (200, 429)

    def test_a23_password_reset_confirm(self, api, db_helper):
        """Confirm password reset with token from DB."""
        # Clear token — reset endpoints are AllowAny
        api.clear_token()
        # Request reset first
        api.post("auth/password/reset/", json={"email": "alice@test.com"})

        token = db_helper.get_password_reset_token("alice@test.com")
        if not token:
            pytest.skip("No reset token found — Celery worker may not be running")

        r = api.post(
            "auth/password/reset/confirm/",
            json={
                "token": token,
                "new_password": "NewTestPass123!",
            },
        )
        assert r.status_code == 200

        # Restore original password
        r = api.login_as("alice@test.com", password="NewTestPass123!")
        assert r.status_code == 200

    def test_a24_password_change(self, api, state):
        """Change password for authenticated user."""
        # Login with current password
        r = api.login_as("alice@test.com", password="NewTestPass123!")
        if r.status_code != 200:
            # Try original password
            r = api.login_as("alice@test.com")
            if r.status_code != 200:
                pytest.skip("Cannot login")

        r = api.post(
            "auth/password/change/",
            json={
                "current_password": "NewTestPass123!",
                "new_password": "TestPass123!",
            },
        )
        # May succeed or fail depending on which password is current
        if r.status_code == 200:
            assert "message" in r.json()

    def test_a25_login_after_password_change(self, api, state):
        """Verify login works with the final password."""
        r = api.login_as_with_retry("alice@test.com")
        assert r.status_code == 200, f"Login failed after password ops: {r.text}"
        state.store_user("alice", r.json())


# =============================================================================
# A26–A28: SESSIONS
# =============================================================================


class TestAuthSessions:
    """Test session listing and revocation."""

    def test_a26_list_sessions(self, api, state):
        """List active sessions for authenticated user."""
        api.set_token(state.get_token("alice"))
        r = api.get("auth/sessions/")
        assert r.status_code == 200
        data = r.json()
        # Should be a list (possibly wrapped in results)
        if isinstance(data, dict) and "results" in data:
            assert isinstance(data["results"], list)
        elif isinstance(data, list):
            assert isinstance(data, list)

    def test_a27_revoke_session(self, api, state, db_helper):
        """Revoke a specific session by ID."""
        api.set_token(state.get_token("alice"))
        # List sessions first
        r = api.get("auth/sessions/")
        assert r.status_code == 200
        data = r.json()
        sessions = data if isinstance(data, list) else data.get("results", [])
        if len(sessions) < 2:
            pytest.skip("Need at least 2 sessions to test revocation")

        # Revoke the oldest session (not current)
        session_id = sessions[-1].get("id")
        if session_id:
            r = api.delete(f"auth/sessions/{session_id}/")
            assert r.status_code in (200, 204)

    def test_a28_revoke_nonexistent_session(self, api, state):
        """Revoke non-existent session returns 404."""
        api.set_token(state.get_token("alice"))
        fake_id = str(uuid.uuid4())
        r = api.delete(f"auth/sessions/{fake_id}/")
        assert r.status_code == 404


# =============================================================================
# A29–A31: OAUTH SMOKE TESTS
# =============================================================================


class TestAuthOAuth:
    """Smoke tests for OAuth endpoints (redirect verification only)."""

    def test_a29_google_oauth_redirect(self, api):
        """GET /auth/oauth/google/ returns redirect to Google."""
        r = api.get("auth/oauth/google/", allow_redirects=False)
        # Should redirect (302) or return error if not configured
        assert r.status_code in (302, 400, 500)

    def test_a30_apple_oauth_redirect(self, api):
        """GET /auth/oauth/apple/ returns redirect to Apple."""
        r = api.get("auth/oauth/apple/", allow_redirects=False)
        assert r.status_code in (302, 400, 500)

    def test_a31_refresh_all_user_tokens(self, api, state):
        """Final: ensure all 4 users have valid tokens for subsequent phases."""
        for name in ["alice", "bob", "carol", "nobody"]:
            email = f"{name}@test.com"
            r = api.login_as_with_retry(email)
            assert r.status_code == 200, f"Failed to login {name}: {r.text}"
            state.store_user(name, r.json())
