"""Security tests for CLI PKCE browser authentication."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.cli_auth_service import (
    approve_cli_session,
    consume_code,
    register_cli_session,
    verify_pkce,
    _validate_redirect_uri,
)


@pytest.fixture
def fake_redis():
    import fakeredis.aioredis

    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_invalid_pkce_verifier_rejected():
    challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert verify_pkce("wrong-verifier-value-that-is-long-enough-1234567890ab", challenge) is False


@pytest.mark.asyncio
async def test_wrong_redirect_uri_rejected():
    with pytest.raises(ValueError, match="loopback"):
        _validate_redirect_uri("https://evil.example/callback")


@pytest.mark.asyncio
async def test_register_and_approve_flow(fake_redis):
    with patch("app.services.cli_auth_service._redis", AsyncMock(return_value=fake_redis)):
        reg = await register_cli_session(
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            code_challenge_method="S256",
            state="state-abc-123456",
            redirect_uri="http://127.0.0.1:8765/callback",
            device_name="test-cli",
        )
        redirect = await approve_cli_session(
            session_id=reg["session_id"],
            state="state-abc-123456",
            user_id="00000000-0000-4000-8000-000000000001",
        )
        assert "code=" in redirect
        assert "127.0.0.1:8765" in redirect


@pytest.mark.asyncio
async def test_invalid_state_on_approve(fake_redis):
    with patch("app.services.cli_auth_service._redis", AsyncMock(return_value=fake_redis)):
        reg = await register_cli_session(
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            code_challenge_method="S256",
            state="good-state-123456789",
            redirect_uri="http://127.0.0.1:8765/callback",
            device_name=None,
        )
        with pytest.raises(ValueError):
            await approve_cli_session(
                session_id=reg["session_id"],
                state="wrong-state-123456789",
                user_id="00000000-0000-4000-8000-000000000001",
            )


@pytest.mark.asyncio
async def test_duplicate_approve_rejected(fake_redis):
    with patch("app.services.cli_auth_service._redis", AsyncMock(return_value=fake_redis)):
        reg = await register_cli_session(
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            code_challenge_method="S256",
            state="state-dup-123456789",
            redirect_uri="http://127.0.0.1:8765/callback",
            device_name=None,
        )
        await approve_cli_session(
            session_id=reg["session_id"],
            state="state-dup-123456789",
            user_id="00000000-0000-4000-8000-000000000001",
        )
        with pytest.raises(LookupError):
            await approve_cli_session(
                session_id=reg["session_id"],
                state="state-dup-123456789",
                user_id="00000000-0000-4000-8000-000000000001",
            )


@pytest.mark.asyncio
async def test_authorization_code_single_use(fake_redis):
    with patch("app.services.cli_auth_service._redis", AsyncMock(return_value=fake_redis)):
        reg = await register_cli_session(
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            code_challenge_method="S256",
            state="state-code-123456789",
            redirect_uri="http://127.0.0.1:8765/callback",
            device_name=None,
        )
        redirect = await approve_cli_session(
            session_id=reg["session_id"],
            state="state-code-123456789",
            user_id="00000000-0000-4000-8000-000000000001",
        )
        from urllib.parse import parse_qs, urlparse

        code = parse_qs(urlparse(redirect).query)["code"][0]
        first = await consume_code(code)
        second = await consume_code(code)
        assert first is not None
        assert second is None


@pytest.mark.asyncio
async def test_expired_session_not_found(fake_redis):
    with patch("app.services.cli_auth_service._redis", AsyncMock(return_value=fake_redis)):
        with pytest.raises(LookupError):
            await approve_cli_session(
                session_id="missing-session",
                state="state",
                user_id="00000000-0000-4000-8000-000000000001",
            )