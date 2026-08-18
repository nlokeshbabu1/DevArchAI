"""Unit tests for Redis-backed rate limiter middleware."""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse


# ---------------------------------------------------------------------------
# RateLimitMiddleware — unit tests with fake Redis
# ---------------------------------------------------------------------------

class TestRateLimitMiddleware:
    """Tests for the Redis-backed sliding window rate limiter."""

    @pytest.fixture
    def _app(self):
        from app.middleware.security import RateLimitMiddleware
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/api/v1/repos")
        async def repos():
            return {"repos": []}

        @app.get("/api/v1/auth/login")
        async def login():
            return {"token": "x"}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/docs")
        async def docs():
            return {"docs": True}

        return app

    def test_health_check_skips_rate_limiting(self, _app):
        """Health checks bypass the rate limiter entirely."""
        client = TestClient(_app, raise_server_exceptions=False)
        for _ in range(150):
            resp = client.get("/health")
        assert resp.status_code == 200

    def test_docs_skips_rate_limiting(self, _app):
        """Swagger/docs endpoints bypass rate limiting."""
        client = TestClient(_app, raise_server_exceptions=False)
        for _ in range(150):
            resp = client.get("/docs")
        assert resp.status_code == 200

    def test_under_limit_returns_200(self, _app):
        """Requests under the rate limit pass through."""
        client = TestClient(_app, raise_server_exceptions=False)
        resp = client.get("/api/v1/repos")
        assert resp.status_code == 200

    def test_middleware_class_exists(self):
        """RateLimitMiddleware is importable."""
        from app.middleware.security import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    def test_auth_paths_defined(self):
        """Auth paths frozenset contains expected paths."""
        from app.middleware.security import _AUTH_PATHS
        assert "/api/v1/auth/login" in _AUTH_PATHS
        assert "/api/v1/auth/register" in _AUTH_PATHS
        assert "/api/v1/auth/refresh" in _AUTH_PATHS
        assert "/api/v1/auth/github/callback" in _AUTH_PATHS

    def test_skip_paths_defined(self):
        """Skip paths frozenset contains health/docs paths."""
        from app.middleware.security import _SKIP_RATE_LIMIT_PATHS
        assert "/health" in _SKIP_RATE_LIMIT_PATHS
        assert "/docs" in _SKIP_RATE_LIMIT_PATHS
        assert "/openapi.json" in _SKIP_RATE_LIMIT_PATHS

    def test_rate_limit_config_exists(self):
        """Rate limit settings are defined."""
        from app.config import settings
        assert hasattr(settings, 'RATE_LIMIT_REQUESTS')
        assert hasattr(settings, 'RATE_LIMIT_WINDOW')
        assert hasattr(settings, 'RATE_LIMIT_AUTH_REQUESTS')
        assert hasattr(settings, 'RATE_LIMIT_AUTH_WINDOW')
        assert settings.RATE_LIMIT_REQUESTS > 0
        assert settings.RATE_LIMIT_AUTH_REQUESTS > 0

    @pytest.mark.asyncio
    async def test_sliding_window_under_limit(self):
        """Mock test: sliding window allows requests under limit."""
        from app.middleware.security import RateLimitMiddleware
        middleware = RateLimitMiddleware(app=FastAPI())
        request = MagicMock()
        request.url.path = "/api/v1/repos"
        request.client.host = "10.0.0.1"
        request.headers = {}
        request.scope = {"client": ("10.0.0.1", 0)}

        # Pipeline ops are NOT awaited (buffered), only execute() is awaited
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 5, True, True])

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        mock_cache = MagicMock()
        mock_cache.is_connected = True
        mock_cache._redis = mock_redis

        response = MagicMock()
        response.status_code = 200

        async def call_next(r):
            return response

        with patch("app.cache.redis_cache.get_cache", new_callable=AsyncMock, return_value=mock_cache):
            result = await middleware.dispatch(request, call_next)
            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_sliding_window_over_limit_returns_429(self):
        """Mock test: sliding window returns 429 when over limit."""
        from app.middleware.security import RateLimitMiddleware
        middleware = RateLimitMiddleware(app=FastAPI())
        request = MagicMock()
        request.url.path = "/api/v1/repos"
        request.client.host = "10.0.0.1"
        request.headers = {}
        request.scope = {"client": ("10.0.0.1", 0)}

        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 101, True, True])

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_redis.zrem = AsyncMock()

        mock_cache = MagicMock()
        mock_cache.is_connected = True
        mock_cache._redis = mock_redis

        response = MagicMock()
        response.status_code = 200

        async def call_next(r):
            return response

        with patch("app.cache.redis_cache.get_cache", new_callable=AsyncMock, return_value=mock_cache):
            result = await middleware.dispatch(request, call_next)
            assert result.status_code == 429
            assert "Retry-After" in result.headers

    @pytest.mark.asyncio
    async def test_auth_endpoint_uses_auth_limit(self):
        """Mock test: auth endpoints use the stricter auth limit."""
        from app.middleware.security import RateLimitMiddleware
        middleware = RateLimitMiddleware(app=FastAPI())
        request = MagicMock()
        request.url.path = "/api/v1/auth/login"
        request.client.host = "10.0.0.2"
        request.headers = {}
        request.scope = {"client": ("10.0.0.2", 0)}

        # Auth limit = 10. ZCARD returns 10 (at limit) => should 429
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 10, True, True])

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_redis.zrem = AsyncMock()  # awaited in over-limit path

        mock_cache = MagicMock()
        mock_cache.is_connected = True
        mock_cache._redis = mock_redis

        response = MagicMock()
        response.status_code = 200

        async def call_next(r):
            return response

        with patch("app.cache.redis_cache.get_cache", new_callable=AsyncMock, return_value=mock_cache):
            result = await middleware.dispatch(request, call_next)
            assert result.status_code == 429

    @pytest.mark.asyncio
    async def test_redis_unavailable_returns_503(self):
        """Mock test: Redis down returns 503 (fail closed)."""
        from app.middleware.security import RateLimitMiddleware
        middleware = RateLimitMiddleware(app=FastAPI())
        request = MagicMock()
        request.url.path = "/api/v1/repos"
        request.client.host = "10.0.0.3"
        request.headers = {}
        request.scope = {"client": ("10.0.0.3", 0)}

        mock_cache = MagicMock()
        mock_cache.is_connected = False
        mock_cache._redis = None

        response = MagicMock()
        response.status_code = 200

        async def call_next(r):
            return response

        with patch("app.cache.redis_cache.get_cache", new_callable=AsyncMock, return_value=mock_cache):
            result = await middleware.dispatch(request, call_next)
            assert result.status_code == 503

    @pytest.mark.asyncio
    async def test_redis_exception_returns_503(self):
        """Mock test: Redis exception returns 503 (fail closed)."""
        from app.middleware.security import RateLimitMiddleware
        middleware = RateLimitMiddleware(app=FastAPI())
        request = MagicMock()
        request.url.path = "/api/v1/repos"
        request.client.host = "10.0.0.4"
        request.headers = {}
        request.scope = {"client": ("10.0.0.4", 0)}

        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(side_effect=RuntimeError("connection lost"))

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        mock_cache = MagicMock()
        mock_cache.is_connected = True
        mock_cache._redis = mock_redis

        response = MagicMock()
        response.status_code = 200

        async def call_next(r):
            return response

        with patch("app.cache.redis_cache.get_cache", new_callable=AsyncMock, return_value=mock_cache):
            result = await middleware.dispatch(request, call_next)
            assert result.status_code == 503


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------

