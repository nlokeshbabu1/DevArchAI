"""
GitHub Scanner Service
Fetches repository file tree using GitHub API.
"""

from typing import Any

import httpx
import structlog

from app.config import settings
from app.core.exceptions import InvalidRepositoryException, RepositoryNotFoundException
from app.services.github_validator import GitHubValidator

logger = structlog.get_logger(__name__)


class GitHubScanner:
    """Service for scanning GitHub repository contents."""

    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_API_VERSION = "2022-11-28"

    def __init__(self, token: str | None = None):
        self.token = token or settings.GITHUB_TOKEN
        self.validator = GitHubValidator()
        self._client: httpx.AsyncClient | None = None
        self._cache = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": self.GITHUB_API_VERSION,
                "User-Agent": "DevArchAI-Scanner/1.0",
            }

            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )

        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_file_tree(self, repo_url: str, branch: str | None = None) -> list[str]:
        """
        Fetch the file tree of a GitHub repository.

        Args:
            repo_url: GitHub repository URL
            branch: Branch to fetch (default: default branch)

        Returns:
            List of file paths in the repository

        Raises:
            RepositoryNotFoundException: If repository doesn't exist
            InvalidRepositoryException: If URL is invalid
        """
        # Validate URL first
        validation = self.validator.validate_github_repo(repo_url)

        if not validation.valid:
            raise InvalidRepositoryException(f"Invalid GitHub URL: {validation.error_message}")

        owner = validation.owner
        repo = validation.repo

        # Get default branch if not specified
        if branch is None:
            branch = await self._get_default_branch(owner, repo)

        # Fetch tree recursively
        files = await self._fetch_tree(owner, repo, branch)

        logger.info(
            "Fetched repository file tree",
            owner=owner,
            repo=repo,
            branch=branch,
            file_count=len(files)
        )

        return files

    async def _get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch of a repository."""
        client = await self._get_client()

        try:
            url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}"
            response = await client.get(url)

            if response.status_code == 404:
                raise RepositoryNotFoundException(f"Repository {owner}/{repo} not found")

            if response.status_code == 403:
                # Rate limited
                if self.token:
                    raise InvalidRepositoryException(
                        "Access denied. Check if the repository is private and token has permissions."
                    )
                else:
                    # Try without auth for public repos
                    pass

            response.raise_for_status()
            data = response.json()

            default_branch = data.get("default_branch", "main")
            logger.debug("Got default branch", branch=default_branch)

            return default_branch

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RepositoryNotFoundException(f"Repository {owner}/{repo} not found")
            raise InvalidRepositoryException(f"Failed to get repository info: {str(e)}")

    async def _fetch_tree(
        self,
        owner: str,
        repo: str,
        branch: str,
        path: str = "",
        max_depth: int = 10,
        current_depth: int = 0
    ) -> list[str]:
        """
        Recursively fetch the file tree.

        Uses GitHub Git Data API to get the tree.
        """
        if current_depth >= max_depth:
            logger.warning("Max depth reached", depth=current_depth)
            return []

        client = await self._get_client()
        files = []

        try:
            # Get the tree SHA for the branch
            sha_url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/git/refs/heads/{branch}"
            sha_response = await client.get(sha_url)

            if sha_response.status_code == 404:
                raise RepositoryNotFoundException(f"Branch {branch} not found")

            sha_response.raise_for_status()
            sha_data = sha_response.json()

            # Handle different response formats
            if "object" in sha_data:
                commit_sha = sha_data["object"]["sha"]
            else:
                commit_sha = sha_data.get("sha", "")

            # Get the tree
            tree_url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{commit_sha}"
            params = {"recursive": "1"}  # Get full tree recursively
            tree_response = await client.get(tree_url, params=params)

            if tree_response.status_code == 404:
                raise RepositoryNotFoundException(f"Could not fetch tree for {owner}/{repo}")

            tree_response.raise_for_status()
            tree_data = tree_response.json()

            # Parse tree entries
            for entry in tree_data.get("tree", []):
                file_path = entry.get("path", "")
                entry_type = entry.get("type", "")

                # Skip directories, only include files
                if entry_type == "blob" and file_path:
                    # Filter out common non-essential files
                    if self._should_include_file(file_path):
                        files.append(file_path)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RepositoryNotFoundException("Repository or branch not found")
            if e.response.status_code == 403:
                # Rate limit exceeded
                raise InvalidRepositoryException(
                    "GitHub API rate limit exceeded. Please try again later or provide a GitHub token."
                )
            raise InvalidRepositoryException(f"Failed to fetch tree: {str(e)}")

        return files

    def _should_include_file(self, file_path: str) -> bool:
        """
        Determine if a file should be included in the analysis.

        Filters out binary files, large files, and non-essential files.
        """
        # Skip common non-essential directories
        skip_dirs = [
            "node_modules/",
            "vendor/",
            ".git/",
            "__pycache__/",
            ".venv/",
            "venv/",
            "env/",
            ".env/",
            "dist/",
            "build/",
            "target/",
            ".idea/",
            ".vscode/",
        ]

        for skip_dir in skip_dirs:
            if file_path.startswith(skip_dir) or f"/{skip_dir}" in file_path:
                return False

        # Skip binary files and large files
        binary_extensions = [
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx",
            ".zip", ".tar", ".gz", ".rar", ".7z",
            ".exe", ".dll", ".so", ".dylib",
            ".bin", ".dat", ".db", ".sqlite",
            ".woff", ".woff2", ".ttf", ".eot",
            ".mp3", ".mp4", ".avi", ".mov",
            ".pickle", ".pkl", ".parquet", ".feather",
        ]

        for ext in binary_extensions:
            if file_path.lower().endswith(ext):
                return False

        # Skip very large files (by path length heuristic)
        if len(file_path) > 500:
            return False

        return True

    async def get_repository_info(self, repo_url: str) -> dict[str, Any]:
        """
        Get repository metadata.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Dictionary with repository information
        """
        validation = self.validator.validate_github_repo(repo_url)

        if not validation.valid:
            raise InvalidRepositoryException(f"Invalid GitHub URL: {validation.error_message}")

        owner = validation.owner
        repo = validation.repo

        client = await self._get_client()

        try:
            url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}"
            response = await client.get(url)

            if response.status_code == 404:
                raise RepositoryNotFoundException(f"Repository {owner}/{repo} not found")

            response.raise_for_status()
            data = response.json()

            return {
                "full_name": data.get("full_name", f"{owner}/{repo}"),
                "description": data.get("description"),
                "default_branch": data.get("default_branch", "main"),
                "stargazers_count": data.get("stargazers_count", 0),
                "forks_count": data.get("forks_count", 0),
                "language": data.get("language"),
                "is_private": data.get("private", False),
                "size": data.get("size", 0),  # Size in KB
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RepositoryNotFoundException(f"Repository {owner}/{repo} not found")
            raise InvalidRepositoryException(f"Failed to get repository info: {str(e)}")


# Convenience functions
_scanner = GitHubScanner()


async def fetch_repo_files(repo_url: str, branch: str | None = None) -> list[str]:
    """
    Fetch file tree from a GitHub repository.

    Args:
        repo_url: GitHub repository URL
        branch: Branch to fetch (default: default branch)

    Returns:
        List of file paths
    """
    return await _scanner.fetch_file_tree(repo_url, branch)


async def get_repo_info(repo_url: str) -> dict[str, Any]:
    """
    Get repository metadata.

    Args:
        repo_url: GitHub repository URL

    Returns:
        Repository information dictionary
    """
    return await _scanner.get_repository_info(repo_url)
