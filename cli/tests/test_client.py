"""Tests for the API client: auth headers, error mapping, retries."""

from __future__ import annotations

import httpx
import pytest

from devsec.api.client import ApiClient
from devsec.config import Config
from devsec.utils.errors import ApiError, AuthError, ConfigError, ExitCode


def _config(tmp_path, token: str = "") -> Config:
    return Config(
        config_file=tmp_path / "config.toml",
        env={
            "DEVSEC_API_URL": "http://127.0.0.1:8000",
            "DEVSEC_API_TOKEN": token,
        },
    )


def test_api_key_sent_as_x_api_key(tmp_path):
    cfg = _config(tmp_path, "dk_secret_token_123")
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        return httpx.Response(200, json={"ok": True})

    client = ApiClient(cfg, transport=httpx.MockTransport(handler))
    client.get_json("/auth/me")
    assert seen["headers"]["X-API-Key"] == "dk_secret_token_123"
    assert "Authorization" not in seen["headers"]


def test_jwt_sent_as_bearer(tmp_path):
    cfg = _config(tmp_path, "jwt.token.abc")
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        return httpx.Response(200, json={"ok": True})

    client = ApiClient(cfg, transport=httpx.MockTransport(handler))
    client.get_json("/auth/me")
    assert seen["headers"]["Authorization"] == "Bearer jwt.token.abc"


def test_no_token_no_auth_header(tmp_path):
    cfg = _config(tmp_path)
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        return httpx.Response(401, json={"detail": "Not authenticated"})

    client = ApiClient(cfg, transport=httpx.MockTransport(handler))
    with pytest.raises(AuthError) as exc_info:
        client.get_json("/auth/me")
    assert "X-API-Key" not in seen["headers"]
    assert exc_info.value.exit_code == ExitCode.AUTH
    assert exc_info.value.status_code == 401


def test_401_maps_to_auth_error_with_request_id(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "bad creds"}, headers={"X-Request-ID": "req-42"})

    client = ApiClient(_config(tmp_path, "dk_x"), transport=httpx.MockTransport(handler))
    with pytest.raises(AuthError) as exc_info:
        client.get_json("/auth/me")
    assert exc_info.value.request_id == "req-42"
    assert exc_info.value.hint is not None


def test_500_maps_to_api_error_with_server_message(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "internal explosion"})

    client = ApiClient(_config(tmp_path, "dk_x"), transport=httpx.MockTransport(handler))
    with pytest.raises(ApiError) as exc_info:
        client.get_json("/scans/1")
    assert exc_info.value.message == "internal explosion"
    assert exc_info.value.status_code == 500
    assert exc_info.value.exit_code == ExitCode.API


def test_validation_error_detail_is_joined(tmp_path):
    body = {"detail": [{"loc": ["body", "url"], "msg": "invalid url", "type": "value_error"}]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json=body)

    client = ApiClient(_config(tmp_path, "dk_x"), transport=httpx.MockTransport(handler))
    with pytest.raises(ApiError) as exc_info:
        client.post_json("/repositories", payload={"url": "nope"})
    assert "url" in exc_info.value.message


def test_legacy_error_object_shape_is_parsed(tmp_path):
    body = {"error": {"code": "HTTP_401", "message": "Could not validate credentials"}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json=body)

    client = ApiClient(_config(tmp_path, "dk_x"), transport=httpx.MockTransport(handler))
    with pytest.raises(AuthError) as exc_info:
        client.get_json("/auth/me")
    assert "Could not validate credentials" in exc_info.value.message


def test_retry_on_503_then_success(tmp_path):
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(503, json={"detail": "unavailable"})
        return httpx.Response(200, json={"recovered": True})

    client = ApiClient(
        _config(tmp_path, "dk_x"), max_retries=2, transport=httpx.MockTransport(handler)
    )
    assert client.get_json("/repositories") == {"recovered": True}
    assert calls["count"] == 3


def test_no_retry_after_max_attempts(tmp_path):
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(503, json={"detail": "unavailable"})

    client = ApiClient(
        _config(tmp_path, "dk_x"), max_retries=1, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(ApiError) as exc_info:
        client.get_json("/repositories")
    assert calls["count"] == 2  # initial + 1 retry
    assert exc_info.value.status_code == 503


def test_post_is_not_retried(tmp_path):
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(503, json={"detail": "unavailable"})

    client = ApiClient(
        _config(tmp_path, "dk_x"), max_retries=3, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(ApiError):
        client.post_json("/repositories", payload={"url": "x"})
    assert calls["count"] == 1


def test_409_maps_to_api_error_with_hint(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": "Already exists"})

    client = ApiClient(_config(tmp_path, "dk_x"), transport=httpx.MockTransport(handler))
    with pytest.raises(ApiError) as exc_info:
        client.post_json("/repositories", payload={"url": "x"})
    assert exc_info.value.status_code == 409
    assert exc_info.value.exit_code == ExitCode.API
    assert exc_info.value.hint is not None


def test_404_maps_to_api_error(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Repository not found"})

    client = ApiClient(_config(tmp_path, "dk_x"), transport=httpx.MockTransport(handler))
    with pytest.raises(ApiError) as exc_info:
        client.get_json("/repositories/unknown")
    assert exc_info.value.status_code == 404
    assert exc_info.value.exit_code == ExitCode.API


def test_network_error_maps_to_api_error(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = ApiClient(_config(tmp_path, "dk_x"), transport=httpx.MockTransport(handler))
    with pytest.raises(ApiError) as exc_info:
        client.get_json("/auth/me")
    assert "Unable to reach the API" in exc_info.value.message
    assert exc_info.value.exit_code == ExitCode.API


def test_timeout_maps_to_api_error(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    client = ApiClient(_config(tmp_path, "dk_x"), transport=httpx.MockTransport(handler))
    with pytest.raises(ApiError) as exc_info:
        client.get_json("/auth/me")
    assert "timed out" in exc_info.value.message
    assert exc_info.value.exit_code == ExitCode.API


def test_token_never_appears_in_error(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Not authenticated"})

    client = ApiClient(
        _config(tmp_path, "dk_should_not_leak_abc123"), transport=httpx.MockTransport(handler)
    )
    with pytest.raises(AuthError) as exc_info:
        client.get_json("/auth/me")
    assert "dk_should_not_leak_abc123" not in str(exc_info.value)
    assert "dk_should_not_leak_abc123" not in str(exc_info.value.hint)


def test_invalid_api_url_raises_config_error(tmp_path):
    cfg = Config(
        config_file=tmp_path / "config.toml",
        env={"DEVSEC_API_URL": "not-a-url", "DEVSEC_API_TOKEN": ""},
    )
    with pytest.raises(ConfigError):
        ApiClient(cfg)
