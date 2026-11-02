"""Phase 1 authentication, cookie, JWT, OAuth state, and WebSocket security tests."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket
from jose import jwt
from pydantic import ValidationError
from starlette.websockets import WebSocketState

from app.config import Settings
from app.core.oauth_state import generate_oauth_state_sync, validate_oauth_state_sync
from app.core.security import (
    JWT_AUDIENCE,
    JWT_ISSUER,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.websocket_auth import (
    _parse_auth_message,
    _reject_query_string_credentials,
    is_websocket_origin_allowed,
)


class TestProductionCookieValidation:
    def test_production_rejects_insecure_cookies(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 40)
        monkeypatch.setenv("COOKIE_SECURE", "false")
        monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')
        with pytest.raises(ValidationError):
            Settings()

    def test_production_rejects_wildcard_cors(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 40)
        monkeypatch.setenv("COOKIE_SECURE", "true")
        monkeypatch.setenv("CORS_ORIGINS", '["*"]')
        with pytest.raises(ValidationError):
            Settings()

    def test_development_allows_insecure_cookies(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", "a" * 40)
        monkeypatch.setenv("COOKIE_SECURE", "false")
        settings = Settings()
        assert settings.COOKIE_SECURE is False


class TestJwtValidation:
    def test_refresh_token_rejected_as_access(self):
        token = create_refresh_token({"sub": "00000000-0000-0000-0000-000000000001"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_wrong_algorithm_rejected(self):
        from app.config import settings

        token = jwt.encode(
            {
                "sub": "user",
                "type": "access",
                "iss": JWT_ISSUER,
                "aud": JWT_AUDIENCE,
                "exp": datetime.now(UTC) + timedelta(minutes=5),
                "iat": datetime.now(UTC),
                "jti": "abc",
            },
            settings.SECRET_KEY,
            algorithm="HS384",
        )
        assert decode_token(token) is None

    @pytest.mark.asyncio
    async def test_access_token_type_required_for_api_user_resolution(self):
        from uuid import uuid4

        from app.core.security import get_current_user_from_token
        from app.db.session import get_sync_session_factory

        refresh = create_refresh_token({"sub": str(uuid4())})
        sync_db = get_sync_session_factory()()
        user = await get_current_user_from_token(refresh, sync_db)
        assert user is None
        sync_db.close()


class TestOAuthState:
    def test_state_single_use(self):
        state = generate_oauth_state_sync()
        assert validate_oauth_state_sync(state) is True
        assert validate_oauth_state_sync(state) is False

    def test_missing_state_invalid(self):
        assert validate_oauth_state_sync("not-registered") is False


class TestWebSocketAuthMessage:
    def test_parse_auth_message_accepts_access_token(self):
        raw = json.dumps({"type": "auth", "access_token": "jwt-here"})
        creds = _parse_auth_message(raw)
        assert creds is not None
        assert creds.access_token == "jwt-here"

    def test_parse_auth_rejects_non_auth_type(self):
        raw = json.dumps({"type": "ping"})
        assert _parse_auth_message(raw) is None

    def test_query_string_credentials_rejected(self):
        ws = MagicMock(spec=WebSocket)
        ws.query_params = {"token": "leaked"}
        ws.url.path = "/ws/scan/abc"
        assert _reject_query_string_credentials(ws) is True

    def test_origin_allowlist(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "CORS_ORIGINS", ["http://localhost:5174"])
        assert is_websocket_origin_allowed("http://localhost:5174") is True
        assert is_websocket_origin_allowed("http://evil.example") is False
        assert is_websocket_origin_allowed(None) is True


class TestCookieHelpers:
    def test_refresh_cookie_set_and_clear_use_matching_path(self):
        from fastapi import Response

        from app.config import settings
        from app.core.cookie_settings import clear_refresh_cookie, refresh_cookie_name, refresh_cookie_params, set_refresh_cookie

        response = Response()
        set_refresh_cookie(response, "opaque-refresh-value")
        params = refresh_cookie_params()
        cookie_name = refresh_cookie_name()
        set_cookie = response.headers.get("set-cookie", "")
        assert f"{cookie_name}=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert params["path"] in set_cookie

        cleared = Response()
        clear_refresh_cookie(cleared)
        delete_cookie = cleared.headers.get("set-cookie", "")
        assert cookie_name in delete_cookie or "refresh_token" in delete_cookie
        assert params["path"] in delete_cookie


@pytest.mark.asyncio
async def test_receive_websocket_credentials_rejects_query_token():
    from app.core.websocket_auth import receive_websocket_credentials

    ws = AsyncMock(spec=WebSocket)
    ws.headers = {"origin": "http://localhost:5174"}
    ws.query_params = {"token": "secret"}
    ws.url.path = "/ws/scan/x"
    ws.close = AsyncMock()

    result = await receive_websocket_credentials(ws)
    assert result is None
    ws.close.assert_awaited()
    ws.accept.assert_not_awaited()


@pytest.mark.asyncio
async def test_authenticate_scan_websocket_auth_timeout():
    from app.core.websocket_auth import receive_websocket_credentials

    ws = AsyncMock(spec=WebSocket)
    ws.headers = {}
    ws.query_params = {}
    ws.url.path = "/ws/scan/x"
    ws.accept = AsyncMock()
    ws.close = AsyncMock()

    async def slow_receive():
        raise TimeoutError

    with patch("app.core.websocket_auth.asyncio.wait_for", side_effect=TimeoutError):
        creds = await receive_websocket_credentials(ws)
    assert creds is None
    ws.close.assert_awaited()
