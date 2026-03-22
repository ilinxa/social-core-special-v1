"""
API Integration Test Infrastructure.

Provides session-scoped helpers for making real HTTP requests against
a running Django server backed by Docker PostgreSQL + Redis.

Prerequisites:
    make dev-up && make dev-migrate && make dev  (in separate terminal)
"""

import time
import uuid

import psycopg2
import pytest
import redis as redis_lib
import requests

# =============================================================================
# PYTEST HOOKS — Enforce definition order (prevent pytest-django reordering)
# =============================================================================


def pytest_collection_modifyitems(items):
    """Preserve test definition order within each module.

    pytest-django reorders tests based on fixture dependencies (especially 'db').
    We rename our DB fixture to 'db_helper' to avoid collision, but this hook
    provides extra safety to keep tests in the order they appear in source files.
    """

    # Sort by: (module file path, class line number, function line number)
    def sort_key(item):
        # Get the module's file path for inter-file ordering
        fspath = str(item.fspath)
        # Get the line number for intra-file ordering
        # item.reportinfo() returns (fspath, lineno, test_id)
        _, lineno, _ = item.reportinfo()
        return (fspath, lineno or 0)

    items.sort(key=sort_key)


# =============================================================================
# API HELPER — HTTP client with token management
# =============================================================================


class APIHelper:
    """HTTP client that wraps requests.Session with auth token management."""

    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        # Mobile client type ensures refresh tokens come in response body
        self.session.headers["X-Client-Type"] = "mobile"

    def _url(self, path):
        return f"{self.base_url}/{path.lstrip('/')}"

    def set_token(self, token):
        """Set Authorization: Bearer header."""
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_token(self):
        """Remove Authorization header."""
        self.session.headers.pop("Authorization", None)

    def get(self, path, **kwargs):
        return self.session.get(self._url(path), **kwargs)

    def post(self, path, json=None, **kwargs):
        return self.session.post(self._url(path), json=json, **kwargs)

    def patch(self, path, json=None, **kwargs):
        return self.session.patch(self._url(path), json=json, **kwargs)

    def put(self, path, json=None, **kwargs):
        return self.session.put(self._url(path), json=json, **kwargs)

    def delete(self, path, **kwargs):
        return self.session.delete(self._url(path), **kwargs)

    # -- Convenience auth methods --

    def register_user(self, email, password="TestPass123!", username=None):
        """Register a new user. Returns response object.

        RegisterSerializer fields: email, username, password (+ optional device_*).
        If username is not provided, it's derived from the email local part.
        Clears any stale Bearer token first (AllowAny endpoints still
        validate tokens if present via DRF authentication classes).
        """
        if username is None:
            # Derive username from email local part (e.g., alice@test.com -> alice)
            local = email.split("@")[0].replace(".", "_").replace("-", "_")
            # Ensure minimum 5 chars for regex validation
            if len(local) < 5:
                local = local + "_user"
            username = local
        self.clear_token()
        return self.post(
            "auth/register/",
            json={
                "email": email,
                "username": username,
                "password": password,
            },
        )

    def login_as(self, email, password="TestPass123!"):
        """Login and set Bearer token. Returns response object.

        Clears any stale Bearer token first — DRF validates tokens on
        AllowAny endpoints, so a revoked/expired token in the session
        headers would cause 401 even on login.
        """
        self.clear_token()
        r = self.post(
            "auth/login/",
            json={
                "email": email,
                "password": password,
            },
        )
        if r.status_code == 200:
            data = r.json()
            self.set_token(data["tokens"]["access_token"])
        return r

    def refresh_tokens(self, refresh_token):
        """Refresh access token using refresh token. Returns response.

        Clears Bearer token first — RefreshView has AllowAny permission,
        so no auth needed. A stale/revoked token in the header would cause
        JWTAuthentication to 500 during validation before the view runs.
        """
        self.clear_token()
        return self.post(
            "auth/refresh/",
            json={
                "refresh_token": refresh_token,
            },
        )

    def login_as_with_retry(self, email, password="TestPass123!", max_wait=60):
        """Login with rate-limit retry. Waits up to max_wait seconds if throttled."""
        r = self.login_as(email, password)
        if r.status_code == 429:
            # Extract wait time from response
            import re

            wait = 30  # default
            try:
                text = r.json().get("error", {}).get("message", "")
                match = re.search(r"(\d+)\s+second", text)
                if match:
                    wait = int(match.group(1)) + 1
            except Exception:
                pass
            wait = min(wait, max_wait)
            time.sleep(wait)
            r = self.login_as(email, password)
        return r

    def register_with_retry(
        self, email, password="TestPass123!", username=None, max_wait=60
    ):
        """Register with rate-limit retry."""
        r = self.register_user(email, password, username=username)
        if r.status_code == 429:
            import re

            wait = 30
            try:
                text = r.json().get("error", {}).get("message", "")
                match = re.search(r"(\d+)\s+second", text)
                if match:
                    wait = int(match.group(1)) + 1
            except Exception:
                pass
            wait = min(wait, max_wait)
            time.sleep(wait)
            r = self.register_user(email, password, username=username)
        return r


