# apps/auth/tests/test_blacklist.py
"""
Tests for JTIBlacklist — Redis-based JWT ID blacklist with Django cache fallback.

Covers:
    - TestJTIBlacklistWithFallback: Cache fallback path (blacklist, check, remove, TTL)
    - TestJTIBlacklistWithMockedRedis: Redis path (setex, exists, delete, error fallback)
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
from apps.users.tests.factories import UserFactory


# Use LocMemCache so cache.set/get actually stores values in tests.
CACHES_LOCMEM = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'blacklist-test',
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
    """Tests for JTIBlacklist when Redis is unavailable and falls back to Django cache."""

    @pytest.fixture(autouse=True)
    def _force_fallback(self, settings, clear_cache):
        """Force the fallback path by setting _redis to 'fallback' and using LocMemCache."""
        settings.CACHES = CACHES_LOCMEM
        JTIBlacklist._redis = 'fallback'

    def test_blacklist_and_is_blacklisted(self):
        """Blacklisted JTI is detected by is_blacklisted."""
        jti = str(uuid.uuid4())

        JTIBlacklist.blacklist(jti)

        assert JTIBlacklist.is_blacklisted(jti) is True

    def test_is_blacklisted_returns_false_for_unknown_jti(self):
        """is_blacklisted returns False for a JTI that was never blacklisted."""
        jti = str(uuid.uuid4())

        assert JTIBlacklist.is_blacklisted(jti) is False

    def test_remove_deletes_from_blacklist(self):
        """remove() removes a JTI so is_blacklisted returns False afterwards."""
        jti = str(uuid.uuid4())

        JTIBlacklist.blacklist(jti)
        assert JTIBlacklist.is_blacklisted(jti) is True

        result = JTIBlacklist.remove(jti)

        assert result is True
        assert JTIBlacklist.is_blacklisted(jti) is False

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

        assert JTIBlacklist.is_blacklisted(jti) is True


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
        self.mock_redis.setex.assert_called_once_with(expected_key, ttl, '1')

    def test_blacklist_uses_default_ttl_from_settings(self):
        """blacklist() uses JWT_AUTH.ACCESS_TOKEN_LIFETIME when ttl_seconds is None."""
        jti = str(uuid.uuid4())

        with override_settings(JWT_AUTH={'ACCESS_TOKEN_LIFETIME': 1200}):
            JTIBlacklist.blacklist(jti)

        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        self.mock_redis.setex.assert_called_once_with(expected_key, 1200, '1')

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

    def test_redis_error_falls_back_to_cache(self, settings, clear_cache):
        """When Redis raises an exception, blacklist() falls back to Django cache."""
        settings.CACHES = CACHES_LOCMEM
        jti = str(uuid.uuid4())
        self.mock_redis.setex.side_effect = ConnectionError("Redis down")

        JTIBlacklist.blacklist(jti, ttl_seconds=300)

        # The value should be in Django cache via fallback.
        expected_key = f"{JTIBlacklist.KEY_PREFIX}{jti}"
        assert cache.get(expected_key) is not None


# =============================================================================
# BLACKLIST USER TOKENS
# =============================================================================


@pytest.mark.django_db
class TestBlacklistUserTokens:
    """Tests for JTIBlacklist.blacklist_user_tokens()."""

    @pytest.fixture(autouse=True)
    def _force_fallback(self, settings, clear_cache):
        """Force the fallback path so blacklist() uses Django cache."""
        settings.CACHES = CACHES_LOCMEM
        JTIBlacklist._redis = 'fallback'

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
