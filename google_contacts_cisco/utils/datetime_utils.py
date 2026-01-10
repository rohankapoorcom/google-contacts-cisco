"""Datetime utilities for timezone handling and formatting.

This module provides utilities for converting UTC timestamps to configured
timezones and formatting them for display.
"""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo


def format_timestamp_for_display(
    dt: Optional[datetime],
    target_timezone: str = "UTC",
) -> Optional[str]:
    """Format a datetime for display in the target timezone.

    Converts a UTC datetime to the target timezone and returns an ISO 8601
    formatted string with timezone information. This allows the frontend to
    properly display timestamps in the user's local timezone.

    Args:
        dt: The datetime to format (should be timezone-aware UTC)
        target_timezone: IANA timezone name (e.g., "America/New_York", "Europe/London")

    Returns:
        ISO 8601 formatted string with timezone (e.g., "2026-01-09T15:30:00-05:00")
        or None if dt is None

    Example:
        >>> dt = datetime(2026, 1, 9, 20, 30, 0, tzinfo=timezone.utc)
        >>> format_timestamp_for_display(dt, "America/New_York")
        "2026-01-09T15:30:00-05:00"
    """
    if dt is None:
        return None

    # Ensure the datetime is timezone-aware (UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Convert to target timezone
    try:
        from zoneinfo import ZoneInfoNotFoundError

        target_tz = ZoneInfo(target_timezone)
        dt_local = dt.astimezone(target_tz)
        return dt_local.isoformat()
    except (ZoneInfoNotFoundError, OSError, ValueError, KeyError):
        # If conversion fails (invalid timezone, missing tzdata, etc),
        # return UTC timestamp
        return dt.isoformat()


def get_current_time_utc() -> datetime:
    """Get current time in UTC.

    Returns:
        Current datetime in UTC with timezone information
    """
    return datetime.now(timezone.utc)
