"""SQLite database layer with WAL mode."""

import aiosqlite
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import json
import logging

from .config import settings
from .models import TrendItem, TrendEvent, DedupeKey

logger = logging.getLogger(__name__)


class Database:
    """Async SQLite database manager."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.database_path
        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Initialize database connection and create tables."""
        # Ensure directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(self.db_path)

        # Enable WAL mode for better concurrency
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA synchronous=NORMAL")

        await self._create_tables()
        logger.info(f"Database connected: {self.db_path}")

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        async with self._lock:
            # Trends events table (append-only log)
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS trends_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    geo TEXT NOT NULL,
                    title TEXT NOT NULL,
                    normalized_title TEXT NOT NULL,
                    rank INTEGER,
                    search_volume TEXT,
                    growth_percent TEXT,
                    started_time TEXT,
                    status TEXT,
                    duration TEXT,
                    raw_payload TEXT,
                    fetched_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Deduplication keys table
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS dedupe_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    geo TEXT NOT NULL,
                    date_key TEXT NOT NULL,
                    normalized_title TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT NOT NULL,
                    UNIQUE(geo, date_key, normalized_title)
                )
            """)

            # Create indexes
            await self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_dedupe_lookup 
                ON dedupe_keys(geo, date_key, normalized_title)
            """)
            await self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_dedupe_expires 
                ON dedupe_keys(expires_at)
            """)
            await self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_trends_geo_date 
                ON trends_events(geo, fetched_at)
            """)

            await self._connection.commit()
            logger.info("Database tables created/verified")

    async def insert_trend_event(self, trend: TrendItem, raw_payload: str = "") -> int:
        """Insert a trend event and return the ID."""
        async with self._lock:
            cursor = await self._connection.execute(
                """
                INSERT INTO trends_events 
                (geo, title, normalized_title, rank, search_volume, growth_percent, 
                 started_time, status, duration, raw_payload, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trend.geo,
                    trend.title,
                    trend.normalized_title,
                    trend.rank,
                    trend.search_volume,
                    trend.growth_percent,
                    trend.started_time,
                    trend.status,
                    trend.duration,
                    raw_payload,
                    datetime.now().isoformat(),
                ),
            )
            await self._connection.commit()
            return cursor.lastrowid

    async def check_and_insert_dedupe(
        self, geo: str, date_key: str, normalized_title: str
    ) -> bool:
        """
        Atomically check if a dedupe key exists and insert if not.
        Returns True if this is a NEW trend (not seen before today).
        Returns False if duplicate (already seen today).
        """
        expires_at = datetime.now() + timedelta(hours=settings.dedupe_ttl_hours)

        async with self._lock:
            try:
                await self._connection.execute(
                    """
                    INSERT INTO dedupe_keys (geo, date_key, normalized_title, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (geo, date_key, normalized_title, expires_at.isoformat()),
                )
                await self._connection.commit()
                logger.debug(f"New dedupe key: {geo}/{date_key}/{normalized_title[:30]}")
                return True  # New trend
            except aiosqlite.IntegrityError:
                # Duplicate - already exists
                logger.debug(f"Duplicate trend: {geo}/{date_key}/{normalized_title[:30]}")
                return False

    async def cleanup_expired_dedupe_keys(self) -> int:
        """Remove expired dedupe keys. Returns count of deleted rows."""
        async with self._lock:
            now = datetime.now().isoformat()
            cursor = await self._connection.execute(
                "DELETE FROM dedupe_keys WHERE expires_at < ?", (now,)
            )
            await self._connection.commit()
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired dedupe keys")
            return deleted

    async def get_recent_trends(self, geo: str, limit: int = 50) -> List[dict]:
        """Get recent trends for a geo."""
        async with self._lock:
            cursor = await self._connection.execute(
                """
                SELECT * FROM trends_events 
                WHERE geo = ? 
                ORDER BY fetched_at DESC 
                LIMIT ?
                """,
                (geo, limit),
            )
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    async def get_stats(self) -> dict:
        """Get database statistics."""
        async with self._lock:
            stats = {}

            # Total events
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM trends_events"
            )
            stats["total_events"] = (await cursor.fetchone())[0]

            # Active dedupe keys
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM dedupe_keys WHERE expires_at > ?",
                (datetime.now().isoformat(),),
            )
            stats["active_dedupe_keys"] = (await cursor.fetchone())[0]

            # Events by geo
            cursor = await self._connection.execute(
                "SELECT geo, COUNT(*) FROM trends_events GROUP BY geo"
            )
            stats["events_by_geo"] = dict(await cursor.fetchall())

            return stats


# Global database instance
db = Database()
