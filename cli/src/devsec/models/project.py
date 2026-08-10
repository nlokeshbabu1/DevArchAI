"""Project (backend repository) models.

The backend models projects as *repositories* under ``/api/v1/repositories``.
These Pydantic models map that API surface onto the CLI's ``devsec project``
commands while remaining tolerant of extra backend fields.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Project(BaseModel):
    """A project as returned by the backend repositories API."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    full_name: str | None = None
    url: str
    description: str | None = None
    default_branch: str = "main"
    is_private: bool = False
    is_active: bool = True
    scan_count: int = 0
    last_scan_at: datetime | None = None
    scan_status: str | None = None
    overall_score: float | None = None
    tech_stack: list[str] = Field(default_factory=list)
    issues: dict[str, int] = Field(default_factory=dict)


class ProjectCreate(BaseModel):
    """Payload for creating a project (backend repository)."""

    url: str
    name: str | None = None


class ProjectList(BaseModel):
    """Paginated project list response."""

    projects: list[Project]
    total: int = 0
    page: int = 1
    page_size: int = 20

    @classmethod
    def from_response(cls, payload: dict) -> ProjectList:
        return cls(
            projects=[Project.model_validate(item) for item in payload.get("repositories", [])],
            total=payload.get("total", 0),
            page=payload.get("page", 1),
            page_size=payload.get("page_size", 20),
        )
