"""Test datetime utilities."""

from datetime import datetime, timezone

from google_contacts_cisco.utils.datetime_utils import (
    format_timestamp_for_display,
    get_current_time_utc,
)


class TestFormatTimestampForDisplay:
    """Test format_timestamp_for_display function."""

    def test_format_utc_timestamp_to_utc(self):
        """Test formatting UTC timestamp to UTC."""
        from zoneinfo import ZoneInfo

        dt = datetime(2026, 1, 9, 20, 30, 0, tzinfo=timezone.utc)
        result = format_timestamp_for_display(dt, "UTC")

        # Compute expected value dynamically
        expected_dt = dt.astimezone(ZoneInfo("UTC"))
        expected = expected_dt.isoformat()

        assert result == expected

    def test_format_utc_timestamp_to_eastern(self):
        """Test formatting UTC timestamp to US/Eastern timezone."""
        from zoneinfo import ZoneInfo

        dt = datetime(2026, 1, 9, 20, 30, 0, tzinfo=timezone.utc)
        result = format_timestamp_for_display(dt, "America/New_York")

        # Compute expected value dynamically
        expected_dt = dt.astimezone(ZoneInfo("America/New_York"))
        expected = expected_dt.isoformat()

        assert result == expected

    def test_format_utc_timestamp_to_london(self):
        """Test formatting UTC timestamp to Europe/London timezone."""
        from zoneinfo import ZoneInfo

        dt = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = format_timestamp_for_display(dt, "Europe/London")

        # Compute expected value dynamically
        expected_dt = dt.astimezone(ZoneInfo("Europe/London"))
        expected = expected_dt.isoformat()

        assert result == expected

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

    def test_format_timestamp_to_tokyo(self):
        """Test formatting UTC timestamp to Asia/Tokyo timezone."""
        from zoneinfo import ZoneInfo

        dt = datetime(2026, 1, 9, 20, 30, 0, tzinfo=timezone.utc)
        result = format_timestamp_for_display(dt, "Asia/Tokyo")

        # Tokyo is UTC+9
        expected_dt = dt.astimezone(ZoneInfo("Asia/Tokyo"))
        expected = expected_dt.isoformat()

        assert result == expected
        assert "+09:00" in result

    def test_format_timestamp_to_los_angeles(self):
        """Test formatting UTC timestamp to America/Los_Angeles timezone."""
        from zoneinfo import ZoneInfo

        dt = datetime(2026, 1, 9, 20, 30, 0, tzinfo=timezone.utc)
        result = format_timestamp_for_display(dt, "America/Los_Angeles")

        # LA is UTC-8 in January (PST)
        expected_dt = dt.astimezone(ZoneInfo("America/Los_Angeles"))
        expected = expected_dt.isoformat()

        assert result == expected
        assert "-08:00" in result

    def test_format_timestamp_handles_dst_transition(self):
        """Test formatting handles daylight saving time transitions."""
        from zoneinfo import ZoneInfo

        # Summer time in London (BST = UTC+1)
        dt_summer = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        result_summer = format_timestamp_for_display(dt_summer, "Europe/London")
        expected_summer = dt_summer.astimezone(ZoneInfo("Europe/London")).isoformat()
        assert result_summer == expected_summer

        # Winter time in London (GMT = UTC+0)
        dt_winter = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result_winter = format_timestamp_for_display(dt_winter, "Europe/London")
        expected_winter = dt_winter.astimezone(ZoneInfo("Europe/London")).isoformat()
        assert result_winter == expected_winter


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
