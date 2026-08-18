"""AI Suggestion schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AISuggestionBase(BaseModel):
    """Base schema for AI suggestion."""

    title: str
    description: str
    severity: str  # critical, high, medium, low, info
    confidence: float = Field(ge=0.0, le=1.0, default=0.9)
    category: str  # security, reliability, cost, etc.
    fix_type: str  # terraform, dockerfile, kubernetes, ci_cd, general
    file_path: str
    line_number: int | None = None
    fix_code: str | None = None
    auto_fix_available: bool = False
    metadata: dict[str, Any] | None = None


class AISuggestionCreate(AISuggestionBase):
    """Schema for creating AI suggestion."""

    finding_id: str
    scan_id: str


class AISuggestionUpdate(BaseModel):
    """Schema for updating AI suggestion."""

    status: str | None = None
    pr_url: str | None = None
    pr_number: int | None = None
    metadata: dict[str, Any] | None = None


class AISuggestionResponse(AISuggestionBase):
    """Schema for AI suggestion response."""

    id: str
    finding_id: str
    scan_id: str
    status: str
    applied_at: datetime | None = None
    pr_url: str | None = None
    pr_number: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AISuggestionListResponse(BaseModel):
    """Schema for list of AI suggestions."""

    suggestions: list[AISuggestionResponse]
    total: int
    status_filter: str | None = None


class ApplyFixRequest(BaseModel):
    """Request to apply fix."""

    dry_run: bool = False


class ApplyFixResponse(BaseModel):
    """Response after applying fix."""

    success: bool
    message: str
    file_path: str
    backup_path: str | None = None


class CreatePRRequest(BaseModel):
    """Request to create GitHub PR."""

    branch_name: str | None = None
    pr_title: str | None = None
    pr_description: str | None = None


class CreatePRResponse(BaseModel):
    """Response after creating PR."""

    success: bool
    pr_url: str
    pr_number: int
    branch_name: str
    message: str
