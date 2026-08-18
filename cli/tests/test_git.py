"""Tests for git metadata extraction."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from devsec.utils.git import get_git_metadata


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for cmd in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "user.name", "Test"],
    ):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    (repo / "a.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def test_metadata_in_clean_repo(git_repo: Path):
    meta = get_git_metadata(git_repo)
    assert meta.is_git is True
    assert meta.root == str(git_repo.resolve())
    assert meta.branch == "main"
    assert meta.commit_sha
    assert meta.worktree_clean is True


def test_dirty_worktree_detected(git_repo: Path):
    (git_repo / "untracked.txt").write_text("x", encoding="utf-8")
    meta = get_git_metadata(git_repo)
    assert meta.worktree_clean is False


def test_remote_credentials_are_scrubbed(git_repo: Path):
    subprocess.run(
        [
            "git",
            "remote",
            "add",
            "origin",
            "https://ghp_FAKETOKEN@github.com/acme/infra.git",
        ],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    meta = get_git_metadata(git_repo)
    assert meta.remote_url == "https://github.com/acme/infra.git"
    assert "ghp_FAKETOKEN" not in (meta.remote_url or "")


def test_display_name_from_remote(git_repo: Path):
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/acme/infra.git"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    meta = get_git_metadata(git_repo)
    assert meta.display_name == "acme/infra"


def test_non_repo_directory(tmp_path: Path):
    meta = get_git_metadata(tmp_path)
    assert meta.is_git is False
    assert meta.error


def test_missing_remote_raises_usage(git_repo: Path):
    meta = get_git_metadata(git_repo)
    assert meta.remote_url is None
    try:
        meta.require_remote()
    except Exception as exc:
        assert "git remote" in str(exc).lower()
    else:
        raise AssertionError("expected UsageError")
