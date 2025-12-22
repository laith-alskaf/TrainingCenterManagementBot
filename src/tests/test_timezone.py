"""
Unit tests for timezone utilities.
"""
import pytest
from datetime import datetime, date, time
import pytz

from  domain.value_objects import (
    SYRIA_TZ,
    now_syria,
    today_syria,
    localize_datetime,
    parse_date,
    parse_time,
    parse_datetime_syria,
    is_past_or_now,
    format_datetime_syria,
    datetime_to_mongodb,
    datetime_from_mongodb,
)


class TestSyriaTimezone:
    """Tests for Syria timezone utilities."""
    
    def test_syria_timezone(self):
        """Test Syria timezone is correctly defined."""
        assert str(SYRIA_TZ) == "Asia/Damascus"
    
    def test_now_syria(self):
        """Test now_syria returns timezone-aware datetime."""
        now = now_syria()
        assert now.tzinfo is not None
        assert str(now.tzinfo) == "Asia/Damascus" or "EET" in str(now.tzinfo) or "EEST" in str(now.tzinfo)
    
    def test_today_syria(self):
        """Test today_syria returns correct date."""
        today = today_syria()
        assert isinstance(today, date)
        
        # Should match now_syria's date
        now = now_syria()
        assert today == now.date()


class TestDateTimeParsing:
    """Tests for date/time parsing functions."""
    
    def test_parse_date_valid(self):
        """Test parsing valid date strings."""
        d = parse_date("2024-01-15")
        assert d == date(2024, 1, 15)
    
    def test_parse_date_with_whitespace(self):
        """Test parsing date with whitespace."""
        d = parse_date("  2024-01-15  ")
        assert d == date(2024, 1, 15)
    
    def test_parse_date_invalid(self):
        """Test parsing invalid date raises error."""
        with pytest.raises(ValueError):
            parse_date("15-01-2024")  # Wrong format
        
        with pytest.raises(ValueError):
            parse_date("2024/01/15")  # Wrong separator
    
    def test_parse_time_valid(self):
        """Test parsing valid time strings."""
        t = parse_time("14:30")
        assert t == time(14, 30)
    
    def test_parse_time_midnight(self):
        """Test parsing midnight time."""
        t = parse_time("00:00")
        assert t == time(0, 0)
    
    def test_parse_time_end_of_day(self):
        """Test parsing end of day time."""
        t = parse_time("23:59")
        assert t == time(23, 59)
    
    def test_parse_time_invalid(self):
        """Test parsing invalid time raises error."""
        with pytest.raises(ValueError):
            parse_time("2:30 PM")  # 12-hour format
        
        with pytest.raises(ValueError):
            parse_time("25:00")  # Invalid hour
    
    def test_parse_datetime_syria(self):
        """Test parsing date and time into Syria timezone."""
        dt = parse_datetime_syria("2024-01-15", "14:30")
        
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30
        assert dt.tzinfo is not None


class TestTimeComparison:
    """Tests for time comparison functions."""
    
    def test_is_past_or_now_past(self):
        """Test is_past_or_now with past datetime."""
        past = now_syria().replace(year=2020)
        assert is_past_or_now(past) is True
    
    def test_is_past_or_now_future(self):
        """Test is_past_or_now with future datetime."""
        future = now_syria().replace(year=2030)
        assert is_past_or_now(future) is False
    
    def test_is_past_or_now_ignores_seconds(self):
        """Test that comparison ignores seconds."""
        now = now_syria()
        
        # Same minute but different seconds
        same_minute = now.replace(second=0, microsecond=0)
        assert is_past_or_now(same_minute) is True


class TestLocalization:
    """Tests for datetime localization."""
    
    def test_localize_naive_datetime(self):
        """Test localizing a naive datetime."""
        naive = datetime(2024, 1, 15, 14, 30)
        localized = localize_datetime(naive)
        
        assert localized.tzinfo is not None
        assert localized.hour == 14
        assert localized.minute == 30
    
    def test_localize_aware_datetime(self):
        """Test localizing an already aware datetime."""
        utc = pytz.UTC.localize(datetime(2024, 1, 15, 12, 0))
        localized = localize_datetime(utc)
        
        assert localized.tzinfo is not None
        # Should be converted to Syria time (UTC+2 or UTC+3)
        assert localized.hour in (14, 15)


class TestFormatting:
    """Tests for datetime formatting."""
    
    def test_format_with_time(self):
        """Test formatting with time."""
        dt = SYRIA_TZ.localize(datetime(2024, 1, 15, 14, 30))
        formatted = format_datetime_syria(dt, include_time=True)
        
        assert formatted == "2024-01-15 14:30"
    
    def test_format_without_time(self):
        """Test formatting without time."""
        dt = SYRIA_TZ.localize(datetime(2024, 1, 15, 14, 30))
        formatted = format_datetime_syria(dt, include_time=False)
        
        assert formatted == "2024-01-15"


class TestMongoDBConversion:
    """Tests for MongoDB datetime conversion."""
    
    def test_to_mongodb_converts_to_utc(self):
        """Test conversion to UTC for MongoDB."""
        syria_dt = SYRIA_TZ.localize(datetime(2024, 1, 15, 14, 30))
        utc_dt = datetime_to_mongodb(syria_dt)
        
        assert utc_dt.tzinfo == pytz.UTC
        # Syria is UTC+2 or UTC+3, so UTC time should be earlier
        assert utc_dt.hour < syria_dt.hour or utc_dt.day < syria_dt.day
    
    def test_from_mongodb_converts_to_syria(self):
        """Test conversion from UTC to Syria timezone."""
        utc_dt = pytz.UTC.localize(datetime(2024, 1, 15, 12, 0))
        syria_dt = datetime_from_mongodb(utc_dt)
        
        assert str(syria_dt.tzinfo) == "Asia/Damascus" or "EET" in str(syria_dt.tzinfo)
        # Syria is ahead of UTC
        assert syria_dt.hour > utc_dt.hour or syria_dt.day > utc_dt.day
    
    def test_roundtrip_conversion(self):
        """Test that conversion to/from MongoDB preserves the instant."""
        original = SYRIA_TZ.localize(datetime(2024, 1, 15, 14, 30))
        
        # Convert to MongoDB and back
        mongodb = datetime_to_mongodb(original)
        restored = datetime_from_mongodb(mongodb)
        
        # Should represent the same instant
        assert original.utctimetuple() == restored.utctimetuple()
