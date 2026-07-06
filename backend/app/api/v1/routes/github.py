"""GitHub API routes for repository operations."""

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import InvalidRepositoryException, RepositoryNotFoundException
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.repository import Repository
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/github", tags=["GitHub"])


class GitHubBranch:
    """GitHub branch information."""

    def __init__(self, name: str, protected: bool, commit_sha: str):
        self.name = name
        self.protected = protected
        self.commit_sha = commit_sha

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "protected": self.protected,
            "commit_sha": self.commit_sha,
        }


def extract_repo_info(repo_url: str) -> tuple[str, str]:
    """
    Extract owner and repo name from GitHub URL.

    Args:
        repo_url: GitHub repository URL

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        InvalidRepositoryException: If URL is not a valid GitHub URL
    """
    if not repo_url.startswith("https://github.com/"):
        raise InvalidRepositoryException("Invalid GitHub URL")

    # Remove protocol and domain
    path = repo_url.replace("https://github.com/", "")

    # Remove .git suffix if present
    if path.endswith(".git"):
        path = path[:-4]

    # Split into owner and repo
    parts = path.split("/")
    if len(parts) < 2:
        raise InvalidRepositoryException("Invalid GitHub URL format")

    return parts[0], parts[1]


@router.get("/branches")
async def get_repository_branches(repo_url: str):
    """
    Get list of branches for a GitHub repository.

    Args:
        repo_url: GitHub repository URL

    Returns:
        List of branches with name and protection status
    """
    try:
        owner, repo_name = extract_repo_info(repo_url)
    except InvalidRepositoryException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    logger.info("Fetching branches", owner=owner, repo=repo_name)

    # Build GitHub API URL
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/branches"

    # Set up headers
    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=10.0)

            if response.status_code == 404:
                raise RepositoryNotFoundException(f"Repository {owner}/{repo_name} not found")

            if response.status_code == 403:
                # Rate limited
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="GitHub API rate limit exceeded. Please add GITHUB_TOKEN to environment.",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"GitHub API error: {response.status_code}",
                )

            branches_data = response.json()

            branches = [
                GitHubBranch(
                    name=branch["name"],
                    protected=branch.get("protected", False),
                    commit_sha=branch["commit"]["sha"],
                )
                for branch in branches_data
            ]

            # Sort: main/master first, then alphabetically
            branches.sort(key=lambda b: (b.name not in ["main", "master"], b.name))

            # Get actual default branch from repository info
            default_branch = branches[0].name if branches else "main"

            logger.info(f"Branches fetched successfully: {[b.name for b in branches]}, default: {default_branch}")

            return {"branches": [b.to_dict() for b in branches], "default_branch": default_branch}

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="GitHub API timeout",
        )
    except httpx.RequestError as e:
        logger.error("GitHub API request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch branches: {str(e)}",
        )


@router.get("/repo-info")
async def get_repository_info(repo_url: str):
    """
    Get basic repository information.

    Args:
        repo_url: GitHub repository URL

    Returns:
        Repository information including default branch
    """
    try:
        owner, repo_name = extract_repo_info(repo_url)
    except InvalidRepositoryException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    logger.info("Fetching repository info", owner=owner, repo=repo_name)

    # Build GitHub API URL
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

    # Set up headers
    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=10.0)

            if response.status_code == 404:
                raise RepositoryNotFoundException(f"Repository {owner}/{repo_name} not found")

            if response.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="GitHub API rate limit exceeded. Please add GITHUB_TOKEN to environment.",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"GitHub API error: {response.status_code}",
                )

            repo_data = response.json()

            return {
                "full_name": repo_data["full_name"],
                "default_branch": repo_data.get("default_branch", "main"),
                "description": repo_data.get("description", ""),
                "private": repo_data.get("private", False),
                "stargazers_count": repo_data.get("stargazers_count", 0),
                "forks_count": repo_data.get("forks_count", 0),
                "language": repo_data.get("language", ""),
            }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="GitHub API timeout",
        )
    except httpx.RequestError as e:
        logger.error("GitHub API request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch repository info: {str(e)}",
        )


