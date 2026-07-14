"""GitLab API routes for project operations."""

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.repository import Repository
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/gitlab", tags=["GitLab"])


def _extract_gitlab_project_path(repo_url: str) -> str:
    """Extract the project path (url-encoded) from a GitLab repository URL.

    Supports:
      - https://gitlab.com/owner/repo
      - https://gitlab.com/group/subgroup/repo
      - https://gitlab.com/owner/repo.git
      - https://self-hosted.example.com/owner/repo
    """
    from urllib.parse import quote

    gitlab_host = settings.GITLAB_URL.rstrip("/").replace("https://", "").replace("http://", "")
    url = repo_url.rstrip("/").replace(".git", "")

    # Strip protocol + host
    for prefix in [f"https://{gitlab_host}/", f"http://{gitlab_host}/"]:
        if url.startswith(prefix):
            path = url[len(prefix):]
            break
    else:
        raise ValueError("URL does not match configured GitLab host")

    # URL-encode each path segment (GitLab requires full path encoding)
    parts = [quote(p, safe="") for p in path.split("/") if p]
    if not parts:
        raise ValueError("No project path found in URL")
    return "/".join(parts)


@router.get("/branches")
async def get_gitlab_branches(repo_url: str):
    """Get list of branches for a GitLab repository."""
    try:
        project_path = _extract_gitlab_project_path(repo_url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    logger.info("Fetching GitLab branches", repo_url=repo_url, project_path=project_path)

    gitlab_url = settings.GITLAB_URL.rstrip("/")
    api_url = f"{gitlab_url}/api/v4/projects/{project_path}/repository/branches"
    params = {"per_page": 50, "order_by": "name", "sort": "asc"}

    headers = {"Accept": "application/json"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, params=params, timeout=10.0)

            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found on GitLab",
                )

            if response.status_code != 200:
                logger.warning("GitLab branches API error", status=response.status_code, body=response.text[:200])
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GitLab API returned status {response.status_code}",
                )

            branches_data = response.json()

            branches = [
                {
                    "name": b["name"],
                    "protected": b.get("protected", False),
                    "commit_sha": b.get("commit", {}).get("id", ""),
                }
                for b in branches_data
            ]

            # Sort: main/master first, then alphabetically
            branches.sort(key=lambda b: (b["name"] not in ["main", "master"], b["name"]))

            default_branch = branches[0]["name"] if branches else "main"

            logger.info(
                "GitLab branches fetched",
                count=len(branches),
                default=default_branch,
            )

            return {"branches": branches, "default_branch": default_branch}

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="GitLab API timeout",
        )
    except httpx.RequestError as e:
        logger.error("GitLab branches request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch branches: {str(e)}",
        )


