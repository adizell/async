# app/shared/utils/datetime_utils.py

"""
Utilities for datetime operations.

This module provides helper functions for working with dates and times
in a consistent manner throughout the application, handling timezone
awareness and various conversion operations.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import pytz  # Dependência para suporte a fusos horários


class DateTimeUtil:
    """
    Utility class for datetime operations.

    Provides static methods for common datetime operations like:
    - Getting current UTC time
    - Converting between different datetime formats
    - Adding/subtracting time periods
    - Comparing dates
    - Converting between UTC and São Paulo timezone
    """

    # Definir timezone de São Paulo/Brasil
    SAO_PAULO_TZ = pytz.timezone('America/Sao_Paulo')

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
    def localnow() -> datetime:
        """
        Get current time in São Paulo timezone.

        Returns:
            datetime: Current time in São Paulo timezone with timezone info
        """
        return datetime.now(DateTimeUtil.SAO_PAULO_TZ)

    @staticmethod
    def localnow_naive() -> datetime:
        """
        Get current São Paulo time as naive datetime (without timezone).

        Returns:
            datetime: Current São Paulo time without timezone info
        """
        return DateTimeUtil.localnow().replace(tzinfo=None)

    @staticmethod
    def utc_to_local(dt: datetime) -> datetime:
        """
        Convert a UTC datetime to São Paulo timezone.

        Args:
            dt: UTC datetime (timezone-aware or naive)

        Returns:
            datetime: São Paulo timezone datetime (timezone-aware)
        """
        # Garantir que dt está em UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elif dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)

        # Converter para São Paulo
        return dt.astimezone(DateTimeUtil.SAO_PAULO_TZ)

    @staticmethod
    def local_to_utc(dt: datetime) -> datetime:
        """
        Convert a São Paulo datetime to UTC.

        Args:
            dt: São Paulo datetime (timezone-aware or naive)

        Returns:
            datetime: UTC datetime (timezone-aware)
        """
        # Se o datetime é ingênuo, assumir que é em horário de São Paulo
        if dt.tzinfo is None:
            dt = DateTimeUtil.SAO_PAULO_TZ.localize(dt)
        elif dt.tzinfo != DateTimeUtil.SAO_PAULO_TZ:
            dt = dt.astimezone(DateTimeUtil.SAO_PAULO_TZ)

        # Converter para UTC
        return dt.astimezone(timezone.utc)

    @staticmethod
    def for_storage(dt: Optional[datetime] = None) -> datetime:
        """
        Format a datetime for database storage.

        Converts to UTC and strips timezone info for consistent storage.
        If no datetime is provided, uses current time.

        Args:
            dt: Datetime to format (optional)

        Returns:
            datetime: UTC naive datetime ready for storage
        """
        if dt is None:
            dt = DateTimeUtil.utcnow()

        # Se tem timezone, converter para UTC
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        else:
            # Se não tem timezone, assumir que já é UTC
            dt = dt.replace(tzinfo=timezone.utc)

        # Remover timezone info para salvar no BD
        return dt.replace(tzinfo=None)

    @staticmethod
    def from_storage(dt: datetime) -> datetime:
        """
        Convert a stored naive datetime to a timezone-aware São Paulo datetime.

        Assumes stored datetime is UTC without timezone info.

        Args:
            dt: Naive datetime from storage

        Returns:
            datetime: São Paulo timezone-aware datetime
        """
        if dt is None:
            return None

        # Adicionar timezone UTC ao timestamp salvo
        dt_utc = dt.replace(tzinfo=timezone.utc)

        # Converter para São Paulo
        return dt_utc.astimezone(DateTimeUtil.SAO_PAULO_TZ)

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
    def timestamp_to_local_datetime(timestamp: float) -> datetime:
        """
        Convert a UTC timestamp to São Paulo datetime.

        Args:
            timestamp: Unix timestamp

        Returns:
            datetime: Datetime object with São Paulo timezone
        """
        dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt_utc.astimezone(DateTimeUtil.SAO_PAULO_TZ)

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
    def format_local(dt: datetime, format_str: str = "%d/%m/%Y %H:%M:%S") -> str:
        """
        Format datetime in São Paulo timezone with a custom format.

        Args:
            dt: Datetime to format
            format_str: Format string (default: DD/MM/YYYY HH:MM:SS)

        Returns:
            str: Formatted datetime string
        """
        # Converter para São Paulo se tiver timezone
        if dt.tzinfo is not None:
            dt = dt.astimezone(DateTimeUtil.SAO_PAULO_TZ)
        else:
            # Se não tiver timezone, assumir que é UTC e converter
            dt = datetime.replace(tzinfo=timezone.utc).astimezone(DateTimeUtil.SAO_PAULO_TZ)

        return dt.strftime(format_str)

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
    def parse_local(date_string: str, format_str: str = "%d/%m/%Y %H:%M:%S") -> datetime:
        """
        Parse a formatted string as a São Paulo datetime.

        Args:
            date_string: Formatted date string
            format_str: Format string used (default: DD/MM/YYYY HH:MM:SS)

        Returns:
            datetime: Parsed datetime in São Paulo timezone
        """
        naive_dt = datetime.strptime(date_string, format_str)
        return DateTimeUtil.SAO_PAULO_TZ.localize(naive_dt)

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
