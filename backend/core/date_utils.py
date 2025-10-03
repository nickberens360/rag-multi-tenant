"""
Date and time utilities for consistent handling across the application.

This module provides shared utilities for parsing timestamps and time ranges,
ensuring consistent behavior and eliminating code duplication.
"""

from datetime import datetime, timedelta, timezone
from typing import Tuple


def parse_time_range(time_range: str, end_date: datetime = None) -> Tuple[datetime, datetime]:
    """
    Parse time range string and return start and end dates.

    Args:
        time_range: Time range string ('1h', '6h', '24h', '7d', '30d')
        end_date: Optional end date. If None, uses current time as end date.

    Returns:
        Tuple[datetime, datetime]: (start_date, end_date)

    Raises:
        ValueError: If time_range format is not recognized
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc).replace(tzinfo=None)

    time_deltas = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    if time_range not in time_deltas:
        raise ValueError(f"Unsupported time range: {time_range}")

    delta = time_deltas[time_range]
    start_date = end_date - delta

    return start_date, end_date


def parse_time_range_start_only(time_range: str, end_date: datetime) -> datetime:
    """
    Parse time range string and return only the start date based on the end date.

    This is a convenience function for cases where only the start date is needed.

    Args:
        time_range: Time range string ('1h', '6h', '24h', '7d', '30d')
        end_date: The end date to calculate from

    Returns:
        datetime: The calculated start date
    """
    start_date, _ = parse_time_range(time_range, end_date)
    return start_date


def parse_timestamp_string(timestamp_str: str) -> datetime:
    """
    Parse timestamp string from database, handling various formats robustly.

    Args:
        timestamp_str: Timestamp string in various formats (ISO, space-separated, etc.)

    Returns:
        datetime: Parsed datetime object (timezone-naive UTC)

    Raises:
        ValueError: If timestamp format is not recognized
    """
    if not timestamp_str:
        raise ValueError("Empty timestamp string")

    try:
        # Handle ISO format with timezone info (e.g., "2023-12-25T10:30:00Z" or "2023-12-25T10:30:00+00:00")
        if "T" in timestamp_str:
            # Replace 'Z' with '+00:00' for fromisoformat compatibility
            normalized = timestamp_str.replace("Z", "+00:00")
            dt_obj = datetime.fromisoformat(normalized)

            # Convert to naive UTC datetime for consistency
            if dt_obj.tzinfo is not None:
                return dt_obj.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                # Already naive, assume UTC
                return dt_obj

        # Handle space-separated format (e.g., "2023-12-25 10:30:00" or "2023-12-25 10:30:00.123456")
        elif " " in timestamp_str:
            try:
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

        # Handle date-only format (e.g., "2023-12-25")
        else:
            return datetime.strptime(timestamp_str, "%Y-%m-%d")

    except (ValueError, TypeError) as e:
        raise ValueError(f"Unable to parse timestamp '{timestamp_str}': {e}") from e


def get_utc_now() -> datetime:
    """
    Get current UTC time as a timezone-naive datetime.

    Returns:
        datetime: Current UTC time without timezone info
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_utc_naive(dt: datetime) -> datetime:
    """
    Ensure a datetime object is timezone-naive UTC.

    Args:
        dt: Input datetime object

    Returns:
        datetime: Timezone-naive UTC datetime
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        # Already naive, assume it's UTC
        return dt
