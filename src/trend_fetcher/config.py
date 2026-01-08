"""Configuration settings using Pydantic."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Discord
    discord_webhook_url: str = Field(..., description="Discord webhook URL for notifications")

    # Polling
    poll_interval_min: int = Field(default=60, description="Minimum polling interval in seconds")
    poll_interval_max: int = Field(default=120, description="Maximum polling interval in seconds")

    # Google Trends
    geos: str = Field(default="US,GB,ID", description="Comma-separated geo codes")
    category_id: int = Field(default=6, description="Google Trends category ID (6=Games)")
    hours: int = Field(default=24, description="Time window in hours")

    # Database
    database_path: str = Field(default="./data/trends.db", description="SQLite database path")

    # Deduplication
    dedupe_ttl_hours: int = Field(default=48, description="Hours to keep dedupe records")

    # Timezone
    timezone: str = Field(default="Asia/Jakarta", description="Default timezone")

    # Health check
    health_port: int = Field(default=8080, description="Health check server port")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")

    @property
    def geo_list(self) -> List[str]:
        """Parse geo codes into list."""
        return [g.strip().upper() for g in self.geos.split(",") if g.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
