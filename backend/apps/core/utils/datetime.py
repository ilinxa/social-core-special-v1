"""
DateTime Utilities
==================
Timezone-aware datetime helpers for consistent date/time handling.

Design Principles:
    - All datetimes should be timezone-aware (USE_TZ=True)
    - Internal storage uses UTC
    - Conversion to user timezone happens at the presentation layer
    - Use these utilities instead of datetime.now() directly

Configuration:
    settings.TIME_ZONE: Default timezone (usually "UTC")
    settings.USE_TZ: Should be True

Usage:
    from apps.core.utils.datetime import utc_now, to_user_timezone

    # Get current UTC time
    now = utc_now()

    # Convert to user's timezone for display
    local_time = to_user_timezone(now, "America/New_York")
"""

from datetime import datetime, timedelta, date, timezone as _stdlib_tz
from typing import Optional, Union

from django.utils import timezone
import zoneinfo


# =============================================================================
# CURRENT TIME
# =============================================================================

def utc_now() -> datetime:
    """
    Get current datetime in UTC with timezone info.

    Always use this instead of datetime.now() or datetime.utcnow()
    to ensure timezone awareness.

    Returns:
        Current datetime in UTC

    Example:
        user.last_login = utc_now()
        user.save()
    """
    return timezone.now()


def today_utc() -> date:
    """
    Get current date in UTC.

    Returns:
        Current date in UTC
    """
    return utc_now().date()


# =============================================================================
# TIMEZONE CONVERSION
# =============================================================================

def to_user_timezone(
    dt: datetime,
    user_timezone: str = "UTC"
) -> datetime:
    """
    Convert a datetime to a specific timezone.

    Args:
        dt: Datetime to convert (should be timezone-aware)
        user_timezone: Target timezone name (e.g., "America/New_York")

    Returns:
        Datetime in the target timezone

    Example:
        utc_time = utc_now()
        local_time = to_user_timezone(utc_time, user.profile.timezone)
        # Display local_time to user
    """
    if dt.tzinfo is None:
        # Make naive datetime UTC-aware
        dt = timezone.make_aware(dt, _stdlib_tz.utc)

    try:
        tz = zoneinfo.ZoneInfo(user_timezone)
    except KeyError:
        # Invalid timezone - fall back to UTC
        tz = zoneinfo.ZoneInfo("UTC")

    return dt.astimezone(tz)


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC.

    Args:
        dt: Datetime to convert (can be naive or aware)

    Returns:
        Datetime in UTC

    Note:
        If dt is naive, it's assumed to be in the default timezone.
    """
    if dt.tzinfo is None:
        dt = timezone.make_aware(dt)
    return dt.astimezone(_stdlib_tz.utc)


# =============================================================================
# DATE RANGES
# =============================================================================

def start_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Get the start of day (00:00:00) for a datetime.

    Args:
        dt: Datetime (default: now)

    Returns:
        Datetime at 00:00:00 of the same day

    Example:
        # Get all orders from today
        today_start = start_of_day()
        Order.objects.filter(created_at__gte=today_start)
    """
    dt = dt or utc_now()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Get the end of day (23:59:59.999999) for a datetime.

    Args:
        dt: Datetime (default: now)

    Returns:
        Datetime at 23:59:59.999999 of the same day
    """
    dt = dt or utc_now()
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def start_of_week(dt: Optional[datetime] = None) -> datetime:
    """
    Get the start of the week (Monday 00:00:00) for a datetime.

    Args:
        dt: Datetime (default: now)

    Returns:
        Datetime at start of the week (Monday)
    """
    dt = dt or utc_now()
    days_since_monday = dt.weekday()
    monday = dt - timedelta(days=days_since_monday)
    return start_of_day(monday)


def start_of_month(dt: Optional[datetime] = None) -> datetime:
    """
    Get the start of the month for a datetime.

    Args:
        dt: Datetime (default: now)

    Returns:
        Datetime at day 1, 00:00:00 of the month
    """
    dt = dt or utc_now()
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# =============================================================================
# RELATIVE TIME
# =============================================================================

def days_ago(days: int) -> datetime:
    """
    Get datetime N days ago from now.

    Args:
        days: Number of days ago

    Returns:
        Datetime N days in the past

    Example:
        # Get users who logged in within last 7 days
        week_ago = days_ago(7)
        User.objects.filter(last_login__gte=week_ago)
    """
    return utc_now() - timedelta(days=days)


def hours_ago(hours: int) -> datetime:
    """
    Get datetime N hours ago from now.

    Args:
        hours: Number of hours ago

    Returns:
        Datetime N hours in the past
    """
    return utc_now() - timedelta(hours=hours)


def minutes_ago(minutes: int) -> datetime:
    """
    Get datetime N minutes ago from now.

    Args:
        minutes: Number of minutes ago

    Returns:
        Datetime N minutes in the past
    """
    return utc_now() - timedelta(minutes=minutes)


def days_from_now(days: int) -> datetime:
    """
    Get datetime N days from now.

    Args:
        days: Number of days in the future

    Returns:
        Datetime N days in the future

    Example:
        # Set token expiry to 7 days from now
        token.expires_at = days_from_now(7)
    """
    return utc_now() + timedelta(days=days)


# =============================================================================
# FORMATTING
# =============================================================================

def format_datetime(
    dt: datetime,
    format_string: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format a datetime to string.

    Args:
        dt: Datetime to format
        format_string: strftime format string

    Returns:
        Formatted datetime string

    Common formats:
        - ISO: "%Y-%m-%dT%H:%M:%SZ"
        - Date only: "%Y-%m-%d"
        - Human readable: "%B %d, %Y at %I:%M %p"
    """
    return dt.strftime(format_string)


def format_iso(dt: datetime) -> str:
    """
    Format datetime as ISO 8601 string.

    Args:
        dt: Datetime to format

    Returns:
        ISO 8601 formatted string (e.g., "2024-01-15T10:30:00Z")
    """
    # Convert to UTC and format
    utc_dt = to_utc(dt)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(iso_string: str) -> datetime:
    """
    Parse an ISO 8601 datetime string.

    Args:
        iso_string: ISO formatted string

    Returns:
        Timezone-aware datetime (UTC)

    Raises:
        ValueError: If string format is invalid
    """
    # Handle 'Z' suffix
    if iso_string.endswith("Z"):
        iso_string = iso_string[:-1] + "+00:00"
    return datetime.fromisoformat(iso_string)


# =============================================================================
# DURATION
# =============================================================================

def time_until(dt: datetime) -> timedelta:
    """
    Get time remaining until a future datetime.

    Args:
        dt: Future datetime

    Returns:
        Timedelta until that time (negative if in past)
    """
    return dt - utc_now()


def time_since(dt: datetime) -> timedelta:
    """
    Get time elapsed since a past datetime.

    Args:
        dt: Past datetime

    Returns:
        Timedelta since that time (negative if in future)
    """
    return utc_now() - dt


def is_past(dt: datetime) -> bool:
    """
    Check if a datetime is in the past.

    Args:
        dt: Datetime to check

    Returns:
        True if in past, False if now or future
    """
    return dt < utc_now()


def is_future(dt: datetime) -> bool:
    """
    Check if a datetime is in the future.

    Args:
        dt: Datetime to check

    Returns:
        True if in future, False if now or past
    """
    return dt > utc_now()
