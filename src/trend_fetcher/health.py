"""FastAPI health check server."""

from fastapi import FastAPI
from datetime import datetime
import logging

from .config import settings
from .database import db

logger = logging.getLogger(__name__)

app = FastAPI(title="Google Trends Gaming Alert", version="1.0.0")

# Track system state
_start_time = datetime.now()
_last_poll_times: dict[str, datetime] = {}
_poll_errors: dict[str, str] = {}


def update_last_poll(geo: str, success: bool, error: str = None):
    """Update the last poll time for a geo."""
    _last_poll_times[geo] = datetime.now()
    if error:
        _poll_errors[geo] = error
    elif geo in _poll_errors:
        del _poll_errors[geo]


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Google Trends Gaming Alert",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/healthz")
async def healthcheck():
    """Health check endpoint for container orchestration."""
    uptime_seconds = (datetime.now() - _start_time).total_seconds()

    # Check database connectivity
    db_healthy = True
    try:
        await db.get_stats()
    except Exception as e:
        db_healthy = False
        logger.error(f"Database health check failed: {e}")

    # Determine overall health
    is_healthy = db_healthy and len(_poll_errors) < len(settings.geo_list)

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "uptime_seconds": int(uptime_seconds),
        "database": "connected" if db_healthy else "disconnected",
        "last_polls": {
            geo: time.isoformat() for geo, time in _last_poll_times.items()
        },
        "errors": _poll_errors if _poll_errors else None,
        "geos_monitored": settings.geo_list,
    }


@app.get("/stats")
async def stats():
    """Get system statistics."""
    try:
        db_stats = await db.get_stats()
    except Exception as e:
        db_stats = {"error": str(e)}

    return {
        "uptime_seconds": int((datetime.now() - _start_time).total_seconds()),
        "geos": settings.geo_list,
        "poll_interval": f"{settings.poll_interval_min}-{settings.poll_interval_max}s",
        "last_polls": {
            geo: time.isoformat() for geo, time in _last_poll_times.items()
        },
        "database": db_stats,
    }


@app.get("/ready")
async def readiness():
    """Readiness probe for Kubernetes."""
    try:
        await db.get_stats()
        return {"ready": True}
    except Exception:
        return {"ready": False}
