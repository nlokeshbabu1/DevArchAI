"""Security middleware for rate limiting, session validation, brute force protection, and security headers."""

from __future__ import annotations

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.config import settings
from app.core.security import decode_token
from app.middleware.rate_limiting.policy import evaluate_request_limits, is_sensitive_failure
from app.middleware.rate_limiting.sliding_window import (
    enforce_specs,
    rate_limit_json_response,
    service_unavailable_response,
)

logger = structlog.get_logger(__name__)

# Backward-compatible exports for tests and documentation.
_AUTH_PATHS = frozenset({
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/github/callback",
    "/api/v1/auth/gitlab/callback",
})
_REFRESH_PATH = "/api/v1/auth/refresh"
_SKIP_RATE_LIMIT_PATHS = frozenset({
    "/api/v1/health",
    "/api/v1/ready",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
})


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed hybrid rate limiter (user + IP + route category buckets)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        specs, route_template, category = evaluate_request_limits(request)
        if not specs:
            return await call_next(request)

        try:
            blocked = await enforce_specs(specs)
            if blocked is not None:
                return rate_limit_json_response(blocked)
        except Exception as exc:
            sensitive = any(is_sensitive_failure(s.category) for s in specs) or category.value in {
                "login",
                "register",
                "refresh",
                "password_reset",
            }
            logger.error(
                "rate_limit_redis_failure",
                route_template=route_template,
                category=category.value,
                error_type=type(exc).__name__,
                fail_closed=sensitive,
            )
            if sensitive:
                return service_unavailable_response()
            return service_unavailable_response()

        response = await call_next(request)
        user_specs = [s for s in specs if s.identity_kind == "user"]
        if user_specs and hasattr(response, "headers"):
            response.headers["X-RateLimit-Policy"] = user_specs[0].category
        return response


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
    """Validate session exists and is not revoked/expired on authenticated requests."""

    SKIP_PATHS = {
        "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh",
        "/api/v1/auth/github/url", "/api/v1/auth/github/callback",
        "/api/v1/health", "/api/v1/ready", "/", "/health",
        "/docs", "/redoc", "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if path.startswith("/ws/"):
            return await call_next(request)

        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            payload = decode_token(token)
            if payload is None or payload.get("type") != "access":
                logger.warning("invalid_token", path=path)
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "INVALID_TOKEN", "message": "Invalid or expired token"}},
                    headers={"WWW-Authenticate": "Bearer"},
                )
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

        return await call_next(request)