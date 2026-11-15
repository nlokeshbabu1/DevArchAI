"""Hybrid rate limiting policy and security behavior."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.core.security import hash_email
from app.middleware.rate_limiting.client_ip import get_client_ip
from app.middleware.rate_limiting.policy import normalize_route, build_rate_limit_specs, EndpointCategory
from app.middleware.rate_limiting.sliding_window import RateLimitSpec, check_sliding_window, make_redis_key


class TestRouteNormalization:
    def test_scan_id_not_bypass_poll_limit(self):
        t1, c1 = normalize_route("/api/v1/scans/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/progress")
        t2, c2 = normalize_route("/api/v1/scans/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/progress")
        assert t1 == t2 == "/api/v1/scans/{scan_id}/progress"
        assert c1 == c2 == EndpointCategory.SCAN_POLL


class TestIdentityBuckets:
    def test_two_users_same_ip_get_different_user_keys(self):
        req_a = MagicMock()
        req_a.method = "GET"
        req_a.headers = {"Authorization": "Bearer fake"}
        req_a.url.path = "/api/v1/dashboard"

        req_b = MagicMock()
        req_b.method = "GET"
        req_b.headers = {"Authorization": "Bearer fake2"}
        req_b.url.path = "/api/v1/dashboard"

        with patch("app.middleware.rate_limiting.policy.decode_token", side_effect=[
            {"type": "access", "sub": "user-a"},
            {"type": "access", "sub": "user-b"},
        ]):
            with patch("app.middleware.rate_limiting.policy.get_client_ip", return_value="1.2.3.4"):
                specs_a = build_rate_limit_specs(req_a, "/api/v1/dashboard", EndpointCategory.GENERAL)
                specs_b = build_rate_limit_specs(req_b, "/api/v1/dashboard", EndpointCategory.GENERAL)

        user_keys_a = [s.redis_key for s in specs_a if s.identity_kind == "user"]
        user_keys_b = [s.redis_key for s in specs_b if s.identity_kind == "user"]
        assert user_keys_a != user_keys_b

    def test_user_key_stable_across_ip(self):
        req = MagicMock()
        req.method = "GET"
        req.headers = {"Authorization": "Bearer x"}
        req.url.path = "/api/v1/repos"

        with patch("app.middleware.rate_limiting.policy.decode_token", return_value={"type": "access", "sub": "uid-1"}):
            with patch("app.middleware.rate_limiting.policy.get_client_ip", return_value="9.9.9.9"):
                specs1 = build_rate_limit_specs(req, "/api/v1/repos", EndpointCategory.GENERAL)
            with patch("app.middleware.rate_limiting.policy.get_client_ip", return_value="8.8.8.8"):
                specs2 = build_rate_limit_specs(req, "/api/v1/repos", EndpointCategory.GENERAL)

        assert specs1[0].redis_key == specs2[0].redis_key


class TestAccountKeyPrivacy:
    def test_login_account_key_uses_hash_not_email(self):
        email = "victim@example.com"
        account_id = hash_email(email)
        key = make_redis_key("login_account", "account", account_id, "/api/v1/auth/login")
        assert email not in key
        assert "@" not in key
        assert account_id in key


class TestTrustedProxy:
    def test_spoofed_forwarded_headers_ignored_without_trusted_proxy(self):
        scope = {"client": ("203.0.113.50", 12345), "headers": []}
        request = MagicMock()
        request.client.host = "203.0.113.50"
        request.headers = {"X-Forwarded-For": "1.1.1.1"}
        with patch.object(settings, "TRUSTED_PROXY_CIDRS", []):
            assert get_client_ip(request) == "203.0.113.50"

    def test_forwarded_for_honored_when_peer_is_trusted(self):
        request = MagicMock()
        request.client.host = "10.0.0.1"
        request.headers = {"X-Forwarded-For": "198.51.100.10, 10.0.0.1"}
        with patch.object(settings, "TRUSTED_PROXY_CIDRS", ["10.0.0.0/8"]):
            assert get_client_ip(request) == "198.51.100.10"


@pytest.mark.asyncio
async def test_sliding_window_concurrent_mock():
    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[0, 0, True, True])

    mock_redis = MagicMock()
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    spec = RateLimitSpec(
        redis_key="ratelimit:v2:test:ip:x:/path",
        max_requests=5,
        window_seconds=60,
        category="test",
        identity_kind="ip",
    )

    with patch("app.middleware.rate_limiting.sliding_window.get_redis", AsyncMock(return_value=mock_redis)):
        result = await check_sliding_window(spec)
        assert result.allowed is True
        mock_redis.pipeline.assert_called()


class TestRateLimitResponses:
    @pytest.fixture
    def _app(self):
        from app.middleware.security import RateLimitMiddleware

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/api/v1/repos")
        async def repos():
            return {"ok": True}

        return app

    def test_429_includes_headers(self, _app):
        client = TestClient(_app, raise_server_exceptions=False)
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 999, True, True])
        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_redis.zrem = AsyncMock()
        mock_cache = MagicMock()
        mock_cache._connected = True
        mock_cache._redis = mock_redis

        with patch("app.cache.redis_cache.get_cache", AsyncMock(return_value=mock_cache)):
            with patch("app.middleware.rate_limiting.policy.get_client_ip", return_value="7.7.7.7"):
                resp = client.get("/api/v1/repos")
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert resp.headers.get("X-RateLimit-Limit")
        assert resp.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


class TestMonthlyEntitlementsUntouched:
    """Beta/monthly quotas remain in usage_enforcement, not the HTTP limiter."""

    def test_usage_enforcement_still_exports_monthly_scan_limit(self):
        from app.services import usage_enforcement

        assert hasattr(usage_enforcement, "enforce_scan_monthly_limit")
        assert hasattr(usage_enforcement, "enforce_concurrent_scan_limit")