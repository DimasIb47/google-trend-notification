"""Minimal test for core functionality."""
import asyncio
import sys
import os

# Fix Windows encoding
os.environ['PYTHONUTF8'] = '1'
sys.path.insert(0, 'src')

from trend_fetcher.fetcher import TrendsFetcher
from trend_fetcher.parser import parse_batchexecute_response

async def test():
    print("TEST START")
    
    async with TrendsFetcher() as fetcher:
        success, raw, error = await fetcher.fetch_trends("ID")
        
        print(f"Fetch success: {success}")
        print(f"Response length: {len(raw) if raw else 0}")
        
        if success:
            trends = parse_batchexecute_response(raw, "ID")
            print(f"Trends found: {len(trends)}")
            
            for t in trends[:3]:
                # Use ASCII only output
                print(f"  - {t.title} | Vol: {t.search_volume} | {t.started_time}")
        else:
            print(f"Error: {error}")
    
    print("TEST DONE")

if __name__ == "__main__":
    asyncio.run(test())
