"""Repository downloader utility for cloning GitHub repositories."""

import asyncio
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.core.exceptions import InvalidRepositoryException, RepositoryNotFoundException
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RepoInfo:
    """Repository information."""

    owner: str
    name: str
    full_name: str
    url: str
    branch: str
    commit_hash: str | None = None


class RepoDownloader:
    """Utility for downloading GitHub repositories."""

    def __init__(self, token: str | None = None):
        self.token = token or settings.GITHUB_TOKEN
        self.temp_dir = Path(settings.TEMP_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def clone(
        self,
        repo_url: str,
        branch: str | None = None,
        commit_hash: str | None = None,
    ) -> tuple[str, RepoInfo]:
        """
        Clone a GitHub repository to a temporary directory.

        Args:
            repo_url: GitHub repository URL
            branch: Branch to checkout (default: main/master)
            commit_hash: Specific commit to checkout

        Returns:
            Tuple of (clone_path, repo_info)
        """
        # Parse and validate URL
        repo_info = self._parse_repo_url(repo_url, branch, commit_hash)

        # Create temp directory for this clone
        clone_dir = self._get_clone_path(repo_info)

        # Clean up if exists
        if clone_dir.exists():
            shutil.rmtree(clone_dir)

        clone_dir.mkdir(parents=True, exist_ok=True)

        try:
            await self._execute_clone(repo_info, clone_dir)

            # Checkout specific branch if requested
            if branch and branch not in ["main", "master"]:
                await self._checkout_branch(clone_dir, branch)

            # Checkout specific commit if requested
            if commit_hash:
                await self._checkout_commit(clone_dir, commit_hash)

            logger.info(
                "Repository cloned successfully",
                repo=repo_info.full_name,
                path=str(clone_dir),
            )

            return str(clone_dir), repo_info

        except Exception as e:
            logger.error("Failed to clone repository", repo=repo_url, error=str(e))
            if clone_dir.exists():
                shutil.rmtree(clone_dir)
            raise

    async def _execute_clone(self, repo_info: RepoInfo, clone_dir: Path) -> None:
        """Execute git clone command."""
        cmd = ["git", "clone", "--depth", "1"]

        if self.token:
            # Use token for authentication
            auth_url = repo_info.url.replace(
                "https://github.com/",
                f"https://{self.token}@github.com/",
            )
            cmd.append(auth_url)
        else:
            cmd.append(repo_info.url)

        cmd.append(str(clone_dir))

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            if "not found" in error_msg.lower() or "doesn't exist" in error_msg.lower():
                raise RepositoryNotFoundException(repo_info.url)
            raise InvalidRepositoryException(f"Clone failed: {error_msg}")

    async def _checkout_branch(self, repo_path: Path, branch: str) -> None:
        """Checkout a specific branch."""
        cmd = ["git", "-C", str(repo_path), "fetch", "origin", f"{branch}:{branch}"]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.warning(
                "Failed to fetch branch, trying checkout",
                branch=branch,
                error=stderr.decode(),
            )

        # Try checkout
        cmd = ["git", "-C", str(repo_path), "checkout", branch]
        process = await asyncio.create_subprocess_exec(
            *cmd,
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
        cmd = ["git", "-C", str(repo_path), "fetch", "origin", commit_hash]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.warning("Failed to fetch commit", error=stderr.decode())

        cmd = ["git", "-C", str(repo_path), "checkout", commit_hash]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise InvalidRepositoryException(f"Failed to checkout commit {commit_hash}")

    def _get_clone_path(self, repo_info: RepoInfo) -> Path:
        """Generate unique clone path."""
        # Create unique directory name
        unique_id = repo_info.commit_hash or repo_info.branch or "main"
        safe_name = repo_info.full_name.replace("/", "_").replace(".", "_")
        clone_dir = self.temp_dir / f"repo_{safe_name}_{unique_id}"

        return clone_dir

    def _parse_repo_url(
        self,
        repo_url: str,
        branch: str | None,
        commit_hash: str | None,
    ) -> RepoInfo:
        """Parse repository information from URL."""
        # Handle various GitHub URL formats
        if repo_url.startswith("git@"):
            # git@github.com:org/repo.git
            match = re.match(r"git@github\.com:(.+?)/(.+?)\.git$", repo_url)
            if match:
                owner = match.group(1)
                name = match.group(2)
                return RepoInfo(
                    owner=owner,
                    name=name,
                    full_name=f"{owner}/{name}",
                    url=repo_url,
                    branch=branch or "main",
                    commit_hash=commit_hash,
                )

        elif repo_url.startswith("https://"):
            # https://github.com/org/repo
            match = re.match(
                r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
                repo_url.rstrip("/"),
            )
            if match:
                owner = match.group(1)
                name = match.group(2)
                return RepoInfo(
                    owner=owner,
                    name=name,
                    full_name=f"{owner}/{name}",
                    url=repo_url,
                    branch=branch or "main",
                    commit_hash=commit_hash,
                )

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

    async def get_default_branch(self, repo_url: str) -> str:
        """Get the default branch of a repository."""
        try:
            # Create a temporary clone to get branch info
            repo_info = self._parse_repo_url(repo_url, None, None)

            # Use git ls-remote to get symbolic ref
            cmd = ["git", "ls-remote", "--symref", repo_info.url, "HEAD"]

            if self.token:
                auth_url = repo_info.url.replace(
                    "https://github.com/",
                    f"https://{self.token}@github.com/",
                )
                cmd = ["git", "ls-remote", "--symref", auth_url, "HEAD"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode()
                # Parse output: ref: refs/heads/main HEAD
                for line in output.split("\n"):
                    if line.startswith("ref:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            branch = parts[1].replace("refs/heads/", "")
                            return branch

            return "main"

        except Exception as e:
            logger.warning("Failed to get default branch", error=str(e))
            return "main"

    async def validate_repository(self, repo_url: str) -> bool:
        """Validate that a repository exists and is accessible."""
        try:
            repo_info = self._parse_repo_url(repo_url, None, None)

            # Use git ls-remote to check if repo exists
            cmd = ["git", "ls-remote", repo_info.url, "HEAD"]

            if self.token:
                auth_url = repo_info.url.replace(
                    "https://github.com/",
                    f"https://{self.token}@github.com/",
                )
                cmd = ["git", "ls-remote", auth_url, "HEAD"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            return process.returncode == 0

        except Exception:
            return False
