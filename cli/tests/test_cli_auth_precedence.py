"""CLI credential precedence (env API key vs browser session)."""

from __future__ import annotations

import os

from devsec.config import Config


def test_env_api_key_overrides_cli_session(isolated_env, tmp_path):
    cfg = Config()
    cfg.save_cli_session(
        {
            "access_token": "cli-jwt-token",
            "refresh_token": "opaque",
            "expires_at": 9999999999,
        }
    )
    os.environ["DEVSEC_API_KEY"] = "sk-env-precedence-key"
    assert cfg.token == "sk-env-precedence-key"
    assert cfg.token_source == "environment"


def test_cli_session_used_without_env(isolated_env):
    cfg = Config()
    os.environ.pop("DEVSEC_API_KEY", None)
    os.environ.pop("DEVSEC_API_TOKEN", None)
    cfg.save_cli_session(
        {
            "access_token": "cli-jwt-token",
            "refresh_token": "opaque",
            "expires_at": 9999999999,
        }
    )
    assert cfg.token == "cli-jwt-token"
    assert cfg.token_source == "cli-session"