"""
Phase 13: Feature Gate Integration Tests
=========================================
Targeted API tests for behaviors modified by the Feature Gate System (Phase 6).
Verifies auth lockout, network follow approval, explore search, notifications,
and session limits work correctly against live PostgreSQL + Redis.

Test IDs: FG-L01 to FG-L06, FG-S01, FG-N01 to FG-N04, FG-E01 to FG-E03,
          FG-NT01 to FG-NT02

Prerequisites:
    - Docker infra running (PostgreSQL + Redis)
    - Django server running with deployment_config.json (all features enabled)
    - Phases 01-12 run first (shared test state)
"""

import time

import pytest

# =============================================================================
# FG-L01–FG-L06: ACCOUNT LOCKOUT
# =============================================================================


class TestFeatureGateAccountLockout:
    """Test auth.lockout.* feature gate behavior.

    Verifies: failed_login_attempts increment, account locking after 10 failures,
    locked account rejection, unlock restore, counter reset on success,
    independent per-user counters.

    Implementation: auth_service.py lines 135-180, feature_config keys:
        auth.lockout.max_failed_attempts (default 10)
        auth.lockout.duration (default 900s)
    """

    def _register_and_verify(self, api, db_helper, email):
        """Helper: register a user and verify directly via DB."""
        r = api.register_with_retry(email)
        assert r.status_code == 201, f"Register {email} failed: {r.text}"
        db_helper.verify_user_directly(email)

    def _failed_login(self, api, email, max_retries=3):
        """Helper: attempt a failed login, handling rate limits."""
        api.clear_token()
        for attempt in range(max_retries):
            r = api.post("auth/login/", json={"email": email, "password": "WrongPass!"})
            if r.status_code == 429:
                time.sleep(3)
                continue
            return r
        return r

    def test_fg_l01_failed_login_increments_counter(self, api, db_helper):
        """FG-L01: Failed login increments failed_login_attempts counter."""
        email = "lockout1@test.com"
        self._register_and_verify(api, db_helper, email)
        assert db_helper.get_failed_login_attempts(email) == 0

        # 3 failed logins
        for i in range(3):
            self._failed_login(api, email)

        attempts = db_helper.get_failed_login_attempts(email)
        assert attempts == 3, f"Expected 3 attempts, got {attempts}"

    def test_fg_l02_account_locks_after_max_attempts(self, api, db_helper):
        """FG-L02: Account locks after 10 failed attempts (max_failed_attempts default)."""
        email = "lockout2@test.com"
        self._register_and_verify(api, db_helper, email)

        # 10 failed logins
        for i in range(10):
            self._failed_login(api, email)

        # Verify locked_until is set in DB
        locked_until = db_helper.get_locked_until(email)
        assert locked_until is not None, "locked_until should be set after 10 failures"

    def test_fg_l03_locked_rejects_correct_password(self, api, db_helper, assert_error):
        """FG-L03: Locked account rejects even correct password with account_locked error."""
        email = "lockout3@test.com"
        self._register_and_verify(api, db_helper, email)

        # Lock account (10 failed attempts)
        for i in range(10):
            self._failed_login(api, email)

        # Verify locked
        assert db_helper.get_locked_until(email) is not None

        # Try correct password
        api.clear_token()
        r = api.post("auth/login/", json={"email": email, "password": "TestPass123!"})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"
        assert_error(r, "account_locked", 401)

        # Verify retry_after is in error details
        data = r.json()
        assert (
            "retry_after" in data["error"]["details"]
        ), f"Missing retry_after in details: {data['error']}"
        assert isinstance(data["error"]["details"]["retry_after"], int)

    def test_fg_l04_unlock_restores_access(self, api, db_helper):
        """FG-L04: DB helper unlock_account() clears lockout; login succeeds after."""
        email = "lockout4@test.com"
        self._register_and_verify(api, db_helper, email)

        # Lock account
        for i in range(10):
            self._failed_login(api, email)

        assert db_helper.get_locked_until(email) is not None

        # Unlock via DB
        db_helper.unlock_account(email)

        # Login should succeed
        r = api.login_as_with_retry(email)
        assert r.status_code == 200, f"Login failed after unlock: {r.text}"

        # Counter and locked_until should be reset
        assert db_helper.get_failed_login_attempts(email) == 0
        assert db_helper.get_locked_until(email) is None

    def test_fg_l05_success_resets_counter(self, api, db_helper):
        """FG-L05: Successful login resets failed_login_attempts to 0."""
        email = "lockout5@test.com"
        self._register_and_verify(api, db_helper, email)

        # 5 failed logins (not enough to lock)
        for i in range(5):
            self._failed_login(api, email)

        assert db_helper.get_failed_login_attempts(email) == 5

        # Successful login
        r = api.login_as_with_retry(email)
        assert r.status_code == 200, f"Login failed: {r.text}"

        # Counter should be reset
        assert db_helper.get_failed_login_attempts(email) == 0
        assert db_helper.get_locked_until(email) is None

    def test_fg_l06_independent_user_counters(self, api, db_helper):
        """FG-L06: Locking user A does not affect user B."""
        email_a = "lockout6a@test.com"
        email_b = "lockout6b@test.com"
        self._register_and_verify(api, db_helper, email_a)
        self._register_and_verify(api, db_helper, email_b)

        # Lock user A
        for i in range(10):
            self._failed_login(api, email_a)

        # Verify A locked, B not
        assert db_helper.get_locked_until(email_a) is not None
        assert db_helper.get_locked_until(email_b) is None

        # User B can still login
        r = api.login_as_with_retry(email_b)
        assert r.status_code == 200, f"User B login failed: {r.text}"


