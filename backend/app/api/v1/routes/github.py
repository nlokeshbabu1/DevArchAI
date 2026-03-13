"""GitHub API routes for repository operations."""

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.core.exceptions import InvalidRepositoryException, RepositoryNotFoundException

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

            return {"branches": [b.to_dict() for b in branches], "default_branch": branches[0].name if branches else "main"}

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
