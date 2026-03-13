"""Health check endpoints."""

from datetime import datetime

import redis.asyncio as redis
from devarchai import __version__
from devarchai.api.deps import get_db
from devarchai.config import settings
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check.

    Checks database and cache connectivity.
    """
    health_status = {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "services": {},
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = "unhealthy"
        health_status["services"]["database_error"] = str(e)
        health_status["status"] = "degraded"

    # Check Redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        health_status["services"]["cache"] = "healthy"
        await redis_client.close()
    except Exception as e:
        health_status["services"]["cache"] = "unhealthy"
        health_status["services"]["cache_error"] = str(e)
        health_status["status"] = "degraded"

    # Determine status code
    status_code = status.HTTP_200_OK
    if health_status["status"] == "degraded":
        status_code = status.HTTP_207_MULTI_STATUS

    return health_status


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes.

    Returns 200 when the application is ready to serve traffic.
    """
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """
    Liveness check for Kubernetes.

    Returns 200 when the application is alive.
    """
    return {"status": "alive"}
