"""Debug script to examine raw response."""
import asyncio
import sys
import os
import json

os.environ['PYTHONUTF8'] = '1'
sys.path.insert(0, 'src')

from trend_fetcher.fetcher import TrendsFetcher

async def debug():
    print("DEBUG: Fetching raw response...")
    
    async with TrendsFetcher() as fetcher:
        success, raw, error = await fetcher.fetch_trends("ID")
        
        print(f"Success: {success}")
        print(f"Length: {len(raw) if raw else 0}")
        print(f"Error: {error}")
        print("\n--- RAW RESPONSE ---")
        print(repr(raw[:2000] if raw else "None"))
        print("--- END ---")

if __name__ == "__main__":
    asyncio.run(debug())