# =============================================================================
# TEST STATE — Session-wide shared state across all test phases
# =============================================================================


class TestState:
    """Mutable container for sharing state between ordered test phases.

    All test phases run sequentially in a single pytest session.
    State created in phase 01 (auth) is consumed by all subsequent phases.
    """

    def __init__(self):
        # name -> {id, email, access_token, refresh_token}
        self.users = {}
        # name -> {id, slug}
        self.businesses = {}
        # {id, configured, owner_membership_id}
        self.platform = {}
        # "context:name" -> {id, permissions}
        self.roles = {}
        # name -> {id, type, status}
        self.transactions = {}
        # name -> {template_id, response_id}
        self.forms = {}
        # name -> {site_id, site_slug, page_slug, api_key_id, raw_key}
        self.cms = {}
        # "context:user" -> {id, role_id}
        self.memberships = {}
        # Permissions from GET /rbac/permissions/
        self.permissions = []

    def store_user(self, name, response_data):
        """Store user data from register/login response."""
        self.users[name] = {
            "id": response_data["user"]["id"],
            "email": response_data["user"]["email"],
            "access_token": response_data["tokens"]["access_token"],
            "refresh_token": response_data["tokens"].get("refresh_token"),
        }

    def get_token(self, name):
        """Get access token for named user."""
        return self.users[name]["access_token"]

    def get_refresh(self, name):
        """Get refresh token for named user."""
        return self.users[name]["refresh_token"]

    def update_tokens(self, name, tokens_data):
        """Update tokens after refresh."""
        self.users[name]["access_token"] = tokens_data["access_token"]
        if tokens_data.get("refresh_token"):
            self.users[name]["refresh_token"] = tokens_data["refresh_token"]


# =============================================================================
# DB HELPER — Direct PostgreSQL queries for out-of-band data
# =============================================================================


