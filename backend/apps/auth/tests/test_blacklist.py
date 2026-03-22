# apps/auth/tests/test_blacklist.py
"""
Tests for JTIBlacklist — Redis-based JWT ID blacklist with fail-closed behavior.

Covers:
    - TestJTIBlacklistWithFallback: Cache fallback path (blacklist write works, read fails closed)
    - TestJTIBlacklistWithMockedRedis: Redis path (setex, exists, delete, error handling)
    - TestBlacklistUserTokens: Bulk blacklisting of active user tokens
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.auth.blacklist import JTIBlacklist
from apps.auth.tests.factories import (
    ExpiredRefreshTokenFactory,
    RefreshTokenFactory,
    RevokedRefreshTokenFactory,
)
from apps.core.exceptions import ServiceUnavailable
from apps.users.tests.factories import UserFactory

# Use LocMemCache so cache.set/get actually stores values in tests.
CACHES_LOCMEM = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "blacklist-test",
    }
}


@pytest.fixture(autouse=True)
def reset_blacklist():
    """Reset JTIBlacklist._redis between every test to prevent state leakage."""
    JTIBlacklist._redis = None
    yield
    JTIBlacklist._redis = None


@pytest.fixture()
def clear_cache():
    """Clear the Django cache before and after each test that uses it."""
    cache.clear()
    yield
    cache.clear()


# =============================================================================
# FALLBACK (DJANGO CACHE) PATH
# =============================================================================


class TestJTIBlacklistWithFallback:
    """Tests for JTIBlacklist when Redis is unavailable.

    The blacklist WRITE path falls back to Django cache (best-effort).
    The blacklist READ path (is_blacklisted) fails closed — raises ServiceUnavailable.
    """

    @pytest.fixture(autouse=True)
    def _force_fallback(self, settings, clear_cache):
        """Force the fallback path by setting _redis to 'fallback' and using LocMemCache."""
        settings.CACHES = CACHES_LOCMEM
        JTIBlacklist._redis = "fallback"

    def test_blacklist_write_succeeds_via_cache_fallback(self):
        """blacklist() writes to Django cache when Redis is unavailable."""
        jti = str(uuid.uuid4())

        JTIBlacklist.blacklist(jti)

        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        assert cache.get(expected_key) is not None

    def test_is_blacklisted_raises_service_unavailable(self):
        """is_blacklisted() raises ServiceUnavailable when Redis is unavailable (fail-closed)."""
        jti = str(uuid.uuid4())

        with pytest.raises(ServiceUnavailable) as exc_info:
            JTIBlacklist.is_blacklisted(jti)

        assert exc_info.value.code == "service_unavailable"
        assert "blacklist" in exc_info.value.details.get("service", "")

    def test_remove_works_via_cache_fallback(self):
        """remove() deletes from Django cache when Redis is unavailable."""
        jti = str(uuid.uuid4())

        JTIBlacklist.blacklist(jti)
        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        assert cache.get(expected_key) is not None

        result = JTIBlacklist.remove(jti)

        assert result is True
        assert cache.get(expected_key) is None

    def test_blacklist_uses_correct_key_prefix(self):
        """Blacklisted entry is stored under KEY_PREFIX + jti in the cache."""
        jti = str(uuid.uuid4())

        JTIBlacklist.blacklist(jti)

        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        assert cache.get(expected_key) is not None

    def test_blacklist_with_custom_ttl(self):
        """blacklist() accepts a custom ttl_seconds argument without error."""
        jti = str(uuid.uuid4())

        # Should not raise; the TTL is passed to cache.set.
        JTIBlacklist.blacklist(jti, ttl_seconds=60)

        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        assert cache.get(expected_key) is not None


# =============================================================================
# MOCKED REDIS PATH
# =============================================================================


class TestJTIBlacklistWithMockedRedis:
    """Tests for JTIBlacklist when a mocked Redis client is available."""

    @pytest.fixture(autouse=True)
    def _setup_mock_redis(self):
        """Inject a MagicMock as the Redis client."""
        self.mock_redis = MagicMock()
        JTIBlacklist._redis = self.mock_redis

    def test_blacklist_calls_setex(self):
        """blacklist() calls redis.setex with the correct key, TTL, and value."""
        jti = str(uuid.uuid4())
        ttl = 600

        JTIBlacklist.blacklist(jti, ttl_seconds=ttl)

        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        self.mock_redis.setex.assert_called_once_with(expected_key, ttl, "1")

    def test_blacklist_uses_default_ttl_from_settings(self):
        """blacklist() uses JWT_AUTH.ACCESS_TOKEN_LIFETIME when ttl_seconds is None."""
        jti = str(uuid.uuid4())

        with override_settings(JWT_AUTH={"ACCESS_TOKEN_LIFETIME": 1200}):
            JTIBlacklist.blacklist(jti)

        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        self.mock_redis.setex.assert_called_once_with(expected_key, 1200, "1")

    def test_is_blacklisted_calls_exists(self):
        """is_blacklisted() calls redis.exists and interprets the result."""
        jti = str(uuid.uuid4())

        self.mock_redis.exists.return_value = 1
        assert JTIBlacklist.is_blacklisted(jti) is True

        self.mock_redis.exists.return_value = 0
        assert JTIBlacklist.is_blacklisted(jti) is False

        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        self.mock_redis.exists.assert_called_with(expected_key)

    def test_remove_calls_delete(self):
        """remove() calls redis.delete and returns True when key existed."""
        jti = str(uuid.uuid4())

        self.mock_redis.delete.return_value = 1
        result = JTIBlacklist.remove(jti)

        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        self.mock_redis.delete.assert_called_once_with(expected_key)
        assert result is True

    def test_redis_error_falls_back_to_cache_on_write(self, settings, clear_cache):
        """When Redis raises an exception, blacklist() falls back to Django cache."""
        settings.CACHES = CACHES_LOCMEM
        jti = str(uuid.uuid4())
        self.mock_redis.setex.side_effect = ConnectionError("Redis down")

        JTIBlacklist.blacklist(jti, ttl_seconds=300)

        # The value should be in Django cache via fallback.
        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        assert cache.get(expected_key) is not None

    def test_redis_error_raises_service_unavailable_on_read(self):
        """When Redis raises an exception, is_blacklisted() raises ServiceUnavailable."""
        jti = str(uuid.uuid4())
        self.mock_redis.exists.side_effect = ConnectionError("Redis down")

        with pytest.raises(ServiceUnavailable):
            JTIBlacklist.is_blacklisted(jti)


# =============================================================================
# BLACKLIST USER TOKENS
# =============================================================================


@pytest.mark.django_db
class TestBlacklistUserTokens:
    """Tests for JTIBlacklist.blacklist_user_tokens()."""

    @pytest.fixture(autouse=True)
    def _setup_mock_redis(self):
        """Use mocked Redis so both blacklist() and is_blacklisted() work."""
        self.mock_redis = MagicMock()
        self._store = {}
        JTIBlacklist._redis = self.mock_redis

        def mock_setex(key, ttl, value):
            self._store[key] = value

        def mock_exists(key):
            return 1 if key in self._store else 0

        self.mock_redis.setex.side_effect = mock_setex
        self.mock_redis.exists.side_effect = mock_exists

    def test_blacklists_all_active_tokens(self):
        """blacklist_user_tokens blacklists the JTI of every active token for the user."""
        user = UserFactory()
        t1 = RefreshTokenFactory(user=user)
        t2 = RefreshTokenFactory(user=user)

        count = JTIBlacklist.blacklist_user_tokens(user.id)

        assert count == 2
        assert JTIBlacklist.is_blacklisted(str(t1.jti)) is True
        assert JTIBlacklist.is_blacklisted(str(t2.jti)) is True

    def test_returns_correct_count(self):
        """blacklist_user_tokens returns the exact number of tokens it blacklisted."""
        user = UserFactory()
        RefreshTokenFactory(user=user)
        RefreshTokenFactory(user=user)
        RefreshTokenFactory(user=user)

        count = JTIBlacklist.blacklist_user_tokens(user.id)

        assert count == 3

    def test_skips_revoked_and_expired_tokens(self):
        """blacklist_user_tokens does not blacklist revoked or expired tokens."""
        user = UserFactory()
        active = RefreshTokenFactory(user=user)
        revoked = RevokedRefreshTokenFactory(user=user)
        expired = ExpiredRefreshTokenFactory(user=user)

        count = JTIBlacklist.blacklist_user_tokens(user.id)

        assert count == 1
        assert JTIBlacklist.is_blacklisted(str(active.jti)) is True
        assert JTIBlacklist.is_blacklisted(str(revoked.jti)) is False
        assert JTIBlacklist.is_blacklisted(str(expired.jti)) is False

    def test_does_not_affect_other_users(self):
        """blacklist_user_tokens only targets tokens belonging to the specified user."""
        user_a = UserFactory()
        user_b = UserFactory()
        token_a = RefreshTokenFactory(user=user_a)
        token_b = RefreshTokenFactory(user=user_b)

        count = JTIBlacklist.blacklist_user_tokens(user_a.id)

        assert count == 1
        assert JTIBlacklist.is_blacklisted(str(token_a.jti)) is True
        assert JTIBlacklist.is_blacklisted(str(token_b.jti)) is False
