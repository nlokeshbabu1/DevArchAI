"""Git repository metadata extraction.

Shells out to ``git`` (a user's local git is the same one they already use).
Output is parsed defensively so a missing git, a non-repo directory, or an
unusual remote never crashes the CLI.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from devsec.models.git import GitMetadata

_REMOTE_URL_PATTERN_PRIORITY = ("origin", "upstream")

# Resolve the user's git binary once; falls back to PATH lookup at runtime.
_GIT_EXECUTABLE = shutil.which("git") or "git"


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [_GIT_EXECUTABLE, *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        proc = subprocess.CompletedProcess(
            args=["git", *args],
            returncode=1,
            stdout="",
            stderr=str(exc),
        )
        return proc


def _strip_credentials(url: str) -> str:
    """Remove userinfo (token/password) from a remote URL.

    e.g. ``https://TOKEN@github.com/o/r.git`` -> ``https://github.com/o/r.git``
    """
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    host_part = rest.rsplit("@", 1)[1]
    return f"{scheme}://{host_part}"


def get_git_metadata(cwd: str | Path) -> GitMetadata:
    """Collect sanitized metadata about the git repository at ``cwd``."""
    cwd = Path(cwd).resolve()

    root = _run_git(["rev-parse", "--show-toplevel"], cwd)
    if root.returncode != 0:
        return GitMetadata(
            is_git=False,
            error=(root.stderr or "not a git repository").strip() or None,
        )

    remote_name = None
    for candidate in _REMOTE_URL_PATTERN_PRIORITY:
        check = _run_git(["remote", "get-url", candidate], cwd)
        if check.returncode == 0 and check.stdout.strip():
            remote_name = candidate
            break
    if remote_name is None:
        remotes = _run_git(["remote"], cwd)
        names = [n for n in remotes.stdout.splitlines() if n.strip()]
        remote_name = names[0] if names else None

    remote_url = None
    if remote_name:
        url = _run_git(["remote", "get-url", remote_name], cwd)
        if url.returncode == 0 and url.stdout.strip():
            remote_url = _strip_credentials(url.stdout.strip())

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    sha = _run_git(["rev-parse", "HEAD"], cwd)
    clean = _run_git(["status", "--porcelain"], cwd)

    return GitMetadata(
        is_git=True,
        root=root.stdout.strip(),
        remote_url=remote_url,
        remote_name=remote_name,
        branch=branch.stdout.strip() or None,
        commit_sha=sha.stdout.strip() or None,
        worktree_clean=clean.returncode == 0 and not clean.stdout.strip(),
    )
