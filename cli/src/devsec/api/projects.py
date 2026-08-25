"""Repository ("project") API calls.

The backend models projects as *repositories* under ``/api/v1/repositories``;
the CLI exposes them under ``devsec project``.
"""

from __future__ import annotations

import uuid

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
    """Fetch a single project by full UUID (backend repository ID)."""
    if not project_id.strip():
        raise UsageError("Project ID cannot be empty.")
    payload = client.get_json(f"/repositories/{project_id.strip()}")
    return Project.model_validate(payload)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def resolve_project(
    client: ApiClient,
    project_id: str | None,
    *,
    auto_single: bool = False,
) -> Project:
    """Resolve a project by full UUID, unique ID prefix, or auto-select when alone."""
    needle = (project_id or "").strip()
    if needle and _is_uuid(needle):
        return get_project(client, needle)

    listing = list_projects(client, page_size=100)
    projects = listing.projects

    if not needle:
        if auto_single and len(projects) == 1:
            return projects[0]
        raise UsageError(
            "No project selected.",
            hint='Run "devsec project select <id>" or pass --project <id>. '
            'Use "devsec project list --json" for full IDs.',
        )

    prefix = needle.lower()
    matches = [project for project in projects if project.id.lower().startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        ids = ", ".join(project.id for project in matches[:3])
        raise UsageError(
            f"Ambiguous project ID prefix: {needle}",
            hint=f"Multiple projects match. Use a longer prefix or full UUID. Matches: {ids}",
        )
    raise UsageError(
        f"No project matches ID prefix: {needle}",
        hint='Run "devsec project list --json" to see available project IDs.',
    )


def resolve_project_for_command(
    client: ApiClient,
    project_id: str | None,
    *,
    selected_project: str | None = None,
    auto_single: bool = False,
) -> Project:
    """Resolve explicit ID, configured selection, or (optionally) the only project."""
    explicit = (project_id or selected_project or "").strip()
    if explicit:
        return resolve_project(client, explicit)
    return resolve_project(client, None, auto_single=auto_single)


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
