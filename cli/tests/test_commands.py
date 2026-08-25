"""End-to-end CLI command tests via Typer's CliRunner."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from typer.testing import CliRunner

from devsec.config import SecretStore
from devsec.main import app

runner = CliRunner()

_ENV_KEYS = (
    "DEVSEC_API_URL",
    "DEVSEC_API_TOKEN",
    "DEVSEC_API_KEY",
    "DEVSEC_FRONTEND_URL",
    "XDG_CONFIG_HOME",
)


@pytest.fixture
def isolated_env(tmp_path: Path):
    """Run CLI commands with an isolated config dir and env."""
    old_env = {k: os.environ.get(k) for k in _ENV_KEYS}
    os.environ["XDG_CONFIG_HOME"] = str(tmp_path)
    os.environ["DEVSEC_API_URL"] = "http://127.0.0.1:59999"
    os.environ.pop("DEVSEC_API_TOKEN", None)
    os.environ.pop("DEVSEC_API_KEY", None)
    os.environ.pop("DEVSEC_FRONTEND_URL", None)
    yield tmp_path
    for key, value in old_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _mock_http(handler):
    """Patch httpx.Client so ApiClient uses a MockTransport."""
    original_client = httpx.Client

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    return patch("devsec.api.client.httpx.Client", client_factory)


def test_version_json(isolated_env):
    result = runner.invoke(app, ["version", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["app"] == "devsec"
    assert "version" in data


def test_version_flag(isolated_env):
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "devsec" in result.stdout


def test_config_set_and_get(isolated_env):
    # Clear the env override so the file value is the effective one (env wins).
    os.environ.pop("DEVSEC_API_URL", None)
    result = runner.invoke(app, ["config", "set", "api-url", "http://example.com"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["config", "get", "api-url", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["value"] == "http://example.com"


def test_config_set_unknown_key_exit_2(isolated_env):
    result = runner.invoke(app, ["config", "set", "nope", "x"])
    assert result.exit_code == 2
    assert "Unknown config key" in result.stderr


def test_config_unset(isolated_env):
    runner.invoke(app, ["config", "set", "api-url", "http://example.com"])
    result = runner.invoke(app, ["config", "unset", "api-url", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["removed"] is True


def test_config_show_aliases_list(isolated_env):
    # Clear env override so file value is the effective one.
    os.environ.pop("DEVSEC_API_URL", None)
    runner.invoke(app, ["config", "set", "api-url", "http://example.com"])
    result = runner.invoke(app, ["config", "show", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["values"]["api_url"] == "http://example.com"


def test_config_show_human_readable(isolated_env):
    os.environ.pop("DEVSEC_API_URL", None)
    runner.invoke(app, ["config", "set", "api-url", "http://example.com"])
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0, result.output
    assert "api_url" in result.stdout
    assert "http://example.com" in result.stdout
    # Secrets must never appear in config show output.
    assert "sk-" not in result.stdout
    assert "dk_" not in result.stdout


def test_config_set_api_url(isolated_env):
    os.environ.pop("DEVSEC_API_URL", None)
    result = runner.invoke(app, ["config", "set", "api-url", "https://api.example.com"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["config", "show", "--json"])
    assert json.loads(result.stdout)["api_url"] == "https://api.example.com"


def test_auth_status_not_authenticated(isolated_env):
    result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["authenticated"] is False
    assert data["api_url"]
    assert data["authentication"] is None


def test_auth_status_human_not_authenticated(isolated_env):
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "Not authenticated" in result.stdout
    assert "devsec auth login" in result.stdout


def test_auth_login_validates_and_stores(isolated_env, tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "dk_12345test"
        assert "dk_12345test" not in str(request.url)
        return httpx.Response(200, json={"id": "1", "email": "a@b.c", "username": "u"})

    with _mock_http(handler):
        result = runner.invoke(app, ["auth", "login", "--api-key", "dk_12345test", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["stored"] is True
    assert data["email"] == "a@b.c"
    assert data["authentication"] == "API Key"
    # Never echo the raw key in output.
    assert "dk_12345test" not in result.output


def test_auth_login_accepts_sk_key(isolated_env, tmp_path):
    key = "sk-9PcnoNLxSP4CQpTufHEHWvscHl744CVAMEUHcL440o"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == key
        return httpx.Response(200, json={"id": "1", "email": "a@b.c", "username": "u"})

    with _mock_http(handler):
        result = runner.invoke(app, ["auth", "login", "--api-key", key, "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["stored"] is True
    assert key not in result.output


def test_auth_login_rejects_bad_format(isolated_env):
    result = runner.invoke(app, ["auth", "login", "--api-key", "wrong"])
    assert result.exit_code == 2
    assert "sk-" in result.output


def test_auth_login_invalid_credentials(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Invalid API key"})

    with _mock_http(handler):
        result = runner.invoke(app, ["auth", "login", "--api-key", "sk-bad-key-value", "--json"])
    assert result.exit_code == 3, result.output
    data = json.loads(result.stdout)
    assert data["error"] in {"auth", "api_error"} or data["exit_code"] == 3
    assert "sk-bad-key-value" not in result.output


def test_auth_status_authenticated(isolated_env, tmp_path):
    store = SecretStore(config_file=tmp_path / "devsec" / "config.toml")
    store.set_token("sk-valid-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "sk-valid-key"
        return httpx.Response(
            200,
            json={"id": "1", "email": "user@example.com", "username": "user", "role": "user"},
        )

    with _mock_http(handler):
        result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["authenticated"] is True
    assert data["account"] == "user@example.com"
    assert data["authentication"] == "API Key"
    assert data["api_url"]
    assert "sk-valid-key" not in result.output


def test_auth_status_human_authenticated(isolated_env, tmp_path):
    store = SecretStore(config_file=tmp_path / "devsec" / "config.toml")
    store.set_token("sk-valid-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"id": "1", "email": "user@example.com", "username": "user"},
        )

    with _mock_http(handler):
        result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0, result.output
    assert "Authenticated" in result.stdout
    assert "user@example.com" in result.stdout
    assert "API Key" in result.stdout
    assert "sk-valid-key" not in result.output


def test_auth_status_invalid_credentials(isolated_env, tmp_path):
    store = SecretStore(config_file=tmp_path / "devsec" / "config.toml")
    store.set_token("sk-expired-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Could not validate credentials"})

    with _mock_http(handler):
        result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["authenticated"] is False
    assert data["error"]
    assert "sk-expired-key" not in result.output


def test_auth_status_with_env_api_key(isolated_env):
    os.environ["DEVSEC_API_KEY"] = "sk-from-env-key"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "sk-from-env-key"
        return httpx.Response(
            200,
            json={"id": "9", "email": "ci@example.com", "username": "ci"},
        )

    with _mock_http(handler):
        result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["authenticated"] is True
    assert data["token_source"] == "environment"
    assert data["account"] == "ci@example.com"
    assert "sk-from-env-key" not in result.output


def test_auth_logout_revokes_sk_key(isolated_env, tmp_path):
    store = SecretStore(config_file=tmp_path / "devsec" / "config.toml")
    store.set_token("sk-abcdef")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"message": "revoked"})

    with _mock_http(handler):
        result = runner.invoke(app, ["auth", "logout", "--revoke", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["revoked"] is True
    assert seen and "/settings/api-keys/current" in seen[0]
    assert store.get_token() is None


def test_browser_open_failure_is_swallowed():
    from devsec.api.auth import _open_browser

    with (
        patch("devsec.api.auth._is_wsl", return_value=False),
        patch("devsec.api.auth.webbrowser.open", side_effect=OSError("no browser")),
        patch("devsec.api.auth.shutil.which", return_value=None),
    ):
        _open_browser("http://example.com/settings")  # must not raise


def test_browser_open_uses_explorer_on_wsl():
    from devsec.api.auth import _open_browser

    calls: list = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0)

    with (
        patch("devsec.api.auth._is_wsl", return_value=True),
        patch(
            "devsec.api.auth.shutil.which",
            side_effect=lambda name: "/usr/bin/explorer.exe" if name == "explorer.exe" else None,
        ),
        patch("devsec.api.auth.subprocess.run", side_effect=fake_run) as run_mock,
        patch(
            "devsec.api.auth.webbrowser.open",
            side_effect=AssertionError("should not reach webbrowser"),
        ),
    ):
        _open_browser("http://example.com/settings")
    assert run_mock.call_count == 1
    assert calls[0] == ["/usr/bin/explorer.exe", "http://example.com/settings"]


def test_auth_logout_clears_token(isolated_env, tmp_path):
    store = SecretStore(config_file=tmp_path / "devsec" / "config.toml")
    store.set_token("dk_abc")
    result = runner.invoke(app, ["auth", "logout", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["logged_out"] is True
    assert data["env_credential_still_set"] is False
    assert store.get_token() is None


def test_auth_logout_does_not_clear_env_api_key(isolated_env, tmp_path):
    os.environ["DEVSEC_API_KEY"] = "sk-env-still-here"
    store = SecretStore(config_file=tmp_path / "devsec" / "config.toml")
    store.set_token("sk-local-key")
    result = runner.invoke(app, ["auth", "logout", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["logged_out"] is True
    assert data["env_credential_still_set"] is True
    assert store.get_token() is None
    assert os.environ["DEVSEC_API_KEY"] == "sk-env-still-here"


def test_project_list_error_when_backend_down(isolated_env):
    result = runner.invoke(app, ["project", "list", "--json"])
    assert result.exit_code == 4
    data = json.loads(result.stdout)
    assert data["error"] == "api_error"
    assert data["exit_code"] == 4


def test_project_list_requires_auth(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Not authenticated"})

    with _mock_http(handler):
        result = runner.invoke(app, ["project", "list", "--json"])
    assert result.exit_code == 3, result.output
    data = json.loads(result.stdout)
    assert data["exit_code"] == 3


def test_project_list_success(isolated_env, tmp_path):
    store = SecretStore(config_file=tmp_path / "devsec" / "config.toml")
    store.set_token("sk-list-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/repositories" in str(request.url)
        return httpx.Response(
            200,
            json={
                "repositories": [
                    {
                        "id": "11111111-2222-3333-4444-555555555555",
                        "name": "acme/infra",
                        "full_name": "acme/infra",
                        "url": "https://github.com/acme/infra",
                        "default_branch": "main",
                        "is_private": False,
                        "is_active": True,
                        "scan_status": "completed",
                        "last_scan_at": "2026-04-01T12:00:00Z",
                        "created_at": "2026-01-15T08:30:00Z",
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
            },
        )

    with _mock_http(handler):
        result = runner.invoke(app, ["project", "list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["total"] == 1
    assert data["projects"][0]["name"] == "acme/infra"
    assert data["projects"][0]["id"] == "11111111-2222-3333-4444-555555555555"


def test_project_list_human_table(isolated_env, tmp_path):
    store = SecretStore(config_file=tmp_path / "devsec" / "config.toml")
    store.set_token("sk-list-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "repositories": [
                    {
                        "id": "11111111-2222-3333-4444-555555555555",
                        "name": "acme/infra",
                        "url": "https://github.com/acme/infra",
                        "default_branch": "main",
                        "scan_status": "completed",
                        "created_at": "2026-01-15T08:30:00Z",
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
            },
        )

    with _mock_http(handler):
        result = runner.invoke(app, ["project", "list"])
    assert result.exit_code == 0, result.output
    assert "Projects" in result.stdout
    assert "GitHub" in result.stdout or "main" in result.stdout


def test_project_detect_json(isolated_env, tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM alpine\n", encoding="utf-8")
    result = runner.invoke(app, ["project", "detect", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["stack"]["has_docker"] is True


def test_project_detect_bad_path(isolated_env):
    result = runner.invoke(app, ["project", "detect", "/definitely/not/a/path"])
    assert result.exit_code == 2


def test_project_current_empty(isolated_env):
    result = runner.invoke(app, ["project", "current", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"selected": None, "project": None}


def test_project_current_empty_human(isolated_env):
    result = runner.invoke(app, ["project", "current"])
    assert result.exit_code == 0, result.output
    assert "No project selected" in result.stdout
    assert "devsec project select" in result.stdout


def test_project_select_and_current(isolated_env, tmp_path):
    project = {
        "id": "11111111-2222-3333-4444-555555555555",
        "name": "acme/infra",
        "url": "https://github.com/acme/infra",
        "default_branch": "main",
        "is_private": False,
        "is_active": True,
        "created_at": "2026-01-15T08:30:00Z",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=project)

    with _mock_http(handler):
        result = runner.invoke(app, ["project", "select", project["id"], "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["id"] == project["id"]

    with _mock_http(handler):
        result = runner.invoke(app, ["project", "current", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["selected"] == project["id"]


def test_project_select_by_prefix(isolated_env, tmp_path):
    project = {
        "id": "ae8f8620-1234-5678-9abc-def012345678",
        "name": "acme/infra",
        "url": "https://github.com/acme/infra",
        "default_branch": "main",
        "is_private": False,
        "is_active": True,
        "created_at": "2026-01-15T08:30:00Z",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url.path).endswith("/repositories"):
            return httpx.Response(
                200,
                json={"repositories": [project], "total": 1, "page": 1, "page_size": 20},
            )
        return httpx.Response(200, json=project)

    with _mock_http(handler):
        result = runner.invoke(app, ["project", "select", "ae8f8620", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["id"] == project["id"]


def test_project_select_unknown_id_exit_2(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url.path).endswith("/repositories"):
            return httpx.Response(
                200,
                json={"repositories": [], "total": 0, "page": 1, "page_size": 100},
            )
        return httpx.Response(404, json={"detail": "Repository not found"})

    with _mock_http(handler):
        result = runner.invoke(app, ["project", "select", "0000", "--json"])
    assert result.exit_code == 2, result.output
    assert json.loads(result.stdout)["exit_code"] == 2


def test_project_select_forbidden(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"detail": "Not allowed"})

    with _mock_http(handler):
        result = runner.invoke(app, ["project", "select", "1111", "--json"])
    assert result.exit_code == 3, result.output


def test_project_add_aliases_create(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={
                "id": "11111111-2222-3333-4444-555555555555",
                "name": "acme/infra",
                "url": "https://github.com/acme/infra",
                "default_branch": "main",
            },
        )

    with _mock_http(handler):
        result = runner.invoke(app, ["project", "add", "https://github.com/acme/infra", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["name"] == "acme/infra"


def test_debug_flag_accepted(isolated_env):
    result = runner.invoke(app, ["--debug", "auth", "status", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["authenticated"] is False
