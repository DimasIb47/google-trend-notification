"""Full test - ALL trends from all 3 regions."""
import asyncio
import sys
import os

os.environ['PYTHONUTF8'] = '1'
sys.path.insert(0, 'src')

from trend_fetcher.fetcher import BrowserFetcher
from trend_fetcher.discord import send_discord_notification

REGIONS = ["US", "GB", "ID"]

async def test_all_trends():
    print("=" * 50)
    print("FULL TEST - ALL TRENDS FROM 3 REGIONS")
    print("=" * 50)
    
    fetcher = BrowserFetcher()
    
    try:
        print("\nInitializing browser...")
        await fetcher.initialize()
        print("Browser ready!")
        
        total_trends = 0
        total_sent = 0
        
        for geo in REGIONS:
            print(f"\n--- {geo} ---")
            success, trends, error = await fetcher.fetch_trends(geo)
            
            if not success:
                print(f"FAILED: {error}")
                continue
            
            print(f"Found {len(trends)} trends")
            total_trends += len(trends)
            
            # Send notification for ALL trends
            for t in trends:
                print(f"  Sending: {t.title}...")
                sent = await send_discord_notification(t)
                if sent:
                    total_sent += 1
                # Rate limit protection
                await asyncio.sleep(0.5)
            
            # Delay between regions
            await asyncio.sleep(2)
        
        print("\n" + "=" * 50)
        print(f"DONE: {total_trends} trends, {total_sent} notifications")
        print("=" * 50)
        
    finally:
        await fetcher.close()

if __name__ == "__main__":
    asyncio.run(test_all_trends())