@router.get("/projects")
async def get_user_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all projects for the authenticated GitLab user."""
    if not current_user.gitlab_access_token:
        logger.warning("No GitLab token for user", user_id=current_user.id)
        return {
            "gitlab_connected": False,
            "gitlab_projects": [],
            "message": "Connect GitLab to import projects",
        }

    logger.info(
        "Fetching user projects from GitLab",
        user_id=current_user.id,
        gitlab_username=current_user.gitlab_username,
        has_token=bool(current_user.gitlab_access_token),
    )

    gitlab_url = settings.GITLAB_URL.rstrip("/")
    api_url = f"{gitlab_url}/api/v4/projects?per_page=100&order_by=updated_at&sort=desc&membership=true"

    headers = {
        "Authorization": f"Bearer {current_user.gitlab_access_token}",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=15.0)

            if response.status_code == 401:
                logger.warning("GitLab token expired", user_id=current_user.id)
                return {
                    "gitlab_connected": False,
                    "gitlab_projects": [],
                    "message": "GitLab token expired. Please reconnect.",
                }

            if response.status_code != 200:
                logger.error("GitLab API error", status=response.status_code)
                return {
                    "gitlab_connected": True,
                    "gitlab_projects": [],
                    "message": "Failed to fetch projects from GitLab",
                }

            gl_projects = response.json()

            logger.info(
                "GitLab API response received",
                user_id=current_user.id,
                status_code=response.status_code,
                raw_count=len(gl_projects),
                first_project=gl_projects[0].get("path_with_namespace") if gl_projects else None,
                first_project_id=gl_projects[0].get("id") if gl_projects else None,
            )

            transformed_projects = [
                {
                    "id": f"gitlab_{proj['id']}",
                    "name": proj["path_with_namespace"],
                    "url": proj["web_url"],
                    "description": proj.get("description", "") or "",
                    "default_branch": proj.get("default_branch", "main"),
                    "is_private": proj.get("visibility", "public") != "public",
                    "language": proj.get("language", "") or proj.get("programming_language", "") or "",
                    "stargazers_count": proj.get("star_count", 0),
                    "forks_count": proj.get("forks_count", 0),
                    "updated_at": proj.get("last_activity_at", ""),
                    "source": "gitlab",
                    "scan_count": 0,
                    "last_scan_at": None,
                    "scan_status": "pending",
                    "overall_score": None,
                    "tech_stack": [],
                    "issues": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                }
                for proj in gl_projects
                if not proj.get("archived", False)
            ]

            logger.info(
                "GitLab projects fetched",
                user_id=current_user.id,
                count=len(transformed_projects),
            )

            return {
                "gitlab_connected": True,
                "gitlab_projects": transformed_projects,
                "total": len(transformed_projects),
            }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="GitLab API timeout",
        )
    except httpx.RequestError as e:
        logger.error("GitLab API request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {str(e)}",
        )


@router.post("/import-projects")
async def import_gitlab_projects(
    project_ids: list[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import selected GitLab projects to user's repository list."""
    if not current_user.gitlab_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitLab not connected. Please login via GitLab first.",
        )

    if not project_ids:
        return {"imported": [], "message": "No projects selected"}

    logger.info("Importing GitLab projects", user_id=current_user.id, count=len(project_ids))

    gitlab_url = settings.GITLAB_URL.rstrip("/")
    imported_projects = []

    for project_id in project_ids:
        api_url = f"{gitlab_url}/api/v4/projects/{project_id}"
        headers = {
            "Authorization": f"Bearer {current_user.gitlab_access_token}",
            "Accept": "application/json",
        }

        logger.info(
            "Fetching GitLab project for import",
            user_id=current_user.id,
            project_id=project_id,
            api_url=api_url,
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, headers=headers, timeout=10.0)

                if response.status_code != 200:
                    logger.warning(
                        "Failed to fetch project for import",
                        gitlab_id=project_id,
                        status_code=response.status_code,
                    )
                    continue

                gl_project = response.json()

                existing = await db.execute(
                    select(Repository).where(
                        Repository.user_id == current_user.id,
                        Repository.url == gl_project["web_url"],
                    )
                )
                if existing.scalar_one_or_none():
                    logger.info("Project already exists, skipping", url=gl_project["web_url"])
                    continue

                repo = Repository(
                    user_id=current_user.id,
                    name=gl_project["path_with_namespace"],
                    url=gl_project["web_url"],
                    description=gl_project.get("description", "") or "",
                    default_branch=gl_project.get("default_branch", "main"),
                    is_private=gl_project.get("visibility", "public") != "public",
                )
                db.add(repo)
                imported_projects.append({
                    "id": str(repo.id),
                    "name": repo.name,
                    "url": repo.url,
                })

        except Exception as e:
            logger.error("Failed to import project", gitlab_id=project_id, error=str(e))
            continue

    await db.commit()

    logger.info("Import complete", imported=len(imported_projects))

    return {
        "imported": imported_projects,
        "total": len(imported_projects),
        "message": f"Successfully imported {len(imported_projects)} projects",
    }