class DBHelper:
    """Direct PostgreSQL access for data not available through API.

    Used to retrieve email verification codes, password reset tokens,
    and other data that would normally arrive via email.
    """

    PG_CONFIG = {
        "dbname": "backend_core_db",
        "user": "django_user",
        "password": "postgres_dev_password",
        "host": "localhost",
        "port": 5432,
    }

    def _connect(self):
        return psycopg2.connect(**self.PG_CONFIG)

    def execute(self, sql, params=None, fetch=True):
        """Execute SQL and optionally fetch results."""
        conn = self._connect()
        try:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if fetch and cur.description:
                    return cur.fetchall()
                return None
        finally:
            conn.close()

    def execute_one(self, sql, params=None):
        """Execute SQL and fetch single row."""
        rows = self.execute(sql, params, fetch=True)
        return rows[0] if rows else None

    def get_verification_code(self, email, retries=15, delay=1.0):
        """Poll for 6-digit email verification code.

        Celery may be async, so we poll with retry.
        Returns the code string or None if not found after retries.
        """
        sql = """
            SELECT code FROM auth_verification_tokens
            WHERE email = %s AND is_used = FALSE
            ORDER BY created_at DESC LIMIT 1
        """
        for _ in range(retries):
            row = self.execute_one(sql, (email,))
            if row:
                return row[0]
            time.sleep(delay)
        return None

    def get_verification_token(self, email, retries=15, delay=1.0):
        """Poll for UUID verification token (magic link).

        Returns UUID string or None.
        """
        sql = """
            SELECT token FROM auth_verification_tokens
            WHERE email = %s AND is_used = FALSE
            ORDER BY created_at DESC LIMIT 1
        """
        for _ in range(retries):
            row = self.execute_one(sql, (email,))
            if row:
                return str(row[0])
            time.sleep(delay)
        return None

    def get_password_reset_token(self, email, retries=15, delay=1.0):
        """Poll for password reset UUID token.

        Returns UUID string or None.
        """
        sql = """
            SELECT t.token FROM auth_password_reset_tokens t
            JOIN users u ON t.user_id = u.id
            WHERE u.email = %s AND t.is_used = FALSE
            ORDER BY t.created_at DESC LIMIT 1
        """
        for _ in range(retries):
            row = self.execute_one(sql, (email,))
            if row:
                return str(row[0])
            time.sleep(delay)
        return None

    def verify_user_directly(self, email):
        """Set is_verified=TRUE directly in DB. Bypasses email flow."""
        sql = "UPDATE users SET is_verified = TRUE WHERE email = %s"
        self.execute(sql, (email,), fetch=False)

    def get_user_id(self, email):
        """Look up user UUID by email. Returns string UUID."""
        row = self.execute_one("SELECT id FROM users WHERE email = %s", (email,))
        return str(row[0]) if row else None

    def is_user_verified(self, email):
        """Check if user is verified."""
        row = self.execute_one(
            "SELECT is_verified FROM users WHERE email = %s", (email,)
        )
        return row[0] if row else False

    def get_refresh_token_jti(self, user_email):
        """Get the most recent refresh token JTI for a user."""
        sql = """
            SELECT rt.jti FROM auth_refresh_tokens rt
            JOIN users u ON rt.user_id = u.id
            WHERE u.email = %s AND rt.is_revoked = FALSE
            ORDER BY rt.created_at DESC LIMIT 1
        """
        row = self.execute_one(sql, (user_email,))
        return str(row[0]) if row else None

    def is_refresh_token_revoked(self, jti):
        """Check if a refresh token JTI is revoked."""
        row = self.execute_one(
            "SELECT is_revoked FROM auth_refresh_tokens WHERE jti = %s",
            (str(jti),),
        )
        return row[0] if row else None

    def count_active_sessions(self, email):
        """Count active device sessions for a user."""
        sql = """
            SELECT COUNT(*) FROM auth_device_sessions ds
            JOIN users u ON ds.user_id = u.id
            WHERE u.email = %s AND ds.is_active = TRUE
        """
        row = self.execute_one(sql, (email,))
        return row[0] if row else 0

    def get_base_member_role_id(self, account_type, account_id):
        """Get the base member role (highest level) for an account.

        Returns UUID string or None.
        """
        row = self.execute_one(
            """
            SELECT id FROM rbac_role
            WHERE account_type = %s AND account_id = %s AND is_deleted = FALSE
            ORDER BY level DESC LIMIT 1
            """,
            (account_type, str(account_id)),
        )
        return str(row[0]) if row else None

    def create_system_form_response(
        self, template_slug, user_email, data, context_type="", context_id=None
    ):
        """Create a form response for a system-owned form template via direct SQL.

        System forms have owner_type='system' and owner_id=NULL, so the standard
        forms API (which requires membership) cannot create responses for them.

        Returns the form response UUID string, or None on failure.
        """
        import json as json_mod

        # Look up template
        row = self.execute_one(
            "SELECT id, version FROM form_template WHERE slug = %s AND owner_type = 'system' AND is_deleted = FALSE",
            (template_slug,),
        )
        if not row:
            return None
        template_id, version = str(row[0]), row[1]

        # Look up user
        user_id = self.get_user_id(user_email)
        if not user_id:
            return None

        response_id = str(uuid.uuid4())
        submitter_context = json_mod.dumps({"user_id": user_id})
        data_json = json_mod.dumps(data)

        self.execute(
            """
            INSERT INTO form_response (
                id, form_template_id, form_version, submitted_by_id,
                submitter_context, data, status, submitted_at,
                processor_notes, context_type, context_id,
                revision, revision_history,
                created_at, updated_at, is_deleted
            ) VALUES (
                %s, %s, %s, %s,
                %s::jsonb, %s::jsonb, 'submitted', NOW(),
                '', %s, %s,
                1, '[]'::jsonb,
                NOW(), NOW(), FALSE
            )
            """,
            (
                response_id,
                template_id,
                version,
                user_id,
                submitter_context,
                data_json,
                context_type,
                str(context_id) if context_id else None,
            ),
            fetch=False,
        )
        return response_id

    def make_superuser(self, email):
        """Promote a user to superuser + staff. Required for platform configuration."""
        self.execute(
            "UPDATE users SET is_superuser = TRUE, is_staff = TRUE WHERE email = %s",
            (email,),
            fetch=False,
        )

    def grant_business_creation_permission(self, email):
        """Set can_create_business=True for a user."""
        self.execute(
            "UPDATE users SET can_create_business = TRUE WHERE email = %s",
            (email,),
            fetch=False,
        )

    def set_business_max_members(self, business_id, max_members):
        """Set max_members for a business account.

        Production default is max_members=1 (owner-only). Integration tests
        that invite/request members must raise this to allow multiple members.
        """
        self.execute(
            "UPDATE business_account SET max_members = %s WHERE id = %s::uuid",
            (max_members, str(business_id)),
            fetch=False,
        )

    def create_platform_membership(self, email):
        """Create an owner membership for a user on the platform account.

        The platform configure endpoint creates roles but NOT memberships.
        CMS admin endpoints require active platform membership via
        PlatformContextMixin, so we must create it explicitly.

        Returns the membership UUID string or None if user/platform not found.
        """
        # Get user ID
        user_id = self.get_user_id(email)
        if not user_id:
            return None

        # Get platform account ID
        row = self.execute_one(
            "SELECT id FROM platform_account WHERE singleton_key = 1"
        )
        if not row:
            return None
        platform_id = str(row[0])

        # Get the owner role (level=0, highest privilege)
        row = self.execute_one(
            """
            SELECT id FROM rbac_role
            WHERE account_type = 'platform' AND account_id = %s
            ORDER BY level ASC LIMIT 1
            """,
            (platform_id,),
        )
        if not row:
            return None
        role_id = str(row[0])

        # Check if membership already exists for THIS user
        existing = self.execute_one(
            """
            SELECT id FROM rbac_membership
            WHERE user_id = %s AND account_type = 'platform'
                AND account_id = %s AND is_deleted = FALSE
            """,
            (user_id, platform_id),
        )
        if existing:
            return str(existing[0])

        # Soft-delete any existing owner membership to avoid unique constraint
        self.execute(
            """
            UPDATE rbac_membership SET is_deleted = TRUE, deleted_at = NOW()
            WHERE account_type = 'platform' AND account_id = %s
                AND is_owner = TRUE AND is_deleted = FALSE
            """,
            (platform_id,),
            fetch=False,
        )

        # Create membership (include all NOT NULL columns)
        membership_id = str(uuid.uuid4())
        self.execute(
            """
            INSERT INTO rbac_membership
                (id, user_id, account_type, account_id, role_id,
                 is_owner, status, joined_at, status_reason,
                 created_at, updated_at, is_deleted)
            VALUES (%s, %s, 'platform', %s, %s,
                    TRUE, 'active', NOW(), '',
                    NOW(), NOW(), FALSE)
            """,
            (membership_id, user_id, platform_id, role_id),
            fetch=False,
        )
        return membership_id


