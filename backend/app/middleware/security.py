"""Security middleware for rate limiting, session validation, brute force protection, and security headers."""

from __future__ import annotations

import time
from collections import defaultdict

import structlog
from fastapi import Request, Response
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.config import settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter.

    Uses in-memory storage. For distributed rate limiting, use Redis.
    Limits are per-IP per-route.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._windows: dict[str, list[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if settings.ENVIRONMENT != "production":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        route_path = request.url.path
        window_key = f"{client_ip}:{route_path}"

        now = time.time()
        window_start = now - settings.RATE_LIMIT_WINDOW

        self._windows[window_key] = [
            t for t in self._windows[window_key] if t > window_start
        ]

        if len(self._windows[window_key]) >= settings.RATE_LIMIT_REQUESTS:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=route_path,
            )
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                    }
                },
                headers={"Retry-After": str(settings.RATE_LIMIT_WINDOW)},
            )

        self._windows[window_key].append(now)
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
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.github.com"
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

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if settings.ENVIRONMENT != "production":
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(skip) for skip in self.SKIP_PATHS) or path.startswith("/ws/"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                jti = payload.get("jti")
                if jti:
                    from app.services.token_blacklist import is_blacklisted
                    if await is_blacklisted(jti):
                        logger.warning("Session validation failed: token blacklisted", path=path, jti=jti[:8])
                        from fastapi.responses import JSONResponse
                        return JSONResponse(
                            status_code=401,
                            content={"error": {"code": "TOKEN_BLACKLISTED", "message": "Token has been revoked"}},
                            headers={"WWW-Authenticate": "Bearer"},
                        )
            except JWTError:
                logger.warning("Session validation failed: invalid token", path=path)
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "INVALID_TOKEN", "message": "Invalid or expired token"}},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return await call_next(request)
