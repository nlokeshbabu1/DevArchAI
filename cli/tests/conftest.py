"""Shared pytest fixtures for the DevArchAI CLI."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from devsec.config import Config

_ENV_KEYS = (
    "DEVSEC_API_URL",
    "DEVSEC_API_TOKEN",
    "DEVSEC_API_KEY",
    "DEVSEC_FRONTEND_URL",
    "DEVSEC_DISABLE_WEBSOCKET",
    "XDG_CONFIG_HOME",
)


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


@pytest.fixture
def isolated_env(tmp_path: Path):
    """Run CLI commands with an isolated config dir and env."""
    old_env = {k: os.environ.get(k) for k in _ENV_KEYS}
    os.environ["XDG_CONFIG_HOME"] = str(tmp_path)
    os.environ["DEVSEC_API_URL"] = "http://127.0.0.1:59999"
    os.environ["DEVSEC_DISABLE_WEBSOCKET"] = "1"
    os.environ.pop("DEVSEC_API_TOKEN", None)
    os.environ.pop("DEVSEC_API_KEY", None)
    os.environ.pop("DEVSEC_FRONTEND_URL", None)
    yield tmp_path
    for key, value in old_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
