"""Common schemas and shared types."""

from datetime import datetime
from enum import Enum
from typing import TypeVar

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthResponse(BaseModel):
    """Health check response."""

    status: HealthStatus
    version: str
    timestamp: datetime
    services: dict


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Base paginated response."""

    total: int
    page: int
    page_size: int
    total_pages: int


T = TypeVar("T")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response."""

    error: dict


class BulkOperationResponse(BaseModel):
    """Bulk operation response."""

    success_count: int
    failure_count: int
    errors: list[dict] | None = None
