"""
Comprehensive unit tests for backend.core.date_utils module.

Tests all date utility functions including edge cases, error handling,
and timezone consistency.
"""

from datetime import datetime, timedelta, timezone

import pytest

from backend.core.date_utils import (
    ensure_utc_naive,
    get_utc_now,
    parse_time_range,
    parse_time_range_start_only,
    parse_timestamp_string,
)


class TestParseTimeRange:
    """Tests for parse_time_range function."""

    def test_parse_time_range_valid_ranges(self):
        """Test parsing of all valid time range formats."""
        end_date = datetime(2024, 1, 15, 12, 0, 0)

        # Test 1 hour range
        start, end = parse_time_range("1h", end_date)
        assert end == end_date
        assert start == end_date - timedelta(hours=1)

        # Test 6 hour range
        start, end = parse_time_range("6h", end_date)
        assert end == end_date
        assert start == end_date - timedelta(hours=6)

        # Test 24 hour range
        start, end = parse_time_range("24h", end_date)
        assert end == end_date
        assert start == end_date - timedelta(days=1)

        # Test 7 day range
        start, end = parse_time_range("7d", end_date)
        assert end == end_date
        assert start == end_date - timedelta(days=7)

        # Test 30 day range
        start, end = parse_time_range("30d", end_date)
        assert end == end_date
        assert start == end_date - timedelta(days=30)

    def test_parse_time_range_with_custom_end_date(self):
        """Test that custom end date is respected."""
        custom_end = datetime(2024, 6, 15, 10, 30, 45)
        start, end = parse_time_range("24h", custom_end)

        assert end == custom_end
        assert start == datetime(2024, 6, 14, 10, 30, 45)

    def test_parse_time_range_without_end_date_uses_utc_now(self):
        """Test that omitting end_date uses current UTC time."""
        before_call = datetime.now(timezone.utc).replace(tzinfo=None)
        start, end = parse_time_range("1h")
        after_call = datetime.now(timezone.utc).replace(tzinfo=None)

        # End date should be between before and after
        assert before_call <= end <= after_call

        # Start should be 1 hour before end
        assert end - start == timedelta(hours=1)

    def test_parse_time_range_invalid_format(self):
        """Test that invalid time range raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported time range"):
            parse_time_range("invalid")

        with pytest.raises(ValueError, match="Unsupported time range"):
            parse_time_range("2h")  # Not a supported format

        with pytest.raises(ValueError, match="Unsupported time range"):
            parse_time_range("1d")  # Should be "24h" or "7d"

    def test_parse_time_range_returns_naive_datetime(self):
        """Test that returned datetimes are timezone-naive."""
        start, end = parse_time_range("24h")

        assert start.tzinfo is None
        assert end.tzinfo is None


class TestParseTimeRangeStartOnly:
    """Tests for parse_time_range_start_only function."""

    def test_returns_only_start_date(self):
        """Test that function returns only start date."""
        end_date = datetime(2024, 3, 15, 14, 30, 0)
        start = parse_time_range_start_only("7d", end_date)

        assert start == datetime(2024, 3, 8, 14, 30, 0)
        assert isinstance(start, datetime)

    def test_consistency_with_parse_time_range(self):
        """Test that results match parse_time_range."""
        end_date = datetime(2024, 5, 20, 9, 15, 30)

        start_only = parse_time_range_start_only("24h", end_date)
        start_full, _ = parse_time_range("24h", end_date)

        assert start_only == start_full


class TestParseTimestampString:
    """Tests for parse_timestamp_string function."""

    def test_parse_iso_format_with_z(self):
        """Test parsing ISO format with Z timezone indicator."""
        result = parse_timestamp_string("2024-01-15T10:30:00Z")

        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None  # Should be naive

    def test_parse_iso_format_with_offset(self):
        """Test parsing ISO format with timezone offset."""
        result = parse_timestamp_string("2024-01-15T10:30:00+00:00")

        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

    def test_parse_iso_format_with_non_utc_offset(self):
        """Test parsing ISO format with non-UTC timezone offset."""
        # 10:30 UTC-5 = 15:30 UTC
        result = parse_timestamp_string("2024-01-15T10:30:00-05:00")

        assert result == datetime(2024, 1, 15, 15, 30, 0)
        assert result.tzinfo is None

    def test_parse_space_separated_with_microseconds(self):
        """Test parsing space-separated format with microseconds."""
        result = parse_timestamp_string("2024-01-15 10:30:00.123456")

        assert result == datetime(2024, 1, 15, 10, 30, 0, 123456)
        assert result.tzinfo is None

    def test_parse_space_separated_without_microseconds(self):
        """Test parsing space-separated format without microseconds."""
        result = parse_timestamp_string("2024-01-15 10:30:00")

        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

    def test_parse_date_only_format(self):
        """Test parsing date-only format."""
        result = parse_timestamp_string("2024-01-15")

        assert result == datetime(2024, 1, 15, 0, 0, 0)
        assert result.tzinfo is None

    def test_parse_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Empty timestamp string"):
            parse_timestamp_string("")

    def test_parse_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Unable to parse timestamp"):
            parse_timestamp_string("invalid-date-format")

        with pytest.raises(ValueError, match="Unable to parse timestamp"):
            parse_timestamp_string("2024-13-45")  # Invalid month/day

    def test_parse_none_raises_error(self):
        """Test that None input raises ValueError."""
        with pytest.raises(ValueError):
            parse_timestamp_string(None)


class TestGetUtcNow:
    """Tests for get_utc_now function."""

    def test_returns_naive_datetime(self):
        """Test that function returns timezone-naive datetime."""
        result = get_utc_now()

        assert result.tzinfo is None
        assert isinstance(result, datetime)

    def test_returns_current_time(self):
        """Test that function returns approximately current time."""
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        result = get_utc_now()
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert before <= result <= after

    def test_multiple_calls_increase(self):
        """Test that sequential calls return increasing times."""
        time1 = get_utc_now()
        time2 = get_utc_now()

        assert time2 >= time1


class TestEnsureUtcNaive:
    """Tests for ensure_utc_naive function."""

    def test_converts_aware_utc_to_naive(self):
        """Test converting timezone-aware UTC datetime to naive."""
        aware_dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = ensure_utc_naive(aware_dt)

        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

    def test_converts_aware_non_utc_to_naive_utc(self):
        """Test converting non-UTC timezone-aware datetime to naive UTC."""
        # Create UTC-5 timezone
        utc_minus_5 = timezone(timedelta(hours=-5))
        aware_dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=utc_minus_5)

        result = ensure_utc_naive(aware_dt)

        # 10:30 UTC-5 = 15:30 UTC
        assert result == datetime(2024, 1, 15, 15, 30, 0)
        assert result.tzinfo is None

    def test_already_naive_returns_unchanged(self):
        """Test that already-naive datetime is returned unchanged."""
        naive_dt = datetime(2024, 1, 15, 10, 30, 0)
        result = ensure_utc_naive(naive_dt)

        assert result == naive_dt
        assert result.tzinfo is None

    def test_preserves_microseconds(self):
        """Test that microseconds are preserved during conversion."""
        aware_dt = datetime(2024, 1, 15, 10, 30, 0, 123456, tzinfo=timezone.utc)
        result = ensure_utc_naive(aware_dt)

        assert result.microsecond == 123456
        assert result.tzinfo is None


class TestIntegrationScenarios:
    """Integration tests for common usage patterns."""

    def test_parse_and_convert_iso_timestamp(self):
        """Test parsing ISO timestamp and ensuring it's naive UTC."""
        timestamp_str = "2024-01-15T10:30:00+05:00"
        parsed = parse_timestamp_string(timestamp_str)
        ensured = ensure_utc_naive(parsed)

        # Should already be naive from parse_timestamp_string
        assert parsed == ensured
        assert parsed.tzinfo is None

    def test_time_range_calculation_workflow(self):
        """Test typical workflow: get current time and calculate range."""
        end_date = get_utc_now()
        start_date, calculated_end = parse_time_range("7d", end_date)

        assert calculated_end == end_date
        assert end_date - start_date == timedelta(days=7)
        assert start_date.tzinfo is None
        assert calculated_end.tzinfo is None

    def test_database_timestamp_processing(self):
        """Test simulated database timestamp retrieval and processing."""
        # Simulate database returning ISO timestamp
        db_timestamp = "2024-01-15T14:30:00Z"

        # Parse it
        end_date = parse_timestamp_string(db_timestamp)

        # Calculate range
        start_date = parse_time_range_start_only("24h", end_date)

        assert start_date == datetime(2024, 1, 14, 14, 30, 0)
        assert end_date == datetime(2024, 1, 15, 14, 30, 0)
        assert start_date.tzinfo is None
        assert end_date.tzinfo is None
