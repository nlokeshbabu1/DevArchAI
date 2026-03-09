"""Common schemas used across the API."""

from pydantic import BaseModel, Field
from typing import List, Optional, Generic, TypeVar
from datetime import datetime

T = TypeVar("T")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: str
    environment: str
    services: dict


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
