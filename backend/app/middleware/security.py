"""Security middleware for rate limiting, session validation, brute force protection, and security headers."""

from __future__ import annotations

import time

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.config import settings

logger = structlog.get_logger(__name__)

# Auth and security-sensitive endpoints that require stricter rate limiting
_AUTH_PATHS = frozenset({
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/github/callback",
    "/api/v1/auth/gitlab/callback",
})

# Paths that should skip rate limiting entirely (health checks, docs, etc.)
_SKIP_RATE_LIMIT_PATHS = frozenset({
    "/api/v1/health",
    "/api/v1/ready",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
})


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding window rate limiter.

    Uses atomic Redis pipeline operations for distributed rate limiting.
    Fail-closed: returns 503 if Redis is unavailable.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def _get_redis(self):
        """Get Redis connection from cache. Raises on failure for fail-closed."""
        from app.cache.redis_cache import get_cache
        cache = await get_cache()
        if not cache._connected or cache._redis is None:
            raise ConnectionError("Redis unavailable")
        return cache._redis

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        route_path = request.url.path

        # Skip rate limiting for health checks and docs
        if route_path in _SKIP_RATE_LIMIT_PATHS:
            return await call_next(request)

        # Determine rate limit config based on endpoint type
        is_auth_endpoint = route_path in _AUTH_PATHS
        if is_auth_endpoint:
            max_requests = settings.RATE_LIMIT_AUTH_REQUESTS
            window_seconds = settings.RATE_LIMIT_AUTH_WINDOW
            scope = "auth"
        else:
            max_requests = settings.RATE_LIMIT_REQUESTS
            window_seconds = settings.RATE_LIMIT_WINDOW
            scope = "general"

        now = time.time()
        window_start = now - window_seconds
        window_key = f"ratelimit:{scope}:{client_ip}:{route_path}"

        try:
            redis = await self._get_redis()

            # Atomic Redis pipeline: trim old entries, count, and optionally add
            pipe = redis.pipeline(transaction=True)
            # Remove timestamps outside the window
            pipe.zremrangebyscore(window_key, 0, window_start)
            # Count requests in current window
            pipe.zcard(window_key)
            # Add current request timestamp
            pipe.zadd(window_key, {str(now): now})
            # Set TTL on the key (auto-cleanup)
            pipe.expire(window_key, window_seconds)

            results = await pipe.execute()
            request_count = results[1]  # zcard result

            if request_count >= max_requests:
                # Remove the request we just added (over limit)
                await redis.zrem(window_key, str(now))

                logger.warning(
                    "rate_limit_exceeded",
                    client_ip=client_ip,
                    path=route_path,
                    scope=scope,
                    count=request_count,
                    limit=max_requests,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please try again later.",
                        }
                    },
                    headers={"Retry-After": str(window_seconds)},
                )

        except Exception as exc:
            # Fail closed: if Redis is unavailable, reject the request
            logger.error(
                "rate_limit_redis_failure",
                client_ip=client_ip,
                path=route_path,
                error_type=type(exc).__name__,
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "SERVICE_UNAVAILABLE",
                        "message": "Service temporarily unavailable. Please try again later.",
                    }
                },
                headers={"Retry-After": "30"},
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.github.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Cache-Control"] = "no-store"

        return response


class SessionValidationMiddleware(BaseHTTPMiddleware):
    """Validate session exists and is not revoked/expired on authenticated requests.

    Skips validation for auth endpoints (login, register, refresh, etc.)
    and public endpoints (health, docs).
    """

    SKIP_PATHS = {
        "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh",
        "/api/v1/auth/github/url", "/api/v1/auth/github/callback",
        "/api/v1/health", "/api/v1/ready", "/", "/health",
        "/docs", "/redoc", "/openapi.json",
    }

    # WebSocket paths that require authentication
    WS_AUTH_PATHS = {"/ws/cloud/", "/ws/scan/"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # WebSocket auth validation
        if any(path.startswith(ws_path) for ws_path in self.WS_AUTH_PATHS):
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            query_token = request.query_params.get("token", "")
            token = token or query_token
            if not token:
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "WS_AUTH_REQUIRED", "message": "WebSocket authentication required"}},
                )
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                jti = payload.get("jti")
                if jti:
                    from app.services.token_blacklist import BlacklistRedisError, is_blacklisted
                    try:
                        if await is_blacklisted(jti):
                            return JSONResponse(status_code=401, content={"error": {"code": "TOKEN_BLACKLISTED"}})
                    except BlacklistRedisError:
                        logger.error("auth_revocation_check_failed", path=path, jti=jti[:8], reason="redis_unavailable")
                        return JSONResponse(status_code=503, content={"error": {"code": "SERVICE_UNAVAILABLE", "message": "Service temporarily unavailable"}})
            except JWTError:
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "INVALID_TOKEN", "message": "Invalid WebSocket token"}},
                )

        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                jti = payload.get("jti")
                if jti:
                    from app.services.token_blacklist import BlacklistRedisError, is_blacklisted
                    try:
                        if await is_blacklisted(jti):
                            logger.warning("token_blacklisted", path=path, jti=jti[:8])
                            return JSONResponse(
                                status_code=401,
                                content={"error": {"code": "TOKEN_BLACKLISTED", "message": "Token has been revoked"}},
                                headers={"WWW-Authenticate": "Bearer"},
                            )
                    except BlacklistRedisError:
                        logger.error("auth_revocation_check_failed", path=path, jti=jti[:8], reason="redis_unavailable")
                        return JSONResponse(
                            status_code=503,
                            content={"error": {"code": "SERVICE_UNAVAILABLE", "message": "Service temporarily unavailable"}},
                            headers={"WWW-Authenticate": "Bearer"},
                        )
            except JWTError:
                logger.warning("invalid_token", path=path)
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "INVALID_TOKEN", "message": "Invalid or expired token"}},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return await call_next(request)
