"""Repository schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RepositoryCreate(BaseModel):
    """Repository creation request."""

    url: str = Field(..., description="GitHub repository URL")
    name: str | None = Field(None, description="Repository name (auto-detected if not provided)")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://github.com/example/infrastructure",
                "name": "example/infrastructure",
            }
        }


class RepositoryUpdate(BaseModel):
    """Repository update request."""

    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=1000)
    is_active: bool | None = None


class RepositoryResponse(BaseModel):
    """Repository response."""

    id: UUID
    user_id: UUID
    name: str
    full_name: str | None
    url: str
    description: str | None
    default_branch: str
    is_private: bool
    is_active: bool
    last_analyzed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    scan_count: int = 0
    # Enhanced fields for UI
    last_scan_at: datetime | None = None
    scan_status: str | None = None
    overall_score: float | None = None
    tech_stack: list[str] = Field(default_factory=list)
    issues: dict[str, int] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class RepositoryListResponse(BaseModel):
    """Repository list response."""

    repositories: list[RepositoryResponse]
    total: int
    page: int
    page_size: int
