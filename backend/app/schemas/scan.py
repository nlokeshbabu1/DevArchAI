"""Scan schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.validators import validate_branch, validate_repository_url


class ScanStatus(str, Enum):
    """Scan status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AIScanStatus(str, Enum):
    """AI suggestion generation status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanCreate(BaseModel):
    """Scan creation request."""

    repository_url: str = Field(..., description="GitHub repository URL to scan")
    branch: str | None = Field(default="main", description="Branch to analyze")
    commit_hash: str | None = Field(None, description="Specific commit to analyze")
    include_ai_explanations: bool = Field(default=True, description="Include AI explanations")

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, v: str) -> str:
        return validate_repository_url(v)

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_branch(v)

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
    user_id: str | None  # UUID as string, can be null
    repository_id: str | None  # UUID as string, can be null
    repository_url: str
    branch: str
    commit_hash: str | None
    status: ScanStatus
    scan_status: ScanStatus
    ai_status: AIScanStatus = AIScanStatus.PENDING
    progress: int
    error_message: str | None
    overall_score: float | None
    security_score: float | None
    scalability_score: float | None
    reliability_score: float | None
    cost_score: float | None
    observability_score: float | None
    detected_stack: dict | None = None  # Detected technology stack
    detected_technologies: list[str] | None = None  # List of detected tech names
    files_analyzed: int | None = None  # Number of files analyzed
    findings_count: int | None = None  # Number of findings
    started_at: datetime | None
    completed_at: datetime | None
    analysis_duration_seconds: float | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator('id', 'user_id', 'repository_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID objects to strings."""
        if v is None:
            return None
        if isinstance(v, UUID):
            return str(v)
        return v


class ScanListResponse(BaseModel):
    """Scan list response."""

    scans: list[ScanResponse]
    total: int
    page: int
    page_size: int


class ScanProgressResponse(BaseModel):
    """Scan progress response."""

    id: str
    status: ScanStatus
    progress: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID objects to strings."""
        if isinstance(v, UUID):
            return str(v)
        return v


class ScanCancelResponse(BaseModel):
    """Scan cancellation response."""

    id: str
    status: str
    message: str

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID objects to strings."""
        if isinstance(v, UUID):
            return str(v)
        return v