@router.get("/repos")
async def get_user_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all repositories for the authenticated GitHub user.

    Uses the user's stored GitHub OAuth token to fetch their repositories.
    Returns both GitHub repos and manually added repos for a unified view.
    """
    # Get user's GitHub access token
    if not current_user.github_access_token:
        # User logged in via email/password, not GitHub OAuth
        return {
            "github_connected": False,
            "github_repositories": [],
            "message": "Connect GitHub to import repositories",
        }

    logger.info("Fetching user repositories from GitHub", user_id=current_user.id)

    # Fetch repositories from GitHub API
    api_url = "https://api.github.com/user/repos?per_page=100&sort=updated"

    headers = {
        "Authorization": f"token {current_user.github_access_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=15.0)

            if response.status_code == 401:
                # Token expired or revoked
                logger.warning("GitHub token expired", user_id=current_user.id)
                return {
                    "github_connected": False,
                    "github_repositories": [],
                    "message": "GitHub token expired. Please reconnect.",
                }

            if response.status_code != 200:
                logger.error("GitHub API error", status=response.status_code)
                return {
                    "github_connected": True,
                    "github_repositories": [],
                    "message": "Failed to fetch repositories from GitHub",
                }

            github_repos = response.json()

            # Transform to frontend-friendly format
            transformed_repos = [
                {
                    "id": f"github_{repo['id']}",
                    "name": repo["full_name"],
                    "url": repo["html_url"],
                    "description": repo.get("description", ""),
                    "default_branch": repo.get("default_branch", "main"),
                    "is_private": repo.get("private", False),
                    "language": repo.get("language", ""),
                    "stargazers_count": repo.get("stargazers_count", 0),
                    "forks_count": repo.get("forks_count", 0),
                    "updated_at": repo.get("updated_at", ""),
                    "source": "github",
                    "scan_count": 0,
                    "last_scan_at": None,
                    "scan_status": "pending",
                    "overall_score": None,
                    "tech_stack": [],
                    "issues": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                }
                for repo in github_repos
            ]

            logger.info(
                "GitHub repositories fetched",
                user_id=current_user.id,
                count=len(transformed_repos),
            )

            return {
                "github_connected": True,
                "github_repositories": transformed_repos,
                "total": len(transformed_repos),
            }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="GitHub API timeout",
        )
    except httpx.RequestError as e:
        logger.error("GitHub API request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch repositories: {str(e)}",
        )


@router.post("/import-repos")
async def import_github_repos(
    repo_ids: list[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Import selected GitHub repositories to user's repository list.

    Args:
        repo_ids: List of GitHub repository IDs to import

    Returns:
        List of imported repositories
    """
    if not current_user.github_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub not connected. Please login via GitHub first.",
        )

    if not repo_ids:
        return {"imported": [], "message": "No repositories selected"}

    logger.info("Importing GitHub repos", user_id=current_user.id, count=len(repo_ids))

    imported_repos = []

    for github_repo_id in repo_ids:
        # Fetch repo details from GitHub
        api_url = f"https://api.github.com/repositories/{github_repo_id}"
        headers = {
            "Authorization": f"token {current_user.github_access_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, headers=headers, timeout=10.0)

                if response.status_code != 200:
                    logger.warning("Failed to fetch repo", github_id=github_repo_id)
                    continue

                gh_repo = response.json()

                # Check if already exists
                existing = await db.execute(
                    select(Repository).where(
                        Repository.user_id == current_user.id,
                        Repository.url == gh_repo["html_url"],
                    )
                )
                if existing.scalar_one_or_none():
                    logger.info("Repo already exists, skipping", url=gh_repo["html_url"])
                    continue

                # Create repository
                repo = Repository(
                    user_id=current_user.id,
                    name=gh_repo["full_name"],
                    url=gh_repo["html_url"],
                    description=gh_repo.get("description", ""),
                    default_branch=gh_repo.get("default_branch", "main"),
                    is_private=gh_repo.get("private", False),
                    github_id=str(gh_repo["id"]),
                )
                db.add(repo)
                imported_repos.append({
                    "id": str(repo.id),
                    "name": repo.name,
                    "url": repo.url,
                })

        except Exception as e:
            logger.error("Failed to import repo", github_id=github_repo_id, error=str(e))
            continue

    await db.commit()

    logger.info("Import complete", imported=len(imported_repos))

    return {
        "imported": imported_repos,
        "total": len(imported_repos),
        "message": f"Successfully imported {len(imported_repos)} repositories",
    }
