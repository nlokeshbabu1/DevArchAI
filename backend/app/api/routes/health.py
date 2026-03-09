"""
Health Check Routes
"""

from fastapi import APIRouter
from datetime import datetime
from app.config import settings
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns service status and version information.
    """
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        timestamp=datetime.utcnow(),
        services={
            "api": "up",
            "database": "pending",
            "cache": "pending",
        },
    )


@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes."""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {"status": "alive"}
