"""Git repository metadata model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from devsec.utils.errors import UsageError


class GitMetadata(BaseModel):
    """Sanitized metadata about a local git repository.

    ``remote_url`` is always scrubbed of any embedded credentials (tokens or
    passwords in the URL userinfo are removed) before it leaves this module.
    """

    model_config = ConfigDict(extra="ignore")

    is_git: bool = False
    root: str | None = None
    remote_url: str | None = None
    remote_name: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    worktree_clean: bool | None = None
    error: str | None = None

    @property
    def display_name(self) -> str:
        """Owner/repo style name derived from the remote URL when possible."""
        if not self.remote_url:
            return self.root or "unknown"
        path = self.remote_url.rstrip("/").split("/")[-2:]
        if len(path) == 2 and ".git" not in path[1]:
            return "/".join(path)
        if len(path) == 2:
            return "/".join(path).replace(".git", "")
        return path[-1].replace(".git", "")

    def require_remote(self) -> str:
        """Return the remote URL or raise a clear usage error.

        Phase 1 scans by *reference*: the backend clones the remote URL. A
        repository without a git remote cannot be scanned until archive
        upload is added to the backend.
        """
        if not self.is_git:
            raise UsageError(
                "Not a git repository.",
                hint="Run 'devsec scan' inside a git repository, or push your "
                "project to a git remote first.",
            )
        if not self.remote_url:
            raise UsageError(
                "No Git remote found.",
                hint="Add a remote or use:\n  devsec scan --repo <repository-url>",
            )
        return self.remote_url
