from django.core.cache import cache

from apps.core.exceptions import RateLimitExceeded

RATE_LIMITS = {
    "user_requests_per_hour": 10,
    "user_connection_requests_per_day": 20,
    "business_invitations_per_day": 50,
    "resubmissions_per_day_per_target": 3,
}

RATE_TTLS = {
    "per_hour": 3600,
    "per_day": 86400,
}


def check_rate_limit(user_id, limit_type, ttl_type="per_hour"):
    cache_key = f"txn_rate:{limit_type}:{user_id}"
    current = cache.get(cache_key, 0)
    limit = RATE_LIMITS.get(limit_type, 100)

    if current >= limit:
        raise RateLimitExceeded(
            message=f"Rate limit exceeded for {limit_type}",
            retry_after=RATE_TTLS.get(ttl_type, 3600),
        )

    cache.set(cache_key, current + 1, timeout=RATE_TTLS.get(ttl_type, 3600))
