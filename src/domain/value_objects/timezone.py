"""
Timezone utilities for Syria (Asia/Damascus).
All datetime operations in the system use this module.
"""
from datetime import datetime, date, time
from typing import Optional
import pytz


SYRIA_TZ = pytz.timezone("Asia/Damascus")


def now_syria() -> datetime:
    """Get current datetime in Syria timezone."""
    return datetime.now(SYRIA_TZ)


def today_syria() -> date:
    """Get current date in Syria timezone."""
    return now_syria().date()


def localize_datetime(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware in Syria timezone.
    If naive, assumes it represents Syria local time.
    """
    if dt.tzinfo is None:
        return SYRIA_TZ.localize(dt)
    return dt.astimezone(SYRIA_TZ)


def parse_date(date_str: str) -> date:
    """
    Parse a date string in YYYY-MM-DD format.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        date object
        
    Raises:
        ValueError: If format is invalid
    """
    return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()


def parse_time(time_str: str) -> time:
    """
    Parse a time string in HH:MM 24-hour format.
    
    Args:
        time_str: Time string in HH:MM format
        
    Returns:
        time object
        
    Raises:
        ValueError: If format is invalid
    """
    return datetime.strptime(time_str.strip(), "%H:%M").time()


def parse_datetime_syria(date_str: str, time_str: str) -> datetime:
    """
    Parse date and time strings into a timezone-aware datetime in Syria timezone.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        time_str: Time in HH:MM 24-hour format
        
    Returns:
        Timezone-aware datetime in Asia/Damascus
    """
    d = parse_date(date_str)
    t = parse_time(time_str)
    naive_dt = datetime.combine(d, t)
    return SYRIA_TZ.localize(naive_dt)


def is_past_or_now(scheduled_dt: datetime) -> bool:
    """
    Check if a scheduled datetime is in the past or equal to current time.
    Uses minute-level resolution (ignores seconds).
    
    Args:
        scheduled_dt: Timezone-aware scheduled datetime
        
    Returns:
        True if scheduled time has passed or is now
    """
    now = now_syria()
    # Compare at minute level
    scheduled_minutes = scheduled_dt.replace(second=0, microsecond=0)
    now_minutes = now.replace(second=0, microsecond=0)
    return now_minutes >= scheduled_minutes


def format_datetime_syria(dt: datetime, include_time: bool = True) -> str:
    """
    Format a datetime for display in Syria timezone.
    
    Args:
        dt: Datetime to format
        include_time: Whether to include time in output
        
    Returns:
        Formatted string (YYYY-MM-DD HH:MM or YYYY-MM-DD)
    """
    syria_dt = localize_datetime(dt)
    if include_time:
        return syria_dt.strftime("%Y-%m-%d %H:%M")
    return syria_dt.strftime("%Y-%m-%d")


def datetime_to_mongodb(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC for MongoDB storage.
    MongoDB stores all datetimes in UTC.
    """
    if dt.tzinfo is None:
        dt = SYRIA_TZ.localize(dt)
    return dt.astimezone(pytz.UTC)


def datetime_from_mongodb(dt: datetime) -> datetime:
    """
    Convert a datetime from MongoDB (UTC) to Syria timezone.
    """
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(SYRIA_TZ)
