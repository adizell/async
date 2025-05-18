# app/shared/utils/datetime_utils.py

"""
Utilities for datetime operations.

This module provides helper functions for working with dates and times
in a consistent manner throughout the application, handling timezone
awareness and various conversion operations.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


class DateTimeUtil:
    """
    Utility class for datetime operations.

    Provides static methods for common datetime operations like:
    - Getting current UTC time
    - Converting between different datetime formats
    - Adding/subtracting time periods
    - Comparing dates
    """

    @staticmethod
    def utcnow() -> datetime:
        """
        Get current UTC time.

        This is a replacement for datetime.utcnow() which is deprecated in Python 3.12+.
        It returns a timezone-aware datetime object in UTC.

        Returns:
            datetime: Current UTC time with timezone info
        """
        return datetime.now(timezone.utc)

    @staticmethod
    def utcnow_naive() -> datetime:
        """
        Get current UTC time as naive datetime (without timezone).

        Useful for compatibility with systems that expect naive datetimes.

        Returns:
            datetime: Current UTC time without timezone info
        """
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def timestamp_to_datetime(timestamp: float) -> datetime:
        """
        Convert a UTC timestamp to datetime.

        Args:
            timestamp: Unix timestamp

        Returns:
            datetime: Datetime object with UTC timezone
        """
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    @staticmethod
    def datetime_to_timestamp(dt: datetime) -> float:
        """
        Convert datetime to UTC timestamp.

        Args:
            dt: Datetime object

        Returns:
            float: Unix timestamp
        """
        # Ensure datetime is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.timestamp()

    @staticmethod
    def add_days(dt: datetime, days: int) -> datetime:
        """
        Add days to a datetime.

        Args:
            dt: Datetime object
            days: Number of days to add

        Returns:
            datetime: New datetime with added days
        """
        return dt + timedelta(days=days)

    @staticmethod
    def add_minutes(dt: datetime, minutes: int) -> datetime:
        """
        Add minutes to a datetime.

        Args:
            dt: Datetime object
            minutes: Number of minutes to add

        Returns:
            datetime: New datetime with added minutes
        """
        return dt + timedelta(minutes=minutes)

    @staticmethod
    def days_between(start_date: datetime, end_date: datetime) -> int:
        """
        Calculate days between two datetimes.

        Args:
            start_date: Start datetime
            end_date: End datetime

        Returns:
            int: Number of days between the two dates
        """
        # Ensure both dates are timezone-aware or both naive
        if start_date.tzinfo is None and end_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        elif start_date.tzinfo is not None and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        diff = end_date - start_date
        return diff.days

    @staticmethod
    def format_iso(dt: datetime) -> str:
        """
        Format datetime as ISO 8601 string.

        Args:
            dt: Datetime to format

        Returns:
            str: ISO formatted datetime string
        """
        return dt.isoformat()

    @staticmethod
    def parse_iso(iso_string: str) -> datetime:
        """
        Parse ISO 8601 string to datetime.

        Args:
            iso_string: ISO formatted datetime string

        Returns:
            datetime: Parsed datetime object
        """
        return datetime.fromisoformat(iso_string)

    @staticmethod
    def is_future(dt: datetime) -> bool:
        """
        Check if datetime is in the future.

        Args:
            dt: Datetime to check

        Returns:
            bool: True if datetime is in the future
        """
        # Make sure we compare with timezone-aware now if dt is timezone-aware
        now = DateTimeUtil.utcnow() if dt.tzinfo is not None else DateTimeUtil.utcnow_naive()
        return dt > now

    @staticmethod
    def is_past(dt: datetime) -> bool:
        """
        Check if datetime is in the past.

        Args:
            dt: Datetime to check

        Returns:
            bool: True if datetime is in the past
        """
        # Make sure we compare with timezone-aware now if dt is timezone-aware
        now = DateTimeUtil.utcnow() if dt.tzinfo is not None else DateTimeUtil.utcnow_naive()
        return dt < now
