"""
Metrics Tag Validation
======================
Validation for metric tags to prevent cardinality explosions.

This module enforces rules about which tags are allowed to prevent
Prometheus memory issues from unbounded cardinality.

CRITICAL: Never use high-cardinality tags like user_id, request_id, etc.
"""

# Tags that are allowed (bounded cardinality)
ALLOWED_TAGS = frozenset(
    [
        "method",  # HTTP method (GET, POST, etc.)
        "status_code",  # HTTP status code
        "outcome",  # success/failure/error
        "endpoint",  # API endpoint path
        "template",  # Email template name
        "task",  # Celery task name
        "queue",  # Queue name
        "source",  # Request source (web, mobile, api)
        "type",  # Generic type discriminator
        "status",  # Generic status
        "provider",  # OAuth provider
        "channel",  # Notification channel
    ]
)

# Tags that are forbidden (unbounded cardinality)
FORBIDDEN_TAGS = frozenset(
    [
        "user_id",
        "actor_id",
        "email",
        "request_id",
        "session_id",
        "ip_address",
        "ip",
        "token",
        "timestamp",
        "uuid",
        "id",
    ]
)


def validate_tags(tags: dict) -> None:
    """
    Validate metric tags against allowlist.

    Raises ValueError if forbidden tags are used.
    Only called in development/testing for performance reasons.

    Args:
        tags: Dictionary of tag key-value pairs

    Raises:
        ValueError: If a forbidden tag is used
    """
    if not tags:
        return

    for key in tags.keys():
        if key in FORBIDDEN_TAGS:
            raise ValueError(
                f"Forbidden metric tag: '{key}'. "
                f"High-cardinality tags cause Prometheus memory issues."
            )
