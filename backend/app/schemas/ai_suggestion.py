"""AI Suggestion schemas."""

from datetime import datetime
from typing import Any, Dict, Optional

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
    line_number: Optional[int] = None
    fix_code: Optional[str] = None
    auto_fix_available: bool = False
    metadata: Optional[Dict[str, Any]] = None


class AISuggestionCreate(AISuggestionBase):
    """Schema for creating AI suggestion."""

    finding_id: str
    scan_id: str


class AISuggestionUpdate(BaseModel):
    """Schema for updating AI suggestion."""

    status: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class AISuggestionResponse(AISuggestionBase):
    """Schema for AI suggestion response."""

    id: str
    finding_id: str
    scan_id: str
    status: str
    applied_at: Optional[datetime] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AISuggestionListResponse(BaseModel):
    """Schema for list of AI suggestions."""

    suggestions: list[AISuggestionResponse]
    total: int
    status_filter: Optional[str] = None


class ApplyFixRequest(BaseModel):
    """Request to apply fix."""

    dry_run: bool = False


class ApplyFixResponse(BaseModel):
    """Response after applying fix."""

    success: bool
    message: str
    file_path: str
    backup_path: Optional[str] = None


class CreatePRRequest(BaseModel):
    """Request to create GitHub PR."""

    branch_name: Optional[str] = None
    pr_title: Optional[str] = None
    pr_description: Optional[str] = None


class CreatePRResponse(BaseModel):
    """Response after creating PR."""

    success: bool
    pr_url: str
    pr_number: int
    branch_name: str
    message: str
