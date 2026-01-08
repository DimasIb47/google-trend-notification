"""Main entry point - async orchestration of polling, notifications, and health server."""

import asyncio
import logging
import random
import signal
import sys
from datetime import datetime
from typing import Optional

import uvicorn

from .config import settings
from .database import db
from .fetcher import get_browser_fetcher, close_browser_fetcher
from .deduplicator import is_new_trend, cleanup_expired
from .discord import send_discord_notification, send_test_notification
from .health import app as health_app, update_last_poll

# Configure structured JSON logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger(__name__)

# Shutdown flag
_shutdown = asyncio.Event()


async def poll_geo(geo: str) -> None:
    """
    Poll a single geo for new trends.
    
    This runs in a loop until shutdown is signaled.
    """
    logger.info(f"Starting polling for {geo}")
    
    # Get shared browser fetcher
    fetcher = await get_browser_fetcher()

    while not _shutdown.is_set():
        success = False
        error_msg = None
        new_count = 0
        total_count = 0

        try:
            # Fetch trends using browser
            success, trends, error = await fetcher.fetch_trends(geo)
            total_count = len(trends)

            if success:
                # Process each trend
                for trend in trends:
                    try:
                        # Check if new (atomic dedup)
                        is_new = await is_new_trend(trend)

                        if is_new:
                            new_count += 1
                            logger.info(
                                f"New trend detected: {trend.title} ({geo}) - "
                                f"Volume: {trend.search_volume}, Started: {trend.started_time}"
                            )

                            # Store in database
                            await db.insert_trend_event(trend)

                            # Send Discord notification
                            await send_discord_notification(trend)

                    except Exception as e:
                        logger.error(f"Error processing trend '{trend.title}': {e}")

                logger.info(
                    f"Poll completed for {geo}: {total_count} trends, {new_count} new"
                )
            else:
                error_msg = error or "Unknown fetch error"
                logger.error(f"Failed to fetch trends for {geo}: {error_msg}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Poll error for {geo}: {e}")

        # Update health status
        update_last_poll(geo, success, error_msg)

        # Random jitter sleep
        if not _shutdown.is_set():
            sleep_time = random.uniform(
                settings.poll_interval_min, settings.poll_interval_max
            )
            logger.debug(f"Sleeping {sleep_time:.1f}s before next poll for {geo}")

            try:
                await asyncio.wait_for(_shutdown.wait(), timeout=sleep_time)
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue polling


async def cleanup_task() -> None:
    """Periodic cleanup of expired dedupe keys."""
    while not _shutdown.is_set():
        try:
            await cleanup_expired()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

        # Run cleanup every hour
        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=3600)
        except asyncio.TimeoutError:
            pass


async def run_health_server() -> None:
    """Run the FastAPI health server."""
    config = uvicorn.Config(
        health_app,
        host="0.0.0.0",
        port=settings.health_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    except asyncio.CancelledError:
        pass


def handle_shutdown(sig, frame):
    """Signal handler for graceful shutdown."""
    logger.info(f"Received signal {sig}, initiating shutdown...")
    _shutdown.set()


async def main() -> None:
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Google Trends Gaming Alert System starting...")
    logger.info(f"Monitoring geos: {settings.geo_list}")
    logger.info(f"Category: {settings.category_id} (Games)")
    logger.info(f"Time window: {settings.hours} hours")
    logger.info(f"Poll interval: {settings.poll_interval_min}-{settings.poll_interval_max}s")
    logger.info("Using Playwright headless browser for accurate data fetching")
    logger.info("=" * 60)

    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Initialize database
    await db.connect()

    # Initialize browser
    fetcher = await get_browser_fetcher()

    # Send test notification on startup
    logger.info("Sending startup notification to Discord...")
    await send_test_notification()

    # Create tasks
    tasks = []

    # Health server
    health_task = asyncio.create_task(run_health_server())
    tasks.append(health_task)

    # Polling tasks for each geo (sequential polling to reduce browser load)
    for geo in settings.geo_list:
        poll_task = asyncio.create_task(poll_geo(geo))
        tasks.append(poll_task)

    # Cleanup task
    cleanup = asyncio.create_task(cleanup_task())
    tasks.append(cleanup)

    logger.info(f"Started {len(tasks)} tasks (health + {len(settings.geo_list)} polls + cleanup)")

    # Wait for shutdown signal
    await _shutdown.wait()

    logger.info("Shutting down...")

    # Cancel all tasks
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    # Close browser and database
    await close_browser_fetcher()
    await db.close()

    logger.info("Shutdown complete")


def run():
    """Entry point for running the application."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    run()
