"""Repository schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class RepositoryCreate(BaseModel):
    """Repository creation request."""

    url: str = Field(..., description="GitHub repository URL")
    name: Optional[str] = Field(None, description="Repository name (auto-detected if not provided)")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://github.com/example/infrastructure",
                "name": "example/infrastructure",
            }
        }


class RepositoryUpdate(BaseModel):
    """Repository update request."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class RepositoryResponse(BaseModel):
    """Repository response."""

    id: int
    user_id: int
    name: str
    full_name: Optional[str]
    url: str
    description: Optional[str]
    default_branch: str
    is_private: bool
    is_active: bool
    last_analyzed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    scan_count: int = 0
    # Enhanced fields for UI
    last_scan_at: Optional[datetime] = None
    scan_status: Optional[str] = None
    overall_score: Optional[float] = None
    tech_stack: List[str] = Field(default_factory=list)
    issues: Dict[str, int] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class RepositoryListResponse(BaseModel):
    """Repository list response."""

    repositories: list[RepositoryResponse]
    total: int
    page: int
    page_size: int
