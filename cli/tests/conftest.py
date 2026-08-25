"""Shared pytest fixtures for the DevArchAI CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from devsec.config import Config


@pytest.fixture
def config(tmp_path: Path) -> Config:
    """A Config isolated to a temp config file (no real keyring/config)."""
    config_file = tmp_path / "config.toml"
    return Config(config_file=config_file)


@pytest.fixture
def env_config(tmp_path: Path) -> dict[str, str]:
    """Default environment for Config construction in tests."""
    return {
        "DEVSEC_API_URL": "http://127.0.0.1:8000",
        "DEVSEC_API_TOKEN": "",
        "XDG_CONFIG_HOME": str(tmp_path),
    }


@pytest.fixture
def repo_factory(tmp_path: Path):
    """Create small git repositories for tests."""

    def _make(name: str = "repo", remote: str | None = None) -> Path:
        repo = tmp_path / name
        repo.mkdir()
        (repo / "README.md").write_text("# hello\n", encoding="utf-8")
        return repo

    return _make
