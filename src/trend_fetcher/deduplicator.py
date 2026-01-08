"""Deduplication logic for trends."""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re

from .config import settings
from .database import db
from .models import TrendItem

logger = logging.getLogger(__name__)


def get_date_key_from_started_time(started_time: str, geo: str) -> str:
    """
    Extract date_key from the 'started time' string.
    
    Examples:
        "3 hours ago" -> today's date
        "1 day ago" -> yesterday's date
        "2 days ago" -> 2 days ago
        
    Falls back to system timezone (Asia/Jakarta) if geo timezone unknown.
    """
    tz = get_timezone_for_geo(geo)
    now = datetime.now(tz)

    if not started_time:
        return now.strftime("%Y-%m-%d")

    started_lower = started_time.lower()

    # Parse relative time
    hours_ago = 0
    days_ago = 0

    # Match patterns like "3 hours ago", "1 hour ago"
    hours_match = re.search(r'(\d+)\s*hours?\s*ago', started_lower)
    if hours_match:
        hours_ago = int(hours_match.group(1))

    # Match patterns like "1 day ago", "2 days ago"
    days_match = re.search(r'(\d+)\s*days?\s*ago', started_lower)
    if days_match:
        days_ago = int(days_match.group(1))

    # Match patterns like "30 minutes ago"
    minutes_match = re.search(r'(\d+)\s*minutes?\s*ago', started_lower)
    if minutes_match:
        # Minutes ago is still today
        pass

    # Calculate the actual datetime
    if days_ago > 0:
        target_date = now - timedelta(days=days_ago)
    elif hours_ago >= 24:
        target_date = now - timedelta(hours=hours_ago)
    else:
        target_date = now

    return target_date.strftime("%Y-%m-%d")


def get_timezone_for_geo(geo: str) -> ZoneInfo:
    """Get timezone for a geo code."""
    geo_timezones = {
        "US": "America/New_York",
        "GB": "Europe/London",
        "ID": "Asia/Jakarta",
    }

    tz_name = geo_timezones.get(geo.upper(), settings.timezone)

    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo(settings.timezone)


async def is_new_trend(trend: TrendItem) -> bool:
    """
    Check if a trend is new (not seen today for this geo).
    
    Uses atomic database insert with unique constraint.
    Returns True if new, False if duplicate.
    """
    date_key = get_date_key_from_started_time(trend.started_time, trend.geo)

    return await db.check_and_insert_dedupe(
        geo=trend.geo,
        date_key=date_key,
        normalized_title=trend.normalized_title,
    )


async def cleanup_expired():
    """Clean up expired deduplication records."""
    return await db.cleanup_expired_dedupe_keys()
