"""Quick integration test for the trends fetcher."""

import asyncio
import sys
import os

# Fix Windows console encoding
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, 'src')

from trend_fetcher.fetcher import TrendsFetcher
from trend_fetcher.parser import parse_batchexecute_response
from trend_fetcher.discord import send_discord_notification
from trend_fetcher.models import TrendItem


async def test_fetch_and_notify():
    """Test fetching trends and sending a notification."""
    print("=" * 60)
    print("Google Trends Gaming Alert - Integration Test")
    print("=" * 60)

    async with TrendsFetcher() as fetcher:
        for geo in ["ID", "US"]:
            print(f"\n[*] Testing {geo}...")

            success, raw_response, error = await fetcher.fetch_trends(geo)

            if not success:
                print(f"  [X] Fetch failed: {error}")
                continue

            print(f"  [OK] Fetched {len(raw_response)} bytes")

            # Parse
            trends = parse_batchexecute_response(raw_response, geo)
            print(f"  [OK] Parsed {len(trends)} trends")

            # Show trends
            for trend in trends[:5]:
                print(f"\n  [TREND] {trend.title}")
                print(f"     Volume: {trend.search_volume} ({trend.growth_percent})")
                print(f"     Started: {trend.started_time}")
                print(f"     Status: {trend.status}")

            # Send ONE notification for the first trend
            if trends:
                print(f"\n  [*] Sending Discord notification for: {trends[0].title}")
                sent = await send_discord_notification(trends[0])
                if sent:
                    print("  [OK] Discord notification sent!")
                else:
                    print("  [X] Discord notification failed")

            # Only test first geo for notifications
            break

    print("\n" + "=" * 60)
    print("[OK] Integration test complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_fetch_and_notify())
