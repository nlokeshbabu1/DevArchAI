"""Pull Request schemas for API validation."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PRStatus(str, Enum):
    """Pull Request status."""

    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"
    DRAFT = "draft"


class CreatePRRequest(BaseModel):
    """Request body for creating a Pull Request."""

    scan_id: str = Field(..., description="Scan ID containing findings to fix")
    finding_ids: list[str] | None = Field(
        default=None,
        description="List of finding IDs to fix (defaults to all critical+high if not provided)"
    )
    branch_name: str | None = Field(
        default=None,
        description="Custom branch name (auto-generated if not provided)"
    )
    pr_title: str | None = Field(
        default=None,
        description="Custom PR title (auto-generated if not provided)"
    )
    pr_description: str | None = Field(
        default=None,
        description="Custom PR description (auto-generated if not provided)"
    )
    is_draft: bool = Field(
        default=False,
        description="Create PR as draft (won't trigger CI checks)"
    )
    atomic_mode: bool = Field(
        default=True,
        description="When true (default), all selected findings must produce validated patches or the PR is not created",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "scan_id": "550e8400-e29b-41d4-a716-446655440000",
                "finding_ids": ["finding-uuid-1", "finding-uuid-2"],
                "is_draft": False
            }
        }


class CreatePRResponse(BaseModel):
    """Response body for successful PR creation."""

    pr_id: str
    scan_id: str
    github_pr_number: int
    github_pr_url: str
    branch_name: str
    title: str
    status: PRStatus
    findings_fixed: list[str]
    score_before: float | None
    score_after: float | None
    created_at: datetime
    remediation_report: dict | None = Field(
        default=None,
        description="Structured remediation outcomes, validation, and discovery metadata",
    )

    @field_validator('pr_id', 'scan_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is None:
            return None
        if isinstance(v, UUID):
            return str(v)
        return v


class PRListResponse(BaseModel):
    """Response body for listing PRs."""

    prs: list[dict]
    total: int

    class Config:
        from_attributes = True
