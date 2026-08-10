"""Repository ("project") API calls.

The backend models projects as *repositories* under ``/api/v1/repositories``;
the CLI exposes them under ``devsec project``.
"""

from __future__ import annotations

from devsec.api.client import ApiClient
from devsec.models.project import Project, ProjectCreate, ProjectList
from devsec.utils.errors import UsageError


def list_projects(
    client: ApiClient,
    *,
    page: int = 1,
    page_size: int = 20,
) -> ProjectList:
    """List the user's projects (backend repositories)."""
    payload = client.get_json(
        "/repositories",
        params={"page": page, "page_size": page_size},
    )
    return ProjectList.from_response(payload)


def get_project(client: ApiClient, project_id: str) -> Project:
    """Fetch a single project by ID (backend repository ID)."""
    if not project_id.strip():
        raise UsageError("Project ID cannot be empty.")
    payload = client.get_json(f"/repositories/{project_id.strip()}")
    return Project.model_validate(payload)


def create_project(
    client: ApiClient,
    url: str,
    name: str | None = None,
) -> Project:
    """Register a repository URL as a project to track."""
    url = url.strip()
    if not url:
        raise UsageError("Repository URL cannot be empty.")
    payload = client.post_json(
        "/repositories",
        payload=ProjectCreate(url=url, name=name).model_dump(exclude_none=True),
    )
    return Project.model_validate(payload)
