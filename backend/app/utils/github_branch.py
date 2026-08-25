"""Resolve the default Git branch for a remote repository."""

from __future__ import annotations

import subprocess
from urllib.parse import urlparse

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


def _github_auth_url(repo_url: str, github_token: str | None) -> str:
    if github_token and repo_url.startswith("https://github.com/"):
        return repo_url.replace(
            "https://github.com/",
            f"https://oauth2:{github_token}@github.com/",
        )
    return repo_url


def _parse_owner_repo(repo_url: str) -> tuple[str, str] | None:
    path = urlparse(repo_url.rstrip("/")).path.strip("/")
    if not path:
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            return None
        owner, repo = parts[-2], parts[-1]
    else:
        segments = path.split("/")
        if len(segments) < 2:
            return None
        owner, repo = segments[0], segments[1]
    return owner, repo.replace(".git", "")


def fetch_default_branch_via_git(repo_url: str, github_token: str | None = None) -> str | None:
    """Return the remote HEAD branch using ``git ls-remote`` (no GitHub API quota)."""
    auth_url = _github_auth_url(repo_url, github_token)
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--symref", auth_url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("git ls-remote failed", repo_url=repo_url, error=str(exc))
        return None

    if result.returncode != 0:
        logger.warning(
            "git ls-remote returned non-zero",
            repo_url=repo_url,
            stderr=(result.stderr or "").strip()[:200],
        )
        return None

    for line in result.stdout.splitlines():
        if line.startswith("ref:"):
            parts = line.split()
            if len(parts) >= 2:
                return parts[1].replace("refs/heads/", "")
    return None


def fetch_default_branch_via_github_api(
    repo_url: str,
    github_token: str | None = None,
) -> str | None:
    """Fallback: GitHub REST API default branch lookup."""
    parsed = _parse_owner_repo(repo_url)
    if not parsed:
        return None
    owner, repo = parsed
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
        if response.status_code == 200:
            return response.json().get("default_branch")
    except Exception as exc:
        logger.warning("GitHub API default branch lookup failed", error=str(exc))
    return None


def resolve_repository_branch(
    repo_url: str,
    requested_branch: str | None,
    *,
    github_token: str | None = None,
) -> str:
    """Pick the branch to clone.

  When the caller passes the generic placeholder ``main`` (or omits a branch),
  resolve the remote's actual default branch (e.g. ``master``).
    """
    branch = (requested_branch or "main").strip() or "main"
    if branch not in {"main", "master"}:
        return branch

    detected = fetch_default_branch_via_git(repo_url, github_token)
    if not detected:
        detected = fetch_default_branch_via_github_api(repo_url, github_token)
    if detected and detected != branch:
        logger.info(
            "Resolved repository default branch",
            repo_url=repo_url,
            requested=branch,
            resolved=detected,
        )
        return detected
    return branch
