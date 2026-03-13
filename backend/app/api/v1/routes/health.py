"""Health check routes."""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.common import HealthResponse, HealthStatus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.

    Returns service status and version information.
    """
    services = {
        "api": "up",
        "database": "pending",
        "cache": "pending",
    }

    overall_status = HealthStatus.HEALTHY

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        services["database"] = "up"
    except Exception as e:
        services["database"] = "down"
        overall_status = HealthStatus.DEGRADED
        logger.warning("Database health check failed", error=str(e))

    # Check Redis (if configured)
    try:
        from app.config import settings
        if settings.REDIS_URL:
            import redis.asyncio as redis
            r = redis.from_url(settings.REDIS_URL)
            await r.ping()
            services["cache"] = "up"
            await r.close()
        else:
            services["cache"] = "not_configured"
    except Exception as e:
        services["cache"] = "down"
        overall_status = HealthStatus.DEGRADED
        logger.warning("Cache health check failed", error=str(e))

    return HealthResponse(
        status=overall_status,
        version=settings.VERSION,
        timestamp=datetime.utcnow(),
        services=services,
    )


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check for Kubernetes."""
    try:
        # Check if database is accessible
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "checks": {"database": "ok"}}
    except Exception:
        return {"status": "not_ready", "checks": {"database": "failed"}}


@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {"status": "alive"}
