"""Repository schemas."""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


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

    class Config:
        from_attributes = True


class RepositoryListResponse(BaseModel):
    """Repository list response."""

    repositories: List[RepositoryResponse]
    total: int
    page: int
    page_size: int
