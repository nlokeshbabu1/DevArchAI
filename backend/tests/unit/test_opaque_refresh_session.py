"""Opaque refresh sessions, rotation, and cookie security tests."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.cookie_settings import refresh_cookie_params
from app.core.security import create_access_token, decode_token
from app.services.refresh_session_service import (
    generate_opaque_refresh_token,
    rotate_refresh_session,
)
from app.services.token_blacklist import access_token_blacklist_ttl


class TestOpaqueRefreshToken:
    def test_generate_is_not_jwt(self):
        token = generate_opaque_refresh_token()
        assert token.count(".") != 2
        assert len(token) >= 32


class TestAccessJwt:
    def test_fifteen_minute_expiry_configured(self):
        from app.config import settings

        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15

    def test_access_token_has_type_and_jti(self):
        token = create_access_token({"sub": str(uuid4())})
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "access"
        assert payload.get("jti")


class TestRefreshCookieAttributes:
    def test_cookie_params_http_only(self):
        params = refresh_cookie_params()
        assert params["httponly"] is True


class TestRotationLock:
    @pytest.mark.asyncio
    async def test_concurrent_rotation_second_gets_429(self):
        user_id = uuid4()
        raw = generate_opaque_refresh_token()
        user = MagicMock()
        user.id = user_id
        user.is_active = True

        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="127.0.0.1")

        db = AsyncMock()
        session = MagicMock()
        session.revoked = False
        session.expires_at = None
        session.token_family = str(uuid4())

        with patch(
            "app.services.refresh_session_service._acquire_rotation_lock",
            new_callable=AsyncMock,
            side_effect=[True, False],
        ), patch(
            "app.services.refresh_session_service._find_session_for_token",
            new_callable=AsyncMock,
            return_value=session,
        ), patch(
            "app.services.refresh_session_service.create_refresh_session",
            new_callable=AsyncMock,
            return_value=(MagicMock(), generate_opaque_refresh_token()),
        ), patch(
            "app.services.refresh_session_service._release_rotation_lock",
            new_callable=AsyncMock,
        ):
            await rotate_refresh_session(db, user, request, raw)
            with pytest.raises(HTTPException) as exc:
                await rotate_refresh_session(db, user, request, raw)
            assert exc.value.status_code == 429


class TestBlacklistTtl:
    def test_access_blacklist_ttl_respects_exp(self):
        from datetime import UTC, datetime, timedelta

        exp = datetime.now(UTC) + timedelta(minutes=10)
        ttl = access_token_blacklist_ttl(exp.timestamp())
        assert ttl.total_seconds() <= 600
