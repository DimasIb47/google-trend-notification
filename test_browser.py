"""Simple test - output to file for full visibility."""
import asyncio
import sys
import os

os.environ['PYTHONUTF8'] = '1'
sys.path.insert(0, 'src')

from trend_fetcher.fetcher import BrowserFetcher
from trend_fetcher.discord import send_discord_notification

async def test():
    output = []
    output.append("=" * 50)
    output.append("PLAYWRIGHT BROWSER FETCHER TEST")
    output.append("=" * 50)
    
    fetcher = BrowserFetcher()
    
    try:
        output.append("\n[1] Initializing browser...")
        await fetcher.initialize()
        output.append("    OK - Browser ready")
        
        output.append("\n[2] Fetching trends for Indonesia (ID)...")
        success, trends, error = await fetcher.fetch_trends("ID")
        
        output.append(f"    Success: {success}")
        output.append(f"    Trends found: {len(trends)}")
        
        if error:
            output.append(f"    Error: {error}")
        
        if trends:
            output.append("\n[3] Trends extracted:")
            for t in trends[:5]:
                output.append(f"\n    #{t.rank}: {t.title}")
                output.append(f"        Volume: {t.search_volume} ({t.growth_percent})")
                output.append(f"        Started: {t.started_time}")
                output.append(f"        Status: {t.status}")
                if t.duration:
                    output.append(f"        Duration: {t.duration}")
            
            # Send Discord notification for first trend
            output.append(f"\n[4] Sending Discord notification for: {trends[0].title}")
            sent = await send_discord_notification(trends[0])
            output.append(f"    Sent: {sent}")
        
        output.append("\n" + "=" * 50)
        output.append("TEST COMPLETE - SUCCESS!")
        output.append("=" * 50)
        
    except Exception as e:
        output.append(f"ERROR: {e}")
        
    finally:
        await fetcher.close()
    
    # Write to file
    with open("test_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    print("Test complete. Results in test_result.txt")

if __name__ == "__main__":
    asyncio.run(test())
