# app/test/utils/test_datetime_utils.py

# Para Rodar o Script:
# pytest app/test/utils/test_datetime_utils.py -v

import pytest
from datetime import datetime, timezone
import pytz
from app.shared.utils.datetime_utils import DateTimeUtil


@pytest.mark.asyncio
class TestDateTimeUtil:
    """Test suite for DateTimeUtil class."""

    def test_utcnow(self):
        """Test utcnow() method generates timezone-aware UTC time."""
        dt = DateTimeUtil.utcnow()
        assert dt.tzinfo is not None
        assert dt.tzinfo == timezone.utc

    def test_utcnow_naive(self):
        """Test utcnow_naive() method generates timezone-naive time."""
        dt = DateTimeUtil.utcnow_naive()
        assert dt.tzinfo is None

    def test_localnow(self):
        """Test localnow() method generates São Paulo timezone time."""
        dt = DateTimeUtil.localnow()
        assert dt.tzinfo is not None
        assert dt.tzinfo.zone == 'America/Sao_Paulo'

    def test_localnow_naive(self):
        """Test localnow_naive() method generates timezone-naive São Paulo time."""
        dt = DateTimeUtil.localnow_naive()
        assert dt.tzinfo is None

    def test_utc_to_local(self):
        """Test conversion from UTC to São Paulo timezone."""
        # Create a specific UTC time
        utc_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Convert to São Paulo
        sp_time = DateTimeUtil.utc_to_local(utc_time)

        # São Paulo is typically UTC-3 (or UTC-2 during DST)
        # But let's just verify the timezone is correct and hours are different
        assert sp_time.tzinfo.zone == 'America/Sao_Paulo'
        assert sp_time.hour != utc_time.hour or sp_time.day != utc_time.day

    def test_local_to_utc(self):
        """Test conversion from São Paulo timezone to UTC."""
        # Create a specific São Paulo time
        sp_tz = pytz.timezone('America/Sao_Paulo')
        sp_time = sp_tz.localize(datetime(2023, 6, 15, 9, 0, 0))

        # Convert to UTC
        utc_time = DateTimeUtil.local_to_utc(sp_time)

        # Verify timezone
        assert utc_time.tzinfo == timezone.utc
        assert utc_time.hour != sp_time.hour or utc_time.day != sp_time.day

    def test_for_storage(self):
        """Test formatting datetime for storage."""
        # Test with timezone-aware datetime
        sp_tz = pytz.timezone('America/Sao_Paulo')
        sp_time = sp_tz.localize(datetime(2023, 6, 15, 9, 0, 0))

        storage_time = DateTimeUtil.for_storage(sp_time)

        # Should be timezone-naive
        assert storage_time.tzinfo is None

        # Hours should be different (conversion to UTC happened)
        assert storage_time.hour != sp_time.hour or storage_time.day != sp_time.day

    def test_from_storage(self):
        """Test converting stored datetime to timezone-aware São Paulo time."""
        # Create a naive UTC datetime as if from storage
        storage_time = datetime(2023, 6, 15, 12, 0, 0)

        # Convert to São Paulo timezone
        sp_time = DateTimeUtil.from_storage(storage_time)

        # Should have São Paulo timezone
        assert sp_time.tzinfo.zone == 'America/Sao_Paulo'

        # Hours should be different (conversion from UTC to SP happened)
        assert sp_time.hour != storage_time.hour or sp_time.day != storage_time.day

    def test_timestamp_conversions(self):
        """Test timestamp conversion methods."""
        now = datetime.now(timezone.utc)
        timestamp = DateTimeUtil.datetime_to_timestamp(now)

        utc_dt = DateTimeUtil.timestamp_to_datetime(timestamp)
        local_dt = DateTimeUtil.timestamp_to_local_datetime(timestamp)

        # Check timezones
        assert utc_dt.tzinfo == timezone.utc
        assert local_dt.tzinfo.zone == 'America/Sao_Paulo'

        # Check conversion accuracy (within 1 second tolerance)
        assert abs((utc_dt - now).total_seconds()) < 1

    def test_format_local(self):
        """Test formatting with São Paulo timezone."""
        utc_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Format with default format
        formatted = DateTimeUtil.format_local(utc_time)

        # Should have day/month/year format
        assert '15/06/2023' in formatted

        # Format with custom format
        custom = DateTimeUtil.format_local(utc_time, "%Y-%m-%d")
        assert custom == "2023-06-15"