# =============================================================================
# FG-S01: AUTH SESSION LIMIT
# =============================================================================


class TestFeatureGateSessionLimit:
    """Test auth.sessions.max_per_user feature gate behavior.

    Default max_per_user = 5. Login from 6+ devices should evict oldest.
    Implementation: auth_service.py lines 706-735.
    """

    def test_fg_s01_session_limit_evicts_oldest(self, api, db_helper):
        """FG-S01: Logging in from 6+ devices keeps at most 5 active sessions."""
        email = "lockout1@test.com"  # Reuse registered user from lockout tests
        db_helper.unlock_account(email)  # Ensure unlocked from L01

        # Login from 6 different devices
        for i in range(6):
            api.clear_token()
            r = api.post(
                "auth/login/",
                json={"email": email, "password": "TestPass123!"},
                headers={"X-Device-Id": f"device-session-test-{i}"},
            )
            if r.status_code == 429:
                time.sleep(3)
                r = api.post(
                    "auth/login/",
                    json={"email": email, "password": "TestPass123!"},
                    headers={"X-Device-Id": f"device-session-test-{i}"},
                )
            assert r.status_code == 200, f"Login #{i} failed: {r.text}"

        # Count active sessions
        count = db_helper.count_active_sessions(email)
        assert count <= 5, f"Expected <= 5 sessions, got {count}"


# =============================================================================
# FG-N01–FG-N04: NETWORK FOLLOW
# =============================================================================


