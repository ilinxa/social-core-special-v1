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

    # -- Feature Gate Integration Helpers --

    def get_failed_login_attempts(self, email):
        """Get failed_login_attempts counter for a user."""
        row = self.execute_one(
            "SELECT failed_login_attempts FROM users WHERE email = %s", (email,)
        )
        return row[0] if row else 0

    def get_locked_until(self, email):
        """Get locked_until timestamp for a user. Returns datetime or None."""
        row = self.execute_one(
            "SELECT locked_until FROM users WHERE email = %s", (email,)
        )
        return row[0] if row else None

    def unlock_account(self, email):
        """Clear account lockout (reset counter + locked_until)."""
        self.execute(
            "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE email = %s",
            (email,),
            fetch=False,
        )

    def set_business_visibility(self, slug, is_public):
        """Set business profile is_public flag for follow approval testing."""
        self.execute(
            """UPDATE business_profile SET is_public = %s
               WHERE business_id = (SELECT id FROM business_account WHERE slug = %s)""",
            (is_public, slug),
            fetch=False,
        )


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
    """Clean up ALL test data from previous runs for idempotent test execution.

    Runs once at session start. Uses fresh connections per statement
    to avoid error-state propagation. All @test.com users and data removed.
    """
    import psycopg2 as _pg2

    def _exec(sql, params=None):
        """Execute SQL with a fresh connection. Errors are silently ignored."""
        try:
            c = _pg2.connect(**DBHelper.PG_CONFIG)
            c.autocommit = True
            with c.cursor() as cur:
                cur.execute(sql, params)
            c.close()
        except Exception:
            pass

    # ── Collect ALL test user IDs ───────────────────────────────────────
    try:
        rows = db_helper.execute(
            "SELECT id FROM users WHERE email LIKE '%@test.com'"
        )
        if not rows:
            return
        test_user_ids = tuple(str(r[0]) for r in rows)
    except Exception:
        return

    ph = ",".join(["%s"] * len(test_user_ids))

    # ── Collect ALL test business IDs ───────────────────────────────────
    try:
        rows = db_helper.execute(
            f"SELECT id FROM business_account WHERE created_by_id IN ({ph})",
            test_user_ids,
        )
        test_biz_ids = tuple(str(r[0]) for r in rows) if rows else ()
    except Exception:
        test_biz_ids = ()

    biz_ph = ",".join(["%s"] * len(test_biz_ids)) if test_biz_ids else None

    # ── 1. CMS (deepest children first) ─────────────────────────────────
    if test_biz_ids:
        _exec(
            f"""DELETE FROM cms_section_block_placement
                WHERE section_placement_id IN (
                    SELECT psp.id FROM cms_page_section_placement psp
                    JOIN cms_page p ON psp.page_id = p.id
                    JOIN cms_site s ON p.site_id = s.id
                    WHERE s.account_id IN ({biz_ph}))""",
            test_biz_ids,
        )
        _exec(
            f"""DELETE FROM cms_page_section_placement
                WHERE page_id IN (
                    SELECT p.id FROM cms_page p
                    JOIN cms_site s ON p.site_id = s.id
                    WHERE s.account_id IN ({biz_ph}))""",
            test_biz_ids,
        )
        _exec(
            f"""DELETE FROM cms_content_version
                WHERE page_id IN (
                    SELECT p.id FROM cms_page p
                    JOIN cms_site s ON p.site_id = s.id
                    WHERE s.account_id IN ({biz_ph}))""",
            test_biz_ids,
        )
        _exec(
            f"""DELETE FROM cms_media_usage
                WHERE media_file_id IN (
                    SELECT id FROM cms_media_file
                    WHERE site_id IN (
                        SELECT id FROM cms_site WHERE account_id IN ({biz_ph})))""",
            test_biz_ids,
        )
        _exec(
            f"""DELETE FROM cms_media_file
                WHERE site_id IN (
                    SELECT id FROM cms_site WHERE account_id IN ({biz_ph}))""",
            test_biz_ids,
        )
        _exec(
            f"""DELETE FROM cms_media_folder
                WHERE site_id IN (
                    SELECT id FROM cms_site WHERE account_id IN ({biz_ph}))""",
            test_biz_ids,
        )
        _exec(
            f"""DELETE FROM cms_api_key
                WHERE site_id IN (
                    SELECT id FROM cms_site WHERE account_id IN ({biz_ph}))""",
            test_biz_ids,
        )
        _exec(
            f"""DELETE FROM cms_page
                WHERE site_id IN (
                    SELECT id FROM cms_site WHERE account_id IN ({biz_ph}))""",
            test_biz_ids,
        )
        _exec(
            f"DELETE FROM cms_site WHERE account_id IN ({biz_ph})",
            test_biz_ids,
        )

    # CMS: delete ALL sites (all are test data — platform-owned)
    _exec("DELETE FROM cms_section_block_placement")
    _exec("DELETE FROM cms_page_section_placement")
    _exec("DELETE FROM cms_content_version")
    _exec("DELETE FROM cms_media_usage")
    _exec("DELETE FROM cms_media_file")
    _exec("DELETE FROM cms_media_folder")
    _exec("DELETE FROM cms_api_key")
    _exec("UPDATE cms_site SET homepage_id = NULL")
    _exec("DELETE FROM cms_page")
    _exec("DELETE FROM cms_site")

    # CMS templates created by test users
    _exec(f"DELETE FROM cms_section_template_activation WHERE activated_by_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM cms_block_template_activation WHERE activated_by_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM cms_section_template WHERE created_by_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM cms_block_template WHERE created_by_id IN ({ph})", test_user_ids)

    # ── 2. Forms ────────────────────────────────────────────────────────
    for idx_table in [
        "form_boolean_field_index", "form_integer_field_index",
        "form_text_field_index", "form_date_field_index",
        "form_datetime_field_index", "form_decimal_field_index",
    ]:
        _exec(
            f"""DELETE FROM {idx_table} WHERE response_id IN (
                    SELECT id FROM form_response WHERE submitted_by_id IN ({ph}))""",
            test_user_ids,
        )
    _exec(
        f"""DELETE FROM transaction_form_mapping WHERE form_response_id IN (
                SELECT id FROM form_response WHERE submitted_by_id IN ({ph}))""",
        test_user_ids,
    )
    _exec(f"DELETE FROM form_response WHERE submitted_by_id IN ({ph})", test_user_ids)
    _exec(
        f"""DELETE FROM form_field WHERE template_id IN (
                SELECT id FROM form_template WHERE created_by_id IN ({ph}))""",
        test_user_ids,
    )
    _exec(f"DELETE FROM form_template WHERE created_by_id IN ({ph})", test_user_ids)

    # ── 3. Transactions ─────────────────────────────────────────────────
    _exec(
        f"""DELETE FROM transaction_log WHERE transaction_id IN (
                SELECT id FROM transaction_transaction WHERE created_by_id IN ({ph}))""",
        test_user_ids,
    )
    _exec(f"DELETE FROM transaction_transaction WHERE created_by_id IN ({ph})", test_user_ids)

    # ── 4. Network ──────────────────────────────────────────────────────
    # network_follow.follower_id is polymorphic (user UUID or entity UUID)
    _exec(f"DELETE FROM network_follow WHERE follower_id IN ({ph})", test_user_ids)
    _exec(f"UPDATE network_follow SET removed_by_id = NULL WHERE removed_by_id IN ({ph})", test_user_ids)
    _exec(
        f"DELETE FROM network_connection WHERE user_a_id IN ({ph}) OR user_b_id IN ({ph})",
        test_user_ids + test_user_ids,
    )
    _exec(
        f"UPDATE network_connection SET disconnected_by_id = NULL WHERE disconnected_by_id IN ({ph})",
        test_user_ids,
    )
    _exec(
        f"UPDATE network_connection SET initiated_by_id = NULL WHERE initiated_by_id IN ({ph})",
        test_user_ids,
    )

    # ── 5. Notifications ────────────────────────────────────────────────
    _exec(f"DELETE FROM notification_logs WHERE user_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM notification_preferences WHERE user_id IN ({ph})", test_user_ids)

    # ── 6. Chat ─────────────────────────────────────────────────────────
    _exec(f"""DELETE FROM chat_message_reaction WHERE message_id IN (
                SELECT id FROM chat_message WHERE sender_id IN ({ph}))""", test_user_ids)
    _exec(f"""DELETE FROM chat_message_attachment WHERE message_id IN (
                SELECT id FROM chat_message WHERE sender_id IN ({ph}))""", test_user_ids)
    _exec(f"DELETE FROM chat_message WHERE sender_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM chat_conversation_participant WHERE user_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM chat_block WHERE blocker_id IN ({ph})", test_user_ids)

    # ── 7. Audit logs ───────────────────────────────────────────────────
    _exec(f"DELETE FROM audit_log WHERE actor_id IN ({ph})", test_user_ids)

    # ── 8. RBAC — memberships then roles ────────────────────────────────
    _exec(f"UPDATE rbac_membership SET status_changed_by_id = NULL WHERE status_changed_by_id IN ({ph})", test_user_ids)
    _exec(f"UPDATE rbac_membership SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})", test_user_ids)
    _exec(f"UPDATE rbac_membership SET created_by_id = NULL WHERE created_by_id IN ({ph})", test_user_ids)
    _exec(f"UPDATE rbac_membership SET updated_by_id = NULL WHERE updated_by_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM rbac_membership WHERE user_id IN ({ph})", test_user_ids)
    if test_biz_ids:
        _exec(
            f"""DELETE FROM rbac_role_permission WHERE role_id IN (
                    SELECT id FROM rbac_role
                    WHERE account_type = 'business' AND account_id IN ({biz_ph}))""",
            test_biz_ids,
        )
        _exec(
            f"DELETE FROM rbac_role WHERE account_type = 'business' AND account_id IN ({biz_ph})",
            test_biz_ids,
        )
    # Delete test-created platform roles by name (system roles are:
    # Platform Owner, Platform Admin, Global Moderator, Base Member)
    _test_role_names = ("Platform Moderator", "Temp Role")
    _exec(
        """DELETE FROM rbac_role_permission WHERE role_id IN (
                SELECT id FROM rbac_role
                WHERE account_type = 'platform' AND name IN %s)""",
        (_test_role_names,),
    )
    _exec(
        "DELETE FROM rbac_role WHERE account_type = 'platform' AND name IN %s",
        (_test_role_names,),
    )
    # NULL out test user refs on platform roles (they survive across runs)
    _exec(f"UPDATE rbac_role SET created_by_id = NULL WHERE created_by_id IN ({ph})", test_user_ids)
    _exec(f"UPDATE rbac_role SET updated_by_id = NULL WHERE updated_by_id IN ({ph})", test_user_ids)
    _exec(f"UPDATE rbac_role SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})", test_user_ids)
    # NULL refs from platform_account/profile (singleton, survives runs)
    _exec(f"UPDATE platform_account SET created_by_id = NULL WHERE created_by_id IN ({ph})", test_user_ids)
    _exec(f"UPDATE platform_account SET updated_by_id = NULL WHERE updated_by_id IN ({ph})", test_user_ids)
    _exec(f"UPDATE platform_profile SET updated_by_id = NULL WHERE updated_by_id IN ({ph})", test_user_ids)

    # ── 9. Business data ────────────────────────────────────────────────
    if test_biz_ids:
        _exec(f"DELETE FROM business_slug_history WHERE business_id IN ({biz_ph})", test_biz_ids)
        _exec(f"UPDATE business_profile SET updated_by_id = NULL WHERE updated_by_id IN ({ph})", test_user_ids)
        _exec(f"DELETE FROM business_profile WHERE business_id IN ({biz_ph})", test_biz_ids)
        _exec(f"UPDATE business_account SET updated_by_id = NULL WHERE updated_by_id IN ({ph})", test_user_ids)
        _exec(f"UPDATE business_account SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})", test_user_ids)
        _exec(f"UPDATE business_account SET verified_by_id = NULL WHERE verified_by_id IN ({ph})", test_user_ids)
        _exec(f"DELETE FROM business_account WHERE id IN ({biz_ph})", test_biz_ids)

    # ── 10. User profiles ───────────────────────────────────────────────
    _exec(f"DELETE FROM user_profiles WHERE user_id IN ({ph})", test_user_ids)

    # ── 11. Auth tokens ─────────────────────────────────────────────────
    _exec(
        f"""DELETE FROM auth_verification_tokens
            WHERE user_id IN ({ph}) OR email IN (SELECT email FROM users WHERE id IN ({ph}))""",
        test_user_ids + test_user_ids,
    )
    _exec(f"DELETE FROM auth_password_reset_tokens WHERE user_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM auth_governance_otp WHERE user_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM auth_oauth_connections WHERE user_id IN ({ph})", test_user_ids)
    # Device sessions → refresh tokens (FK order)
    _exec(f"DELETE FROM auth_device_sessions WHERE user_id IN ({ph})", test_user_ids)
    _exec(f"UPDATE auth_refresh_tokens SET replaced_by_id = NULL WHERE user_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM auth_refresh_tokens WHERE user_id IN ({ph})", test_user_ids)

    # ── 12. NULL out ALL remaining FK references to test users ─────────
    # This catches any created_by/updated_by/deleted_by/etc. columns
    # that still reference test users across ALL tables.
    _null_stmts = [
        "UPDATE form_template SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE form_template SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE form_template SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE form_response SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE form_response SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE form_response SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE form_response SET processed_by_id = NULL WHERE processed_by_id IN ({ph})",
        "UPDATE transaction_transaction SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE transaction_transaction SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE transaction_transaction SET resolved_by_id = NULL WHERE resolved_by_id IN ({ph})",
        "UPDATE transaction_transaction SET info_requested_by_id = NULL WHERE info_requested_by_id IN ({ph})",
        "UPDATE transaction_transaction SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE transaction_form_mapping SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE transaction_form_mapping SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE transaction_form_mapping SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE business_account SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE business_account SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE business_account SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE business_account SET verified_by_id = NULL WHERE verified_by_id IN ({ph})",
        "UPDATE business_profile SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE cms_site SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE cms_site SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE cms_site SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE cms_page SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE cms_page SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE cms_page SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE cms_api_key SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE cms_api_key SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE cms_api_key SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE cms_media_file SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE cms_media_file SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE cms_media_file SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE cms_media_folder SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE cms_media_folder SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE cms_media_folder SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE cms_content_version SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE cms_section_template SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE cms_section_template SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE cms_section_template SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE cms_block_template SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE cms_block_template SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE cms_block_template SET deleted_by_id = NULL WHERE deleted_by_id IN ({ph})",
        "UPDATE cms_section_block_placement SET created_by_id = NULL WHERE created_by_id IN ({ph})",
        "UPDATE cms_section_block_placement SET updated_by_id = NULL WHERE updated_by_id IN ({ph})",
        "UPDATE chat_message_attachment SET uploaded_by_id = NULL WHERE uploaded_by_id IN ({ph})",
        "UPDATE chat_conversation_participant SET added_by_id = NULL WHERE added_by_id IN ({ph})",
        "UPDATE chat_conversation_participant SET removed_by_id = NULL WHERE removed_by_id IN ({ph})",
        "UPDATE django_admin_log SET user_id = NULL WHERE user_id IN ({ph})",
    ]
    for stmt in _null_stmts:
        _exec(stmt.format(ph=ph), test_user_ids)

    # ── 13. Users ───────────────────────────────────────────────────────
    _exec(f"UPDATE users SET referred_by_id = NULL WHERE referred_by_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM users_groups WHERE user_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM users_user_permissions WHERE user_id IN ({ph})", test_user_ids)
    _exec(f"DELETE FROM users WHERE id IN ({ph})", test_user_ids)
