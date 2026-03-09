"""Scan schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class ScanStatus(str, Enum):
    """Scan status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanCreate(BaseModel):
    """Scan creation request."""

    repository_url: str = Field(..., description="GitHub repository URL to scan")
    branch: Optional[str] = Field(default="main", description="Branch to analyze")
    commit_hash: Optional[str] = Field(None, description="Specific commit to analyze")
    include_ai_explanations: bool = Field(default=True, description="Include AI explanations")

    class Config:
        json_schema_extra = {
            "example": {
                "repository_url": "https://github.com/example/infrastructure",
                "branch": "main",
                "include_ai_explanations": True,
            }
        }


class ScanResponse(BaseModel):
    """Scan response."""

    id: str  # UUID as string
    user_id: Optional[str]  # UUID as string, can be null
    repository_id: Optional[str]  # UUID as string, can be null
    repository_url: str
    branch: str
    commit_hash: Optional[str]
    status: ScanStatus
    progress: int
    error_message: Optional[str]
    overall_score: Optional[float]
    security_score: Optional[float]
    scalability_score: Optional[float]
    reliability_score: Optional[float]
    cost_score: Optional[float]
    observability_score: Optional[float]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    analysis_duration_seconds: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanListResponse(BaseModel):
    """Scan list response."""

    scans: List[ScanResponse]
    total: int
    page: int
    page_size: int


class ScanProgressResponse(BaseModel):
    """Scan progress response."""

    id: str
    status: ScanStatus
    progress: int
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class ScanCancelResponse(BaseModel):
    """Scan cancellation response."""

    id: str
    status: str
    message: str
