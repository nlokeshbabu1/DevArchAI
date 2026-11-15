"""CLI browser login (mocked)."""

from __future__ import annotations

from unittest.mock import patch

import httpx
from typer.testing import CliRunner

from devsec.config import DEFAULT_API_URL
from devsec.main import app

runner = CliRunner()


def test_default_production_api_url():
    assert DEFAULT_API_URL == "https://backend.devarchai.xyz"


def test_pkce_challenge_is_deterministic():
    from devsec.auth.pkce import challenge_from_verifier

    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert challenge_from_verifier(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_prompt_login_method_browser():
    from devsec.api.auth import _prompt_login_method

    with patch("devsec.api.auth.typer.prompt", return_value="1"):
        assert _prompt_login_method() == "browser"


def test_prompt_login_method_api_key():
    from devsec.api.auth import _prompt_login_method

    with patch("devsec.api.auth.typer.prompt", side_effect=["nope", "2"]):
        assert _prompt_login_method() == "api_key"


def test_prompt_api_key_reads_hidden_input(isolated_env):
    from devsec.api.auth import _prompt_api_key
    from devsec.commands.base import make_client

    config, _client = make_client()
    with patch("devsec.api.auth.typer.prompt", return_value="sk-pasted-key") as prompt_mock:
        assert _prompt_api_key(config) == "sk-pasted-key"
    assert prompt_mock.call_args.kwargs["hide_input"] is True


def test_login_with_api_key_unchanged(isolated_env):
    key = "sk-9PcnoNLxSP4CQpTufHEHWvscHl744CVAMEUHcL440o"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == key
        return httpx.Response(200, json={"id": "1", "email": "user@example.com"})

    original_client = httpx.Client

    def client_factory(**kwargs):  # type: ignore[no-untyped-def]
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    with patch("devsec.api.client.httpx.Client", client_factory):
        result = runner.invoke(app, ["auth", "login", "--api-key", key, "--json"])
    assert result.exit_code == 0, result.output


def test_browser_login_stores_cli_session(isolated_env, tmp_path):
    from devsec.api.client import ApiClient
    from devsec.commands.base import make_client

    config, _client = make_client()
    config.save_cli_session(
        {
            "access_token": "jwt-access",
            "refresh_token": "opaque-refresh",
            "expires_at": 9999999999,
            "email": "cli@example.com",
            "device_name": "test-host",
        }
    )
    assert config.token == "jwt-access"
    assert config.token_source == "cli-session"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization", "").startswith("Bearer ")
        return httpx.Response(200, json={"id": "1", "email": "cli@example.com", "username": "cli"})

    original_client = httpx.Client

    def client_factory(**kwargs):  # type: ignore[no-untyped-def]
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    with patch("devsec.api.client.httpx.Client", client_factory):
        client = ApiClient(config)
        try:
            payload = client.get_json("/auth/me")
        finally:
            client.close()
    assert payload["email"] == "cli@example.com"
