"""Pydantic data models for trends."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TrendItem(BaseModel):
    """A single trend item from Google Trends."""

    title: str = Field(..., description="Trend title/keyword")
    normalized_title: str = Field(default="", description="Normalized title for deduplication")
    rank: int = Field(default=0, description="Position in the trends list")
    search_volume: str = Field(default="", description="Search volume (e.g., '500+', '2K+')")
    growth_percent: str = Field(default="", description="Growth percentage (e.g., '+200%')")
    started_time: str = Field(default="", description="When trend started (e.g., '3 hours ago')")
    status: str = Field(default="Active", description="Trend status (Active/Ended)")
    duration: str = Field(default="", description="How long it lasted (e.g., 'Lasted 2 hrs')")
    geo: str = Field(..., description="Geographic region code (US, GB, ID)")
    related_queries: List[str] = Field(default_factory=list, description="Related search queries")
    articles: List[dict] = Field(default_factory=list, description="Related news articles")


class TrendEvent(BaseModel):
    """A trend event stored in the database."""

    id: Optional[int] = None
    geo: str
    title: str
    normalized_title: str
    rank: int
    search_volume: str
    growth_percent: str
    started_time: str
    status: str
    duration: str
    raw_payload: str = Field(default="", description="Raw JSON payload for auditing")
    fetched_at: datetime
    created_at: Optional[datetime] = None


class DedupeKey(BaseModel):
    """Deduplication key record."""

    id: Optional[int] = None
    geo: str
    date_key: str  # YYYY-MM-DD
    normalized_title: str
    created_at: Optional[datetime] = None
    expires_at: datetime


class PollResult(BaseModel):
    """Result of a polling operation."""

    geo: str
    success: bool
    trends_count: int = 0
    new_trends_count: int = 0
    error: Optional[str] = None
    fetched_at: datetime
