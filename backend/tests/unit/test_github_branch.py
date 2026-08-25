"""Tests for default branch resolution."""

from app.utils.github_branch import resolve_repository_branch


def test_resolve_main_to_master_for_terraform_repo(monkeypatch):
    def fake_git(repo_url: str, github_token: str | None = None):
        return "master"

    monkeypatch.setattr(
        "app.utils.github_branch.fetch_default_branch_via_git",
        fake_git,
    )
    branch = resolve_repository_branch(
        "https://github.com/nlokeshbabu1/Terraform",
        "main",
    )
    assert branch == "master"


def test_explicit_branch_unchanged(monkeypatch):
    monkeypatch.setattr(
        "app.utils.github_branch.fetch_default_branch_via_git",
        lambda *args, **kwargs: "master",
    )
    branch = resolve_repository_branch(
        "https://github.com/nlokeshbabu1/Terraform",
        "develop",
    )
    assert branch == "develop"
