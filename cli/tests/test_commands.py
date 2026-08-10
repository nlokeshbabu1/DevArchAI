"""End-to-end CLI command tests via Typer's CliRunner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from typer.testing import CliRunner

from devsec.config import SecretStore
from devsec.main import app

runner = CliRunner()


@pytest.fixture
def isolated_env(tmp_path: Path):
    """Run CLI commands with an isolated config dir and env."""
    import os

    old_env = {k: os.environ.get(k) for k in ("DEVSEC_API_URL", "DEVSEC_API_TOKEN")}
    os.environ["XDG_CONFIG_HOME"] = str(tmp_path)
    os.environ["DEVSEC_API_URL"] = "http://127.0.0.1:59999"
    os.environ.pop("DEVSEC_API_TOKEN", None)
    yield tmp_path
    for key, value in old_env.items():
        if value is None:
            os.environ.pop(key, None)
    else:
        os.environ.update({k: v for k, v in old_env.items() if v is not None})


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
    runner.invoke(app, ["config", "set", "api-url", "http://example.com"])
    result = runner.invoke(app, ["config", "show", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["values"]["api_url"] == "http://example.com"


def test_auth_status_not_authenticated(isolated_env):
    result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["authenticated"] is False


def test_auth_login_validates_and_stores(isolated_env, tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "dk_12345test"
        return httpx.Response(200, json={"id": "1", "email": "a@b.c", "username": "u"})

    original_client = httpx.Client

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    with patch("devsec.api.client.httpx.Client", client_factory):
        result = runner.invoke(app, ["auth", "login", "--api-key", "dk_12345test", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["stored"] is True


def test_auth_login_accepts_sk_key(isolated_env, tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "sk-9PcnoNLxSP4CQpTufHEHWvscHl744CVAMEUHcL440o"
        return httpx.Response(200, json={"id": "1", "email": "a@b.c", "username": "u"})

    original_client = httpx.Client

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    with patch("devsec.api.client.httpx.Client", client_factory):
        result = runner.invoke(
            app,
            [
                "auth",
                "login",
                "--api-key",
                "sk-9PcnoNLxSP4CQpTufHEHWvscHl744CVAMEUHcL440o",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["stored"] is True


def test_auth_login_rejects_bad_format(isolated_env):
    result = runner.invoke(app, ["auth", "login", "--api-key", "wrong"])
    assert result.exit_code == 2
    assert "sk-" in result.output


def test_auth_logout_revokes_sk_key(isolated_env, tmp_path):
    store = SecretStore(config_file=tmp_path / "devsec" / "config.toml")
    store.set_token("sk-abcdef")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"message": "revoked"})

    original_client = httpx.Client

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    with patch("devsec.api.client.httpx.Client", client_factory):
        result = runner.invoke(app, ["auth", "logout", "--revoke", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["revoked"] is True
    assert seen and "/settings/api-keys/current" in seen[0]


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
    assert json.loads(result.stdout)["logged_out"] is True
    assert store.get_token() is None


def test_project_list_error_when_backend_down(isolated_env):
    result = runner.invoke(app, ["project", "list", "--json"])
    assert result.exit_code == 4
    data = json.loads(result.stdout)
    assert data["error"] == "api_error"
    assert data["exit_code"] == 4


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


def test_project_select_and_current(isolated_env, tmp_path):
    project = {
        "id": "11111111-2222-3333-4444-555555555555",
        "name": "acme/infra",
        "url": "https://github.com/acme/infra",
        "default_branch": "main",
        "is_private": False,
        "is_active": True,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=project)

    original_client = httpx.Client

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    with patch("devsec.api.client.httpx.Client", client_factory):
        result = runner.invoke(app, ["project", "select", project["id"], "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["id"] == project["id"]

    with patch("devsec.api.client.httpx.Client", client_factory):
        result = runner.invoke(app, ["project", "current", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["selected"] == project["id"]


def test_project_select_unknown_id_exit_4(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Repository not found"})

    original_client = httpx.Client

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    with patch("devsec.api.client.httpx.Client", client_factory):
        result = runner.invoke(app, ["project", "select", "0000", "--json"])
    assert result.exit_code == 4, result.output
    assert json.loads(result.stdout)["error"] == "api_error"


def test_project_add_aliases_create(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "11111111-2222-3333-4444-555555555555",
                "name": "acme/infra",
                "url": request.url.path,
                "default_branch": "main",
            },
        )

    original_client = httpx.Client

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    with patch("devsec.api.client.httpx.Client", client_factory):
        result = runner.invoke(app, ["project", "add", "https://github.com/acme/infra", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["name"] == "acme/infra"