class TestSecurityHeadersMiddleware:
    """Tests for security headers attachment."""

    @pytest.fixture
    def _app(self):
        from app.middleware.security import SecurityHeadersMiddleware
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_route():
            return {"test": True}

        return app

    def test_security_headers_present(self, _app):
        """All standard security headers are attached to responses."""
        client = TestClient(_app, raise_server_exceptions=False)
        resp = client.get("/test")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert "X-Frame-Options" in resp.headers
        assert "X-XSS-Protection" in resp.headers
        assert "Referrer-Policy" in resp.headers
        assert "Permissions-Policy" in resp.headers

    def test_csp_header_present(self, _app):
        """Content-Security-Policy header is set."""
        client = TestClient(_app, raise_server_exceptions=False)
        resp = client.get("/test")
        assert "Content-Security-Policy" in resp.headers

    def test_hsts_header_present(self, _app):
        """Strict-Transport-Security header is set."""
        client = TestClient(_app, raise_server_exceptions=False)
        resp = client.get("/test")
        assert "Strict-Transport-Security" in resp.headers


# ---------------------------------------------------------------------------
# SessionValidationMiddleware
# ---------------------------------------------------------------------------

class TestSessionValidationMiddleware:
    """Tests for session/JWT validation middleware."""

    @pytest.fixture
    def _app(self):
        from app.middleware.security import SessionValidationMiddleware
        app = FastAPI()
        app.add_middleware(SessionValidationMiddleware)

        @app.get("/api/v1/repos")
        async def repos():
            return {"repos": []}

        @app.get("/api/v1/auth/login")
        async def login():
            return {"token": "x"}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        return app

    def test_auth_endpoints_skip_validation(self, _app):
        """Auth endpoints skip session validation."""
        client = TestClient(_app, raise_server_exceptions=False)
        resp = client.get("/api/v1/auth/login")
        assert resp.status_code == 200

    def test_health_skips_validation(self, _app):
        """Health check skips session validation."""
        client = TestClient(_app, raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_no_token_passes_through(self, _app):
        """Protected endpoint without token passes through (middleware validates existing tokens only)."""
        client = TestClient(_app, raise_server_exceptions=False)
        resp = client.get("/api/v1/repos")
        assert resp.status_code == 200