# =============================================================================
# REDIS HELPER — Direct Redis queries for cache/blacklist verification
# =============================================================================


class RedisHelper:
    """Direct Redis access for verifying cache state, JTI blacklist, etc."""

    def __init__(self):
        # Cache DB is 1 (from local_docker.py LOCATION)
        self.cache_client = redis_lib.Redis(host="localhost", port=6379, db=1)
        # Broker DB is 0 (from base.py CELERY_BROKER_URL)
        self.broker_client = redis_lib.Redis(host="localhost", port=6379, db=0)

    def get_key(self, key):
        """Get value by exact key from cache DB."""
        val = self.cache_client.get(key)
        return val.decode() if val else None

    def key_exists(self, key):
        """Check if key exists in cache DB."""
        return self.cache_client.exists(key) > 0

    def scan_keys(self, pattern):
        """Scan for keys matching pattern in cache DB."""
        return [k.decode() for k in self.cache_client.scan_iter(pattern)]

    def get_ttl(self, key):
        """Get TTL in seconds from cache DB. Returns -1 if no TTL, -2 if missing."""
        return self.cache_client.ttl(key)

    def flush_cache(self):
        """Flush cache DB (db 1)."""
        self.cache_client.flushdb()

    def get_broker_key(self, key):
        """Get value from broker DB (db 0)."""
        val = self.broker_client.get(key)
        return val.decode() if val else None

    def scan_broker_keys(self, pattern):
        """Scan for keys matching pattern in broker DB."""
        return [k.decode() for k in self.broker_client.scan_iter(pattern)]


