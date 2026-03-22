"""
JTI Blacklist
=============
Redis-based JWT ID blacklist for immediate access token revocation.

Why Redis?
    - Access tokens are validated on EVERY request
    - Database lookup would be too slow
    - Redis TTL auto-expires entries (no cleanup needed)

When to Blacklist:
    - logout_all (revoke all user sessions)
    - Password change (security best practice)
    - Account deactivation
    - Security events (suspicious activity)
    - Session revocation

Usage:
    from apps.auth.blacklist import JTIBlacklist

    # Blacklist a JTI
    JTIBlacklist.blacklist(jti)

    # Check if blacklisted
    if JTIBlacklist.is_blacklisted(jti):
        raise TokenInvalid()

    # Blacklist all user's tokens
    JTIBlacklist.blacklist_user_tokens(user_id)
"""

from django.conf import settings
from django.utils import timezone

from apps.core.observability import get_logger

logger = get_logger(__name__)


class JTIBlacklist:
    """
    Redis-based JTI blacklist for immediate access token revocation.

    Uses Redis SETEX for automatic TTL-based cleanup.
    """

    _redis = None
    KEY_PREFIX = "jti_blacklist:"

    @classmethod
    def _get_redis(cls):
        """Get Redis connection (lazy initialization)."""
        if cls._redis is None:
            try:
                import redis

                redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
                cls._redis = redis.from_url(redis_url)
                # Test connection
                cls._redis.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using fallback cache.")
                cls._redis = "fallback"

        return cls._redis

    @classmethod
    def blacklist(cls, jti: str, ttl_seconds: int = None) -> None:
        """
        Add JTI to blacklist.

        Args:
            jti: The JWT ID to blacklist
            ttl_seconds: Time to live. Defaults to ACCESS_TOKEN_LIFETIME.
                        After this time, the token would be expired anyway.
        """
        if ttl_seconds is None:
            jwt_auth = getattr(settings, "JWT_AUTH", {})
            ttl_seconds = jwt_auth.get("ACCESS_TOKEN_LIFETIME", 900)

        redis_client = cls._get_redis()

        if redis_client == "fallback":
            # Fallback to Django cache
            from django.core.cache import cache

            cache_key = f"{cls.KEY_PREFIX}{jti}"
            cache.set(cache_key, "1", ttl_seconds)
            return

        try:
            key = f"{cls.KEY_PREFIX}{jti}"
            redis_client.setex(key, ttl_seconds, "1")
        except Exception as e:
            logger.error(f"Failed to blacklist JTI: {e}")
            # Fallback to Django cache
            from django.core.cache import cache

            cache_key = f"{cls.KEY_PREFIX}{jti}"
            cache.set(cache_key, "1", ttl_seconds)

    @classmethod
    def is_blacklisted(cls, jti: str) -> bool:
        """
        Check if JTI is blacklisted.

        Security: Fail-closed — if Redis is unavailable, raises ServiceUnavailable
        to deny access rather than silently accepting potentially revoked tokens.

        Args:
            jti: The JWT ID to check

        Returns:
            True if blacklisted, False otherwise

        Raises:
            ServiceUnavailable: If Redis is unavailable (fail-closed)
        """
        from apps.core.exceptions import ServiceUnavailable

        redis_client = cls._get_redis()

        if redis_client == "fallback":
            # Fail closed — deny access when blacklist cannot be checked
            logger.error("auth.blacklist.redis_unavailable", extra={"jti": jti})
            raise ServiceUnavailable(
                message="Security service temporarily unavailable",
                service="blacklist",
            )

        try:
            key = f"{cls.KEY_PREFIX}{jti}"
            return redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check JTI blacklist: {e}")
            # Fail closed — deny access when blacklist cannot be checked
            raise ServiceUnavailable(
                message="Security service temporarily unavailable",
                service="blacklist",
            )

    @classmethod
    def blacklist_user_tokens(cls, user_id: int) -> int:
        """
        Blacklist all active JTIs for a user.

        Called on:
        - logout_all
        - password change
        - account deactivation
        - security events

        Args:
            user_id: User's ID

        Returns:
            Number of tokens blacklisted
        """
        from apps.auth.models import RefreshToken

        # Get all active refresh tokens (each has a JTI)
        active_tokens = RefreshToken.objects.filter(
            user_id=user_id, is_revoked=False, expires_at__gt=timezone.now()
        ).values_list("jti", flat=True)

        count = 0
        for jti in active_tokens:
            cls.blacklist(str(jti))
            count += 1

        logger.info(
            "auth.blacklist.user_tokens",
            extra={"user_id": user_id, "tokens_blacklisted": count},
        )

        return count

    @classmethod
    def remove(cls, jti: str) -> bool:
        """
        Remove JTI from blacklist (rarely needed).

        Args:
            jti: The JWT ID to remove

        Returns:
            True if removed, False if not found
        """
        redis_client = cls._get_redis()

        if redis_client == "fallback":
            from django.core.cache import cache

            cache_key = f"{cls.KEY_PREFIX}{jti}"
            cache.delete(cache_key)
            return True

        try:
            key = f"{cls.KEY_PREFIX}{jti}"
            return redis_client.delete(key) > 0
        except Exception as e:
            logger.error(f"Failed to remove JTI from blacklist: {e}")
            return False
