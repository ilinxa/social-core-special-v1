"""
E2E Test: BUG-009 — Cross-type transaction conflict guard.

Verifies that:
- B-88: A pending business_membership_request BLOCKS creating a business_membership_invitation for the same user
- B-89: A pending business_membership_invitation BLOCKS creating a business_membership_request for the same user

Requires:
    make dev-up && make dev-migrate && make dev  (in separate terminal)
"""

import pytest
import requests

BASE = "http://localhost:8000/api/v1"
PASSWORD = "TestPass123!"


# =============================================================================
# HELPERS
# =============================================================================


class Client:
    """Minimal HTTP client for E2E testing."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers["X-Client-Type"] = "mobile"

    def _url(self, path):
        return f"{BASE}/{path.lstrip('/')}"

    def set_token(self, token):
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_token(self):
        self.session.headers.pop("Authorization", None)

    def register(self, email, username):
        self.clear_token()
        return self.session.post(self._url("auth/register/"), json={
            "email": email, "username": username, "password": PASSWORD,
        })

    def login(self, email):
        self.clear_token()
        r = self.session.post(self._url("auth/login/"), json={
            "email": email, "password": PASSWORD,
        })
        if r.status_code == 200:
            self.set_token(r.json()["tokens"]["access_token"])
        return r

    def get(self, path, **kw):
        return self.session.get(self._url(path), **kw)

    def post(self, path, json=None, **kw):
        return self.session.post(self._url(path), json=json, **kw)

    def patch(self, path, json=None, **kw):
        return self.session.patch(self._url(path), json=json, **kw)


def db_execute(sql, params=None, fetch=True):
    """Direct PostgreSQL query."""
    import psycopg2
    conn = psycopg2.connect(
        dbname="backend_core_db", user="django_user",
        password="postgres_dev_password", host="localhost", port=5432,
    )
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch and cur.description:
                return cur.fetchall()
            return None
    finally:
        conn.close()


def verify_user(email):
    db_execute("UPDATE users SET is_verified = TRUE WHERE email = %s", (email,), fetch=False)


def grant_business_creation(email):
    db_execute(
        "UPDATE users SET can_create_business = TRUE WHERE email = %s",
        (email,), fetch=False,
    )


def set_max_members(biz_id, n):
    db_execute(
        "UPDATE business_account SET max_members = %s WHERE id = %s::uuid",
        (n, str(biz_id)), fetch=False,
    )


def set_open_member_request(biz_id, value):
    db_execute(
        "UPDATE business_account SET open_member_request = %s WHERE id = %s::uuid",
        (value, str(biz_id)), fetch=False,
    )


def get_user_id(email):
    row = db_execute("SELECT id FROM users WHERE email = %s", (email,))
    return str(row[0][0]) if row else None


# =============================================================================
# TEST
# =============================================================================


class TestBug009ConflictGuard:
    """E2E: Cross-type transaction conflict guard (BUG-009)."""

    @pytest.fixture(autouse=True, scope="class")
    def setup_users_and_business(self, request):
        """Create owner + external user, a business, then store IDs for all tests."""
        import uuid

        # Unique emails to avoid collisions
        tag = uuid.uuid4().hex[:8]
        owner_email = f"bug009_owner_{tag}@test.com"
        user_email = f"bug009_user_{tag}@test.com"

        # --- Register & verify both users ---
        owner = Client()
        r = owner.register(owner_email, f"owner_{tag}")
        assert r.status_code == 201, f"Owner register failed: {r.text}"
        verify_user(owner_email)
        grant_business_creation(owner_email)
        r = owner.login(owner_email)
        assert r.status_code == 200, f"Owner login failed: {r.text}"

        user = Client()
        r = user.register(user_email, f"user_{tag}")
        assert r.status_code == 201, f"User register failed: {r.text}"
        verify_user(user_email)
        r = user.login(user_email)
        assert r.status_code == 200, f"User login failed: {r.text}"

        # --- Create business ---
        r = owner.post("business/", json={
            "legal_name": f"Bug009 Corp {tag}",
            "country": "US",
        })
        assert r.status_code == 201, f"Create business failed: {r.text}"
        biz = r.json()
        biz_id = biz["id"]
        biz_slug = biz["slug"]

        # Allow invitations (raise max_members from production default of 1)
        set_max_members(biz_id, 10)
        # Allow external requests
        set_open_member_request(biz_id, True)

        # Get the base member role for the business
        role_row = db_execute(
            "SELECT id FROM rbac_role WHERE account_type = 'business' AND account_id = %s::uuid "
            "AND is_deleted = FALSE ORDER BY level DESC LIMIT 1",
            (str(biz_id),),
        )
        base_role_id = str(role_row[0][0]) if role_row else None

        # Store on class for test methods
        request.cls.owner = owner
        request.cls.user = user
        request.cls.owner_email = owner_email
        request.cls.user_email = user_email
        request.cls.biz_id = biz_id
        request.cls.biz_slug = biz_slug
        request.cls.user_id = get_user_id(user_email)
        request.cls.base_role_id = base_role_id

    def _cancel_transaction(self, client, txn_id):
        """Cancel a transaction to clean up between tests."""
        r = client.post(f"transactions/{txn_id}/cancel/")
        assert r.status_code in (200, 409), f"Cancel failed: {r.text}"

    # -----------------------------------------------------------------
    # B-88: Pending REQUEST blocks INVITATION
    # -----------------------------------------------------------------

    def test_b88_pending_request_blocks_invitation(self):
        """B-88: User sends request → Owner tries to invite same user → 409."""
        # User sends a membership request
        r = self.user.post("transactions/request/", json={
            "transaction_type": "business_membership_request",
            "target_account_type": "business",
            "target_account_id": self.biz_id,
        })
        assert r.status_code == 201, f"Create request failed: {r.text}"
        request_txn_id = r.json()["id"]

        try:
            # Owner tries to invite the same user → should be blocked
            r = self.owner.post("transactions/invitation/", json={
                "transaction_type": "business_membership_invitation",
                "target_user_id": self.user_id,
                "context_type": "business",
                "context_id": self.biz_id,
                "payload": {"role_id": self.base_role_id},
            })
            assert r.status_code == 409, (
                f"Expected 409 (cross-type conflict), got {r.status_code}: {r.text}"
            )
            data = r.json()
            assert "conflict" in data.get("error", {}).get("code", "").lower() or \
                   "duplicate" in str(data).lower() or \
                   "already" in str(data).lower(), \
                f"Expected conflict error, got: {data}"
        finally:
            # Clean up: cancel the request
            self._cancel_transaction(self.user, request_txn_id)

    # -----------------------------------------------------------------
    # B-89: Pending INVITATION blocks REQUEST
    # -----------------------------------------------------------------

    def test_b89_pending_invitation_blocks_request(self):
        """B-89: Owner sends invitation → User tries to request → 409."""
        # Owner sends invitation to user
        r = self.owner.post("transactions/invitation/", json={
            "transaction_type": "business_membership_invitation",
            "target_user_id": self.user_id,
            "context_type": "business",
            "context_id": self.biz_id,
            "payload": {"role_id": self.base_role_id},
        })
        assert r.status_code == 201, f"Create invitation failed: {r.text}"
        invitation_txn_id = r.json()["id"]

        try:
            # User tries to send a request to the same business → should be blocked
            r = self.user.post("transactions/request/", json={
                "transaction_type": "business_membership_request",
                "target_account_type": "business",
                "target_account_id": self.biz_id,
            })
            assert r.status_code == 409, (
                f"Expected 409 (cross-type conflict), got {r.status_code}: {r.text}"
            )
            data = r.json()
            assert "conflict" in data.get("error", {}).get("code", "").lower() or \
                   "duplicate" in str(data).lower() or \
                   "already" in str(data).lower(), \
                f"Expected conflict error, got: {data}"
        finally:
            # Clean up: cancel the invitation
            self._cancel_transaction(self.owner, invitation_txn_id)

    # -----------------------------------------------------------------
    # Verify: After cancellation, cross-type creation succeeds
    # -----------------------------------------------------------------

    def test_request_succeeds_after_invitation_cancelled(self):
        """After invitation is cancelled, user can send a request."""
        # Owner sends invitation
        r = self.owner.post("transactions/invitation/", json={
            "transaction_type": "business_membership_invitation",
            "target_user_id": self.user_id,
            "context_type": "business",
            "context_id": self.biz_id,
            "payload": {"role_id": self.base_role_id},
        })
        assert r.status_code == 201, f"Create invitation failed: {r.text}"
        inv_id = r.json()["id"]

        # Cancel it
        self._cancel_transaction(self.owner, inv_id)

        # Now user can request
        r = self.user.post("transactions/request/", json={
            "transaction_type": "business_membership_request",
            "target_account_type": "business",
            "target_account_id": self.biz_id,
        })
        assert r.status_code == 201, f"Request should succeed after cancel: {r.text}"
        req_id = r.json()["id"]

        # Clean up
        self._cancel_transaction(self.user, req_id)

    # -----------------------------------------------------------------
    # Verify: _relationship injection on business detail
    # -----------------------------------------------------------------

    def test_relationship_shows_active_transaction(self):
        """Business detail shows _relationship with active transaction for authenticated user."""
        # User sends a request
        r = self.user.post("transactions/request/", json={
            "transaction_type": "business_membership_request",
            "target_account_type": "business",
            "target_account_id": self.biz_id,
        })
        assert r.status_code == 201, f"Create request failed: {r.text}"
        req_id = r.json()["id"]

        try:
            # User fetches business detail → should see _relationship
            r = self.user.get(f"business/{self.biz_slug}/")
            assert r.status_code == 200, f"Get business failed: {r.text}"
            data = r.json()

            assert "_relationship" in data, f"Missing _relationship in response: {list(data.keys())}"
            rel = data["_relationship"]
            assert rel["membership_status"] is None, f"Should be non-member, got: {rel['membership_status']}"
            assert rel["active_transaction"] is not None, f"Should have active transaction"
            assert rel["active_transaction"]["id"] == req_id
            assert rel["active_transaction"]["mode"] == "request"
            assert rel["active_transaction"]["status"] == "pending"
        finally:
            self._cancel_transaction(self.user, req_id)

    def test_relationship_absent_for_anonymous(self):
        """Business detail does NOT include _relationship for anonymous users."""
        anon = Client()  # No token
        r = anon.get(f"business/{self.biz_slug}/")
        assert r.status_code == 200, f"Get business failed: {r.text}"
        data = r.json()

        assert "_relationship" not in data, f"Anonymous should not get _relationship: {list(data.keys())}"


# =============================================================================
# PLATFORM CONFLICT GUARD
# =============================================================================


def _ensure_platform_owner_membership(owner_email, platform_id):
    """Ensure a user has an owner membership on the platform."""
    user_id = get_user_id(owner_email)
    existing = db_execute(
        "SELECT id FROM rbac_membership WHERE user_id = %s::uuid "
        "AND account_type = 'platform' AND is_deleted = FALSE",
        (user_id,),
    )
    if existing:
        return str(existing[0][0])

    role_row = db_execute(
        "SELECT id FROM rbac_role WHERE account_type = 'platform' "
        "AND account_id = %s::uuid AND is_deleted = FALSE ORDER BY level ASC LIMIT 1",
        (platform_id,),
    )
    if not role_row:
        return None

    import uuid as uuid_mod
    mid = str(uuid_mod.uuid4())
    db_execute(
        "INSERT INTO rbac_membership (id, user_id, account_type, account_id, "
        "role_id, is_owner, status, joined_at, status_reason, "
        "created_at, updated_at, is_deleted) "
        "VALUES (%s, %s, 'platform', %s, %s, TRUE, 'active', NOW(), '', "
        "NOW(), NOW(), FALSE)",
        (mid, user_id, platform_id, str(role_row[0][0])),
        fetch=False,
    )
    return mid


class TestPlatformConflictGuard:
    """E2E: Cross-type transaction conflict guard for platform membership.

    Mirrors TestBug009ConflictGuard but for platform_membership_invitation
    and platform_membership_request conflict group.
    """

    @pytest.fixture(autouse=True, scope="class")
    def setup_platform_users(self, request):
        """Create platform owner + external user for conflict tests."""
        import uuid

        tag = uuid.uuid4().hex[:8]
        owner_email = f"pguard_owner_{tag}@test.com"
        user_email = f"pguard_user_{tag}@test.com"

        # Register & verify owner
        owner = Client()
        r = owner.register(owner_email, f"powner_{tag}")
        assert r.status_code == 201, f"Owner register failed: {r.text}"
        verify_user(owner_email)
        db_execute(
            "UPDATE users SET is_superuser = TRUE, is_staff = TRUE WHERE email = %s",
            (owner_email,), fetch=False,
        )
        r = owner.login(owner_email)
        assert r.status_code == 200, f"Owner login failed: {r.text}"

        # Register & verify user
        user = Client()
        r = user.register(user_email, f"puser_{tag}")
        assert r.status_code == 201, f"User register failed: {r.text}"
        verify_user(user_email)
        r = user.login(user_email)
        assert r.status_code == 200, f"User login failed: {r.text}"

        # Get platform ID
        r = owner.get("platform/account/")
        assert r.status_code == 200, f"Get platform failed: {r.text}"
        platform_id = r.json()["id"]

        # Enable open member requests
        db_execute(
            "UPDATE platform_account SET open_member_request = TRUE WHERE id = %s::uuid",
            (platform_id,), fetch=False,
        )

        # Ensure owner has platform membership
        _ensure_platform_owner_membership(owner_email, platform_id)

        # Get base member role
        role_row = db_execute(
            "SELECT id FROM rbac_role WHERE account_type = 'platform' "
            "AND account_id = %s::uuid AND is_deleted = FALSE ORDER BY level DESC LIMIT 1",
            (platform_id,),
        )
        base_role_id = str(role_row[0][0]) if role_row else None

        request.cls.owner = owner
        request.cls.user = user
        request.cls.platform_id = platform_id
        request.cls.user_id = get_user_id(user_email)
        request.cls.base_role_id = base_role_id

    def _cancel_transaction(self, client, txn_id):
        r = client.post(f"transactions/{txn_id}/cancel/")
        assert r.status_code in (200, 409), f"Cancel failed: {r.text}"

    # -----------------------------------------------------------------
    # Platform: Pending REQUEST blocks INVITATION
    # -----------------------------------------------------------------

    def test_platform_pending_request_blocks_invitation(self):
        """User sends platform request → Owner tries to invite → 409."""
        r = self.user.post("transactions/request/", json={
            "transaction_type": "platform_membership_request",
            "target_account_type": "platform",
            "target_account_id": self.platform_id,
        })
        assert r.status_code == 201, f"Create request failed: {r.text}"
        request_txn_id = r.json()["id"]

        try:
            r = self.owner.post("transactions/invitation/", json={
                "transaction_type": "platform_membership_invitation",
                "target_user_id": self.user_id,
                "context_type": "platform",
                "context_id": self.platform_id,
                "payload": {"role_id": self.base_role_id},
            })
            assert r.status_code == 409, (
                f"Expected 409 (cross-type conflict), got {r.status_code}: {r.text}"
            )
        finally:
            self._cancel_transaction(self.user, request_txn_id)

    # -----------------------------------------------------------------
    # Platform: Pending INVITATION blocks REQUEST
    # -----------------------------------------------------------------

    def test_platform_pending_invitation_blocks_request(self):
        """Owner sends platform invitation → User tries to request → 409."""
        r = self.owner.post("transactions/invitation/", json={
            "transaction_type": "platform_membership_invitation",
            "target_user_id": self.user_id,
            "context_type": "platform",
            "context_id": self.platform_id,
            "payload": {"role_id": self.base_role_id},
        })
        assert r.status_code == 201, f"Create invitation failed: {r.text}"
        invitation_txn_id = r.json()["id"]

        try:
            r = self.user.post("transactions/request/", json={
                "transaction_type": "platform_membership_request",
                "target_account_type": "platform",
                "target_account_id": self.platform_id,
            })
            assert r.status_code == 409, (
                f"Expected 409 (cross-type conflict), got {r.status_code}: {r.text}"
            )
        finally:
            self._cancel_transaction(self.owner, invitation_txn_id)

    # -----------------------------------------------------------------
    # Platform: After cancellation, cross-type creation succeeds
    # -----------------------------------------------------------------

    def test_platform_request_succeeds_after_cancellation(self):
        """After platform invitation is cancelled, user can request."""
        r = self.owner.post("transactions/invitation/", json={
            "transaction_type": "platform_membership_invitation",
            "target_user_id": self.user_id,
            "context_type": "platform",
            "context_id": self.platform_id,
            "payload": {"role_id": self.base_role_id},
        })
        assert r.status_code == 201
        inv_id = r.json()["id"]

        self._cancel_transaction(self.owner, inv_id)

        r = self.user.post("transactions/request/", json={
            "transaction_type": "platform_membership_request",
            "target_account_type": "platform",
            "target_account_id": self.platform_id,
        })
        assert r.status_code == 201, f"Request should succeed after cancel: {r.text}"
        req_id = r.json()["id"]
        self._cancel_transaction(self.user, req_id)

    # -----------------------------------------------------------------
    # Platform: _relationship injection
    # -----------------------------------------------------------------

    def test_platform_relationship_shows_active_transaction(self):
        """Platform detail shows _relationship with active transaction."""
        r = self.user.post("transactions/request/", json={
            "transaction_type": "platform_membership_request",
            "target_account_type": "platform",
            "target_account_id": self.platform_id,
        })
        assert r.status_code == 201, f"Create request failed: {r.text}"
        req_id = r.json()["id"]

        try:
            r = self.user.get("platform/account/")
            assert r.status_code == 200
            data = r.json()

            assert "_relationship" in data, (
                f"Missing _relationship: {list(data.keys())}"
            )
            rel = data["_relationship"]
            assert rel["membership_status"] is None
            assert rel["active_transaction"] is not None
            assert rel["active_transaction"]["id"] == req_id
            assert rel["active_transaction"]["mode"] == "request"
            assert rel["active_transaction"]["status"] == "pending"
        finally:
            self._cancel_transaction(self.user, req_id)

    def test_platform_relationship_absent_for_anonymous(self):
        """Platform detail does NOT include _relationship for anonymous users."""
        anon = Client()
        r = anon.get("platform/account/")
        assert r.status_code == 200
        data = r.json()

        assert "_relationship" not in data, (
            f"Anonymous should not get _relationship: {list(data.keys())}"
        )