# =============================================================================
# SESSION-SCOPED FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def api():
    """Session-scoped HTTP client."""
    helper = APIHelper()
    # Quick connectivity check
    try:
        helper.session.get(f"{helper.base_url}/")
        # Any response (even 404) means server is up
    except requests.ConnectionError:
        pytest.skip("Django server not running. Start with: make dev")
    return helper


@pytest.fixture(scope="session")
def state():
    """Session-scoped shared test state."""
    return TestState()


@pytest.fixture(scope="session")
def db_helper():
    """Session-scoped PostgreSQL direct access.

    Named 'db_helper' (not 'db') to avoid collision with pytest-django's
    built-in 'db' fixture, which triggers test reordering.
    """
    helper = DBHelper()
    # Quick connectivity check
    try:
        helper.execute("SELECT 1")
    except psycopg2.OperationalError:
        pytest.skip("PostgreSQL not available. Start with: make dev-up")
    return helper


@pytest.fixture(scope="session")
def redis_helper():
    """Session-scoped Redis direct access."""
    helper = RedisHelper()
    try:
        helper.cache_client.ping()
    except redis_lib.ConnectionError:
        pytest.skip("Redis not available. Start with: make dev-up")
    return helper


# =============================================================================
# UTILITY FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def random_uuid():
    """Generate a random UUID (for 404 tests)."""

    def _gen():
        return str(uuid.uuid4())

    return _gen


@pytest.fixture(scope="session")
def assert_error():
    """Helper to assert standard error response format."""

    def _check(response, expected_code, expected_status=None):
        if expected_status:
            assert response.status_code == expected_status, (
                f"Expected {expected_status}, got {response.status_code}: "
                f"{response.text[:500]}"
            )
        data = response.json()
        assert "error" in data, f"Missing 'error' key in response: {data}"
        assert data["error"]["code"] == expected_code, (
            f"Expected error code '{expected_code}', "
            f"got '{data['error']['code']}': {data['error']['message']}"
        )

    return _check


@pytest.fixture(scope="session", autouse=True)
def _cleanup_previous_run(db_helper):
    """Clean up test data from previous runs for idempotent test execution.

    Runs once at session start. Deletes known test users and related data
    so registration tests always start fresh.
    """
    test_emails = [
        "alice@test.com",
        "bob@test.com",
        "carol@test.com",
        "nobody@test.com",
        "deactivate@test.com",
    ]
    for email in test_emails:
        try:
            # Delete in order: auth tokens → device sessions → refresh tokens → user
            db_helper.execute(
                """
                DELETE FROM auth_verification_tokens WHERE email = %s
                """,
                (email,),
                fetch=False,
            )
            db_helper.execute(
                """
                DELETE FROM auth_password_reset_tokens
                WHERE user_id IN (SELECT id FROM users WHERE email = %s)
                """,
                (email,),
                fetch=False,
            )
            db_helper.execute(
                """
                DELETE FROM auth_device_sessions
                WHERE user_id IN (SELECT id FROM users WHERE email = %s)
                """,
                (email,),
                fetch=False,
            )
            db_helper.execute(
                """
                DELETE FROM auth_refresh_tokens
                WHERE user_id IN (SELECT id FROM users WHERE email = %s)
                """,
                (email,),
                fetch=False,
            )
            # Delete memberships
            db_helper.execute(
                """
                DELETE FROM rbac_membership
                WHERE user_id IN (SELECT id FROM users WHERE email = %s)
                """,
                (email,),
                fetch=False,
            )
            # Delete user
            db_helper.execute(
                "DELETE FROM users WHERE email = %s",
                (email,),
                fetch=False,
            )
        except Exception:
            pass  # Table may not exist or FK constraints may prevent deletion
