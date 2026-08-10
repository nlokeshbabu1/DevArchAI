"""Tests for configuration precedence and the secure secret store."""

from __future__ import annotations

import json
from pathlib import Path

from devsec.config import Config, SecretStore
from devsec.utils.errors import UsageError


def test_env_overrides_config_file(tmp_path: Path):
    config_file = tmp_path / "config.toml"
    config_file.write_text('api_url = "http://from-file"\n', encoding="utf-8")
    cfg = Config(
        config_file=config_file,
        env={"DEVSEC_API_URL": "http://from-env", "DEVSEC_API_TOKEN": ""},
    )
    assert cfg.api_url == "http://from-env"
    assert cfg.api_url_source == "environment"


def test_config_file_falls_back_to_default(tmp_path: Path):
    cfg = Config(config_file=tmp_path / "config.toml", env={"DEVSEC_API_TOKEN": ""})
    assert cfg.api_url == "http://localhost:8000"
    assert cfg.api_url_source == "default"


def test_set_and_get_config_value(tmp_path: Path):
    cfg = Config(config_file=tmp_path / "config.toml", env={"DEVSEC_API_TOKEN": ""})
    cfg.set("api-url", "http://example.com")
    assert cfg.file_values() == {"api_url": "http://example.com"}
    assert cfg.api_url == "http://example.com"
    assert cfg.api_url_source == "config-file"


def test_set_unknown_key_raises(tmp_path: Path):
    cfg = Config(config_file=tmp_path / "config.toml", env={"DEVSEC_API_TOKEN": ""})
    try:
        cfg.set("not-a-key", "x")
    except UsageError as exc:
        assert "not-a-key" in str(exc)
    else:
        raise AssertionError("expected UsageError")


def test_unset_removes_value(tmp_path: Path):
    cfg = Config(config_file=tmp_path / "config.toml", env={"DEVSEC_API_TOKEN": ""})
    cfg.set("api-url", "http://example.com")
    cfg.unset("api-url")
    assert "api_url" not in cfg.file_values()


def test_token_from_environment(tmp_path: Path):
    cfg = Config(
        config_file=tmp_path / "config.toml",
        env={"DEVSEC_API_TOKEN": "dk_env_token_1", "DEVSEC_API_URL": "http://x"},
    )
    assert cfg.token == "dk_env_token_1"
    assert cfg.token_source == "environment"
    assert cfg.is_using_api_key


def test_token_from_devsec_api_key_env(tmp_path: Path):
    cfg = Config(
        config_file=tmp_path / "config.toml",
        env={"DEVSEC_API_KEY": "sk-env-key-1", "DEVSEC_API_URL": "http://x"},
    )
    assert cfg.token == "sk-env-key-1"
    assert cfg.token_source == "environment"
    assert cfg.is_using_api_key


def test_devsec_api_key_takes_precedence_over_legacy_env(tmp_path: Path):
    cfg = Config(
        config_file=tmp_path / "config.toml",
        env={
            "DEVSEC_API_KEY": "sk-new-env-1",
            "DEVSEC_API_TOKEN": "dk_old_env_1",
            "DEVSEC_API_URL": "http://x",
        },
    )
    assert cfg.token == "sk-new-env-1"
    assert cfg.token_source == "environment"


def test_env_key_takes_precedence_over_keyring(tmp_path: Path):
    cfg = Config(config_file=tmp_path / "config.toml", env={"DEVSEC_API_KEY": "sk-env-1"})
    cfg.secrets.set_token("dk_keyring_1")
    assert cfg.token == "sk-env-1"
    assert cfg.token_source == "environment"


def test_secret_store_file_fallback(tmp_path: Path):
    store = SecretStore(config_file=tmp_path / "config.toml")
    store.set_token("dk_super_secret")
    creds_file = tmp_path / "credentials.json"
    assert creds_file.exists()
    assert json.loads(creds_file.read_text())["default"] == "dk_super_secret"
    assert store.get_token() == "dk_super_secret"
    assert store.using_fallback is True


def test_secret_store_file_permissions(tmp_path: Path):
    store = SecretStore(config_file=tmp_path / "config.toml")
    store.set_token("dk_super_secret")
    mode = (tmp_path / "credentials.json").stat().st_mode & 0o777
    assert mode == 0o600


def test_secret_store_delete(tmp_path: Path):
    store = SecretStore(config_file=tmp_path / "config.toml")
    store.set_token("dk_super_secret")
    store.delete_token()
    assert store.get_token() is None
    assert not (tmp_path / "credentials.json").exists()


def test_token_not_written_to_config_toml(tmp_path: Path):
    cfg = Config(config_file=tmp_path / "config.toml", env={"DEVSEC_API_TOKEN": ""})
    cfg.secrets.set_token("dk_super_secret")
    body = cfg.config_file.read_text(encoding="utf-8") if cfg.config_file.exists() else ""
    assert "dk_super_secret" not in body
