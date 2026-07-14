"""
GitHub Service - Repository cloning and management
"""

import asyncio
import shutil
from pathlib import Path

import structlog

from app.config import settings
from app.core.exceptions import InvalidRepositoryException, RepositoryNotFoundException

logger = structlog.get_logger(__name__)


class GitHubService:
    """Service for interacting with GitHub repositories."""

    def __init__(self, token: str | None = None):
        self.token = token or settings.GITHUB_TOKEN
        self.temp_dir = Path(settings.TEMP_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def clone_repository(
        self,
        repo_url: str,
        branch: str | None = None,
        commit_hash: str | None = None,
    ) -> str:
        """
        Clone a GitHub repository to a temporary directory.

        Args:
            repo_url: GitHub repository URL
            branch: Branch to checkout (default: main/master)
            commit_hash: Specific commit to checkout

        Returns:
            Path to cloned repository
        """
        # Validate and parse URL
        repo_name = self._parse_repo_url(repo_url)

        # Create temp directory for this clone
        clone_dir = self.temp_dir / f"repo_{commit_hash or branch or 'main'}_{repo_name.replace('/', '_')}"

        # Clean up if exists
        if clone_dir.exists():
            shutil.rmtree(clone_dir)

        clone_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Build git clone command
            cmd = ["git", "clone"]

            if self.token:
                # Use token for authentication
                auth_url = repo_url.replace(
                    "https://github.com/",
                    f"https://{self.token}@github.com/",
                )
                cmd.append(auth_url)
            else:
                cmd.append(repo_url)

            cmd.append(str(clone_dir))

            # Run clone
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RepositoryNotFoundException(repo_url)

            # Checkout specific branch if requested
            if branch:
                await self._checkout_branch(clone_dir, branch)

            # Checkout specific commit if requested
            if commit_hash:
                await self._checkout_commit(clone_dir, commit_hash)

            logger.info(
                "Repository cloned successfully",
                repo=repo_name,
                path=str(clone_dir),
            )

            return str(clone_dir)

        except Exception as e:
            logger.error("Failed to clone repository", repo=repo_url, error=str(e))
            if clone_dir.exists():
                shutil.rmtree(clone_dir)
            raise

    async def _checkout_branch(self, repo_path: Path, branch: str) -> None:
        """Checkout a specific branch."""
        process = await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_path), "checkout", branch,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.warning(
                "Failed to checkout branch",
                branch=branch,
                error=stderr.decode(),
            )

    async def _checkout_commit(self, repo_path: Path, commit_hash: str) -> None:
        """Checkout a specific commit."""
        process = await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_path), "checkout", commit_hash,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise InvalidRepositoryException(f"Failed to checkout commit {commit_hash}")

    def _parse_repo_url(self, repo_url: str) -> str:
        """Parse repository name from URL."""
        # Handle various GitHub URL formats
        if repo_url.startswith("git@"):
            # git@github.com:org/repo.git
            return repo_url.split(":")[-1].replace(".git", "")
        elif repo_url.startswith("https://"):
            # https://github.com/org/repo
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 2:
                return "/".join(parts[-2:]).replace(".git", "")

        raise InvalidRepositoryException(f"Invalid GitHub URL: {repo_url}")

    def cleanup(self, repo_path: str) -> None:
        """Clean up cloned repository."""
        path = Path(repo_path)
        if path.exists() and str(self.temp_dir) in str(path):
            try:
                shutil.rmtree(path)
                logger.info("Cleaned up temporary repository", path=repo_path)
            except Exception as e:
                logger.warning("Failed to cleanup repository", path=repo_path, error=str(e))

    async def get_repository_info(self, repo_url: str) -> dict:
        """Get repository metadata."""
        repo_name = self._parse_repo_url(repo_url)

        # For now, return basic info
        # In production, use GitHub API
        return {
            "name": repo_name,
            "url": repo_url,
        }
