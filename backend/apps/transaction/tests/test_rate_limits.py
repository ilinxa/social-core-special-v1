import pytest
from uuid import uuid4

from apps.core.exceptions import RateLimitExceeded
from apps.transaction.rate_limits import check_rate_limit, RATE_LIMITS


@pytest.fixture
def locmem_cache(settings):
    """Override DummyCache with LocMemCache for rate limit tests."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "rate-limit-test",
        }
    }


@pytest.mark.django_db
class TestCheckRateLimit:

    def test_increments_counter(self, locmem_cache):
        user_id = str(uuid4())
        # Should not raise for first call
        check_rate_limit(user_id, "user_requests_per_hour", "per_hour")

    def test_raises_at_limit(self, locmem_cache):
        user_id = str(uuid4())
        limit = RATE_LIMITS["user_requests_per_hour"]

        for _ in range(limit):
            check_rate_limit(user_id, "user_requests_per_hour", "per_hour")

        with pytest.raises(RateLimitExceeded):
            check_rate_limit(user_id, "user_requests_per_hour", "per_hour")

    def test_different_users_independent(self, locmem_cache):
        user1 = str(uuid4())
        user2 = str(uuid4())
        limit = RATE_LIMITS["user_requests_per_hour"]

        for _ in range(limit):
            check_rate_limit(user1, "user_requests_per_hour", "per_hour")

        # User 2 should still be allowed
        check_rate_limit(user2, "user_requests_per_hour", "per_hour")

    def test_different_limit_types(self, locmem_cache):
        user_id = str(uuid4())
        limit = RATE_LIMITS["user_requests_per_hour"]

        for _ in range(limit):
            check_rate_limit(user_id, "user_requests_per_hour", "per_hour")

        # Different limit type should still work
        check_rate_limit(
            user_id, "business_invitations_per_day", "per_day",
        )

    def test_unknown_limit_type_uses_default(self, locmem_cache):
        user_id = str(uuid4())
        # Default limit is 100, should not raise
        check_rate_limit(user_id, "nonexistent_limit_type", "per_hour")
