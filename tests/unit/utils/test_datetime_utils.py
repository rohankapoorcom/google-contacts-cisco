"""Test datetime utilities."""

from datetime import datetime, timezone

import pytest

from google_contacts_cisco.utils.datetime_utils import (
    format_timestamp_for_display,
    get_current_time_utc,
)


class TestFormatTimestampForDisplay:
    """Test format_timestamp_for_display function."""

    def test_format_utc_timestamp_to_utc(self):
        """Test formatting UTC timestamp to UTC."""
        dt = datetime(2026, 1, 9, 20, 30, 0, tzinfo=timezone.utc)
        result = format_timestamp_for_display(dt, "UTC")
        
        # Should return ISO format with UTC timezone
        assert result == "2026-01-09T20:30:00+00:00"

    def test_format_utc_timestamp_to_eastern(self):
        """Test formatting UTC timestamp to US/Eastern timezone."""
        dt = datetime(2026, 1, 9, 20, 30, 0, tzinfo=timezone.utc)
        result = format_timestamp_for_display(dt, "America/New_York")
        
        # Eastern time is UTC-5 in winter (EST)
        assert result == "2026-01-09T15:30:00-05:00"

    def test_format_utc_timestamp_to_london(self):
        """Test formatting UTC timestamp to Europe/London timezone."""
        dt = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = format_timestamp_for_display(dt, "Europe/London")
        
        # London time is UTC+1 in summer (BST)
        assert result == "2026-06-15T13:00:00+01:00"

    def test_format_none_timestamp(self):
        """Test formatting None returns None."""
        result = format_timestamp_for_display(None, "UTC")
        assert result is None

    def test_format_naive_datetime(self):
        """Test formatting naive datetime assumes UTC."""
        dt = datetime(2026, 1, 9, 20, 30, 0)  # No timezone
        result = format_timestamp_for_display(dt, "UTC")
        
        # Should still work and treat as UTC
        assert result == "2026-01-09T20:30:00+00:00"

    def test_format_with_invalid_timezone_fallback(self):
        """Test formatting with invalid timezone falls back to UTC."""
        dt = datetime(2026, 1, 9, 20, 30, 0, tzinfo=timezone.utc)
        result = format_timestamp_for_display(dt, "Invalid/Timezone")
        
        # Should fall back to UTC format
        assert result == "2026-01-09T20:30:00+00:00"

    def test_format_preserves_microseconds(self):
        """Test formatting preserves microseconds."""
        dt = datetime(2026, 1, 9, 20, 30, 0, 123456, tzinfo=timezone.utc)
        result = format_timestamp_for_display(dt, "UTC")
        
        # Should include microseconds
        assert "123456" in result


class TestGetCurrentTimeUtc:
    """Test get_current_time_utc function."""

    def test_returns_utc_datetime(self):
        """Test that function returns UTC datetime."""
        result = get_current_time_utc()
        
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_returns_current_time(self):
        """Test that function returns approximately current time."""
        before = datetime.now(timezone.utc)
        result = get_current_time_utc()
        after = datetime.now(timezone.utc)
        
        # Result should be between before and after
        assert before <= result <= after
