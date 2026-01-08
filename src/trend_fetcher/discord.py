"""Discord webhook notification sender."""

import httpx
import asyncio
import logging
from typing import Optional
from datetime import datetime

from .config import settings
from .models import TrendItem

logger = logging.getLogger(__name__)

# Geo code to country name/flag mapping
GEO_DISPLAY = {
    "US": ("United States", "🇺🇸"),
    "GB": ("United Kingdom", "🇬🇧"),
    "ID": ("Indonesia", "🇮🇩"),
}


def format_discord_message(trend: TrendItem) -> dict:
    """Format a trend as a Discord webhook message with embed."""
    country_name, flag = GEO_DISPLAY.get(trend.geo, (trend.geo, "🌍"))

    # Determine status emoji
    status_emoji = "🟢" if trend.status.lower() == "active" else "⚫"

    # Build description
    description_lines = []

    if trend.search_volume:
        volume_str = trend.search_volume
        if trend.growth_percent:
            volume_str += f" ({trend.growth_percent})"
        description_lines.append(f"📊 **Volume:** {volume_str}")

    if trend.started_time:
        description_lines.append(f"⏰ **Started:** {trend.started_time}")

    if trend.duration:
        description_lines.append(f"⏱️ **Duration:** {trend.duration}")

    description_lines.append(f"{status_emoji} **Status:** {trend.status}")

    # Add related queries if available
    if trend.related_queries:
        queries = ", ".join(trend.related_queries[:3])
        description_lines.append(f"🔗 **Related:** {queries}")

    description = "\n".join(description_lines)

    # Google Trends URL
    trends_url = f"https://trends.google.com/trending?geo={trend.geo}&category={settings.category_id}"

    embed = {
        "title": f"🔥 {trend.title}",
        "description": description,
        "color": 0xFF6B35 if trend.status.lower() == "active" else 0x6B7280,
        "fields": [
            {
                "name": "📍 Region",
                "value": f"{flag} {country_name}",
                "inline": True,
            },
            {
                "name": "🏆 Rank",
                "value": f"#{trend.rank}",
                "inline": True,
            },
            {
                "name": "🎮 Category",
                "value": "Games",
                "inline": True,
            },
        ],
        "footer": {
            "text": "Google Trends Gaming Alert • De-duplicated per day",
        },
        "timestamp": datetime.utcnow().isoformat(),
        "url": trends_url,
    }

    return {
        "content": "<@906519204214214666>",  # Tag user with Discord ID
        "embeds": [embed],
    }


async def send_discord_notification(
    trend: TrendItem,
    webhook_url: Optional[str] = None,
    max_retries: int = 3,
) -> bool:
    """
    Send a Discord notification for a new trend.
    
    Args:
        trend: The trend item to notify about
        webhook_url: Optional override for webhook URL
        max_retries: Number of retry attempts
        
    Returns:
        True if successful, False otherwise
    """
    url = webhook_url or settings.discord_webhook_url
    message = format_discord_message(trend)

    retry_delay = 1

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url, json=message)

                if response.status_code == 429:
                    # Rate limited
                    retry_after = response.json().get("retry_after", retry_delay * 2)
                    logger.warning(f"Discord rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                if response.status_code >= 400:
                    logger.error(
                        f"Discord webhook error {response.status_code}: {response.text}"
                    )
                    if response.status_code < 500:
                        break  # Don't retry client errors
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue

                logger.info(f"Discord notification sent: {trend.title} ({trend.geo})")
                return True

            except httpx.TimeoutException:
                logger.warning(f"Discord timeout (attempt {attempt + 1})")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2

            except Exception as e:
                logger.error(f"Discord notification error: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2

    logger.error(f"Failed to send Discord notification for: {trend.title}")
    return False


async def send_test_notification(webhook_url: Optional[str] = None) -> bool:
    """Send a test notification to verify webhook works."""
    url = webhook_url or settings.discord_webhook_url

    message = {
        "content": "🧪 **Test Message**\n\nGoogle Trends Gaming Alert System is online.\n\n✅ Webhook connection verified.",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=message)
            return response.status_code < 400
        except Exception as e:
            logger.error(f"Test notification failed: {e}")
            return False