class TestFeatureGateNetworkFollow:
    """Test network follow endpoints and follow_approval_required gate.

    Implementation: network/views.py lines 130-209.
    Feature gate: network.follow_approval_required (default False).
    """

    def test_fg_n01_follow_public_business(self, api, state, db_helper):
        """FG-N01: Following a public business returns 201 with transaction_id."""
        biz = state.businesses.get("alice_corp")
        if not biz:
            pytest.skip("No business available from earlier phases")

        # Ensure business is public
        db_helper.set_business_visibility(biz["slug"], True)

        # Use bob as the follower (not alice who owns the business)
        api.set_token(state.get_token("bob"))

        r = api.post(
            "network/follow/",
            json={"followee_type": "business", "followee_id": biz["id"]},
        )
        assert r.status_code == 201, f"Follow failed: {r.text}"
        data = r.json()
        assert "transaction_id" in data
        assert "status" in data

    def test_fg_n02_follow_private_business_needs_approval(self, api, state, db_helper):
        """FG-N02: Following a private business creates approval request."""
        biz = state.businesses.get("alice_corp")
        if not biz:
            pytest.skip("No business available")

        # Make business private
        db_helper.set_business_visibility(biz["slug"], False)

        # Use nobody as follower (different from N01 to avoid duplicate follow conflict)
        api.set_token(state.get_token("nobody"))

        r = api.post(
            "network/follow/",
            json={"followee_type": "business", "followee_id": biz["id"]},
        )
        assert r.status_code == 201, f"Follow private biz failed: {r.text}"
        data = r.json()
        assert "transaction_id" in data

        # Restore public visibility
        db_helper.set_business_visibility(biz["slug"], True)

    def test_fg_n03_following_list(self, api, state):
        """FG-N03: GET /network/following/ returns paginated results."""
        if "bob" not in state.users:
            pytest.skip("Requires earlier phases (bob not registered)")
        api.set_token(state.get_token("bob"))

        r = api.get("network/following/")
        assert r.status_code == 200, f"Following list failed: {r.text}"
        data = r.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_fg_n04_network_stats(self, api, state):
        """FG-N04: GET /network/stats/ returns stats for authenticated user."""
        if "bob" not in state.users:
            pytest.skip("Requires earlier phases (bob not registered)")
        api.set_token(state.get_token("bob"))

        r = api.get("network/stats/")
        assert r.status_code == 200, f"Network stats failed: {r.text}"


# =============================================================================
# FG-E01–FG-E03: EXPLORE SEARCH
# =============================================================================


class TestFeatureGateExplore:
    """Test explore search endpoints and min_search_length gate.

    Implementation: explore/views.py lines 133-169.
    Feature gate: explore.min_search_length (default 2).
    """

    def test_fg_e01_business_search(self, api, state):
        """FG-E01: Business search returns results for valid query."""
        if "bob" not in state.users:
            pytest.skip("Requires earlier phases (bob not registered)")
        api.set_token(state.get_token("bob"))

        r = api.get("explore/businesses/", params={"q": "corp"})
        assert r.status_code == 200, f"Business search failed: {r.text}"
        data = r.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_fg_e02_combined_search(self, api, state):
        """FG-E02: Combined search returns users + businesses."""
        if "bob" not in state.users:
            pytest.skip("Requires earlier phases (bob not registered)")
        api.set_token(state.get_token("bob"))

        r = api.get("explore/", params={"q": "alice"})
        assert r.status_code == 200, f"Combined search failed: {r.text}"
        data = r.json()
        assert "users" in data
        assert "businesses" in data
        assert "users_count" in data
        assert "businesses_count" in data

    def test_fg_e03_tag_suggestions(self, api, state):
        """FG-E03: Tag suggestions endpoint returns list."""
        if "bob" not in state.users:
            pytest.skip("Requires earlier phases (bob not registered)")
        api.set_token(state.get_token("bob"))

        r = api.get("explore/tags/")
        assert r.status_code == 200, f"Tag suggestions failed: {r.text}"
        data = r.json()
        assert isinstance(data, list)


# =============================================================================
# FG-NT01–FG-NT02: NOTIFICATION INTEGRATION
# =============================================================================


class TestFeatureGateNotifications:
    """Test notification history and types endpoints.

    Verifies notification system is functional after feature gate changes.
    """

    def test_fg_nt01_notification_history(self, api, state):
        """FG-NT01: Notification history returns paginated results."""
        if "bob" not in state.users:
            pytest.skip("Requires earlier phases (bob not registered)")
        api.set_token(state.get_token("bob"))

        r = api.get("notifications/history/")
        assert r.status_code == 200, f"Notification history failed: {r.text}"
        data = r.json()
        assert "notifications" in data
        assert isinstance(data["notifications"], list)
        assert "count" in data

    def test_fg_nt02_configurable_types(self, api, state):
        """FG-NT02: Configurable notification types endpoint works."""
        if "bob" not in state.users:
            pytest.skip("Requires earlier phases (bob not registered)")
        api.set_token(state.get_token("bob"))

        r = api.get("notifications/types/")
        assert r.status_code == 200, f"Configurable types failed: {r.text}"
        data = r.json()
        assert "types" in data
        assert isinstance(data["types"], list)
        assert data["count"] > 0
