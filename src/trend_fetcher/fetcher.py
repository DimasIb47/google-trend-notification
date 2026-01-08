"""Google Trends fetcher using Playwright headless browser.

This fetcher uses a real browser to access Google Trends, ensuring we get
the exact same data that users see on the page.
"""

import asyncio
import logging
from typing import Optional, List, Tuple
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page, Playwright

from .config import settings
from .models import TrendItem

logger = logging.getLogger(__name__)


class BrowserFetcher:
    """Fetches trends using Playwright headless browser."""

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the browser instance (reusable)."""
        if self._initialized:
            return

        logger.info("Initializing Playwright browser...")
        self._playwright = await async_playwright().start()
        
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--no-sandbox",
                "--disable-images",  # Skip images for speed
            ]
        )
        
        self._initialized = True
        logger.info("Browser initialized successfully")

    async def close(self) -> None:
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._initialized = False
        logger.info("Browser closed")

    async def fetch_trends(self, geo: str, max_retries: int = 3) -> Tuple[bool, List[TrendItem], Optional[str]]:
        """
        Fetch trends for a geo by loading the actual Google Trends page.
        
        Returns:
            Tuple of (success, list of TrendItem, error_message)
        """
        if not self._initialized:
            await self.initialize()

        url = f"https://trends.google.com/trending?geo={geo}&category={settings.category_id}&hours={settings.hours}"
        
        retry_delay = 2
        last_error = None

        for attempt in range(max_retries):
            page = None
            try:
                logger.info(f"Fetching trends for {geo} (attempt {attempt + 1}/{max_retries})")
                
                # Create new page context
                page = await self._browser.new_page()
                
                # Block unnecessary resources for speed
                await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", lambda route: route.abort())
                await page.route("**/analytics*", lambda route: route.abort())
                await page.route("**/gtag*", lambda route: route.abort())
                
                # Navigate to page (use domcontentloaded instead of networkidle)
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Wait for trends table to load (increased timeout)
                await page.wait_for_selector("table tbody tr", timeout=30000)
                
                # Wait a bit for dynamic content to render
                await asyncio.sleep(2)
                
                # Extract trends from the table
                trends = await self._extract_trends_from_page(page, geo)
                
                if trends:
                    logger.info(f"Successfully fetched {len(trends)} trends for {geo}")
                    return (True, trends, None)
                else:
                    logger.warning(f"No trends found for {geo}")
                    return (True, [], None)

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Fetch attempt {attempt + 1} failed for {geo}: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2

            finally:
                if page:
                    await page.close()

        logger.error(f"Failed to fetch trends for {geo} after {max_retries} attempts: {last_error}")
        return (False, [], last_error)

    async def _extract_trends_from_page(self, page: Page, geo: str) -> List[TrendItem]:
        """Extract trend data directly from the page DOM."""
        
        # JavaScript to extract all trend data from the table
        trends_data = await page.evaluate("""
            () => {
                const trends = [];
                const rows = document.querySelectorAll('table tbody tr');
                
                rows.forEach((row, index) => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 4) {
                        // Cell 0: checkbox
                        // Cell 1: Title with trend info
                        // Cell 2: Search volume
                        // Cell 3: Started time
                        // Cell 4: Trend breakdown (optional)
                        
                        const titleCell = cells[1];
                        const volumeCell = cells[2];
                        const startedCell = cells[3];
                        
                        // Extract title
                        const titleText = titleCell.innerText.trim().split('\\n')[0];
                        
                        // Extract volume and growth
                        const volumeText = volumeCell.innerText.trim();
                        const volumeParts = volumeText.split('\\n');
                        const searchVolume = volumeParts[0] || '';
                        const growthPercent = volumeParts[1] || '';
                        
                        // Extract started time and duration
                        const startedText = startedCell.innerText.trim();
                        const startedParts = startedText.split('\\n');
                        const startedTime = startedParts[0] || '';
                        const duration = startedParts[1] || '';
                        
                        // Determine status from duration text
                        const status = duration.toLowerCase().includes('lasted') ? 'Ended' : 'Active';
                        
                        if (titleText) {
                            trends.push({
                                title: titleText,
                                rank: index + 1,
                                searchVolume: searchVolume,
                                growthPercent: growthPercent,
                                startedTime: startedTime,
                                duration: duration,
                                status: status
                            });
                        }
                    }
                });
                
                return trends;
            }
        """)
        
        # Convert to TrendItem objects
        items = []
        for data in trends_data:
            from .parser import normalize_title
            
            item = TrendItem(
                title=data["title"],
                normalized_title=normalize_title(data["title"]),
                rank=data["rank"],
                search_volume=data["searchVolume"],
                growth_percent=data["growthPercent"],
                started_time=data["startedTime"],
                status=data["status"],
                duration=data["duration"],
                geo=geo,
            )
            items.append(item)
        
        return items


# Global browser instance for reuse
_browser_fetcher: Optional[BrowserFetcher] = None


async def get_browser_fetcher() -> BrowserFetcher:
    """Get or create the global browser fetcher instance."""
    global _browser_fetcher
    if _browser_fetcher is None:
        _browser_fetcher = BrowserFetcher()
        await _browser_fetcher.initialize()
    return _browser_fetcher


async def close_browser_fetcher() -> None:
    """Close the global browser fetcher."""
    global _browser_fetcher
    if _browser_fetcher:
        await _browser_fetcher.close()
        _browser_fetcher = None
