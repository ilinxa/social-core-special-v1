"""
Core Utilities
==============
Re-exports commonly used utility functions.

Usage:
    from apps.core.utils import utc_now, hash_password, encode_token

For full module access:
    from apps.core.utils.jwt import decode_token_unverified
    from apps.core.utils.datetime import start_of_month
"""

# JWT utilities
from apps.core.utils.jwt import (
    encode_token,
    decode_token,
    decode_token_unverified,
    get_token_expiry,
    is_token_expired,
)

# Password utilities
from apps.core.utils.password import (
    hash_password,
    verify_password,
    validate_password_strength,
    is_password_valid,
    get_password_requirements,
    generate_temporary_password,
)

# DateTime utilities
from apps.core.utils.datetime import (
    utc_now,
    today_utc,
    to_user_timezone,
    to_utc,
    start_of_day,
    end_of_day,
    start_of_week,
    start_of_month,
    days_ago,
    hours_ago,
    minutes_ago,
    days_from_now,
    format_datetime,
    format_iso,
    parse_iso,
    time_until,
    time_since,
    is_past,
    is_future,
)

# Request utilities
from apps.core.utils.request import get_client_ip, parse_user_agent

__all__ = [
    # JWT
    "encode_token",
    "decode_token",
    "decode_token_unverified",
    "get_token_expiry",
    "is_token_expired",
    # Password
    "hash_password",
    "verify_password",
    "validate_password_strength",
    "is_password_valid",
    "get_password_requirements",
    "generate_temporary_password",
    # DateTime
    "utc_now",
    "today_utc",
    "to_user_timezone",
    "to_utc",
    "start_of_day",
    "end_of_day",
    "start_of_week",
    "start_of_month",
    "days_ago",
    "hours_ago",
    "minutes_ago",
    "days_from_now",
    "format_datetime",
    "format_iso",
    "parse_iso",
    "time_until",
    "time_since",
    "is_past",
    "is_future",
    # Request
    "get_client_ip",
    "parse_user_agent",
]
