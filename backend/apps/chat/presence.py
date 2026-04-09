"""
Chat Presence Manager
=====================
Redis-based online presence tracking.

Fail-open: Redis unavailable → everyone shows offline (no exception).
This is the inverse of JTIBlacklist which fail-closes.

Pattern follows JTIBlacklist._get_redis() from apps/auth/blacklist.py.
"""

from django.conf import settings

from apps.core.feature_config import feature_config
from apps.core.observability import get_logger

logger = get_logger(__name__)


class PresenceManager:
    """
    Redis-based presence tracking with TTL auto-expiry.

    Keys: chat:presence:{user_id} with TTL=30s
    Heartbeat refreshes TTL every 20s (driven by consumer).
    """

    _redis = None
    KEY_PREFIX = "chat:presence:"

    @classmethod
    def _get_redis(cls):
        """Get Redis connection (lazy initialization)."""
        if cls._redis is None:
            try:
                import redis

                redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
                cls._redis = redis.from_url(redis_url)
                cls._redis.ping()
            except Exception as e:
                logger.warning(
                    "chat.presence.redis_unavailable",
                    extra={"error": str(e)},
                )
                cls._redis = "unavailable"

        return cls._redis

    @classmethod
    def set_online(cls, user_id, ttl: int | None = None) -> None:
        """Mark user as online with TTL-based auto-expiry."""
        if ttl is None:
            from apps.chat.constants import WS_PRESENCE_TTL_SECONDS

            ttl = feature_config.get_value(
                "chat.presence.ttl_seconds", WS_PRESENCE_TTL_SECONDS
            )

        redis_client = cls._get_redis()
        if redis_client == "unavailable":
            return  # Fail-open

        try:
            key = f"{cls.KEY_PREFIX}{user_id}"
            redis_client.setex(key, ttl, "1")
        except Exception as e:
            logger.warning(
                "chat.presence.set_online_failed",
                extra={"user_id": str(user_id), "error": str(e)},
            )

    @classmethod
    def set_offline(cls, user_id) -> None:
        """Remove user presence key."""
        redis_client = cls._get_redis()
        if redis_client == "unavailable":
            return  # Fail-open

        try:
            key = f"{cls.KEY_PREFIX}{user_id}"
            redis_client.delete(key)
        except Exception as e:
            logger.warning(
                "chat.presence.set_offline_failed",
                extra={"user_id": str(user_id), "error": str(e)},
            )

    @classmethod
    def is_online(cls, user_id) -> bool:
        """Check if a user is online."""
        redis_client = cls._get_redis()
        if redis_client == "unavailable":
            return False  # Fail-open: unknown → offline

        try:
            key = f"{cls.KEY_PREFIX}{user_id}"
            return redis_client.exists(key) > 0
        except Exception as e:
            logger.warning(
                "chat.presence.is_online_failed",
                extra={"user_id": str(user_id), "error": str(e)},
            )
            return False

    @classmethod
    def get_online_users(cls, user_ids: list) -> dict:
        """
        Batch check online status for multiple users.

        Returns: {user_id: bool} dict
        """
        if not user_ids:
            return {}

        redis_client = cls._get_redis()
        if redis_client == "unavailable":
            return {uid: False for uid in user_ids}

        try:
            pipe = redis_client.pipeline()
            for uid in user_ids:
                pipe.exists(f"{cls.KEY_PREFIX}{uid}")
            results = pipe.execute()
            return {uid: bool(result) for uid, result in zip(user_ids, results)}
        except Exception as e:
            logger.warning(
                "chat.presence.batch_check_failed",
                extra={"error": str(e)},
            )
            return {uid: False for uid in user_ids}

    @classmethod
    def reset(cls) -> None:
        """Reset Redis connection (for testing)."""
        cls._redis = None
