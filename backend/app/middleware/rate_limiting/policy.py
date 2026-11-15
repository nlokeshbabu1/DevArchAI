"""Hybrid rate-limit policy: route templates and bucket selection."""

from __future__ import annotations

import re
from enum import Enum

from fastapi import Request

from app.config import settings
from app.core.cookie_settings import read_refresh_token_from_request
from app.core.security import decode_token, hash_token
from app.middleware.rate_limiting.client_ip import get_client_ip
from app.middleware.rate_limiting.sliding_window import RateLimitSpec, make_redis_key

_SKIP_PATHS = frozenset({
    "/api/v1/health",
    "/api/v1/ready",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
})

_SENSITIVE_CATEGORIES = frozenset({
    "login_ip",
    "register_ip",
    "refresh_ip",
    "refresh_session",
    "password_reset_ip",
    "password_reset_account",
})


class EndpointCategory(str, Enum):
    SKIP = "skip"
    LOGIN = "login"
    REGISTER = "register"
    PASSWORD_RESET = "password_reset"
    REFRESH = "refresh"
    SCAN_START = "scan_start"
    SCAN_POLL = "scan_poll"
    AI_EXPLANATION = "ai_explanation"
    AI_REMEDIATION = "ai_remediation"
    REPOSITORY_SYNC = "repository_sync"
    GENERAL = "general"


_ROUTE_RULES: list[tuple[re.Pattern[str], str, EndpointCategory | None]] = [
    (re.compile(r"^/api/v1/auth/login$"), "/api/v1/auth/login", EndpointCategory.LOGIN),
    (re.compile(r"^/api/v1/auth/register$"), "/api/v1/auth/register", EndpointCategory.REGISTER),
    (re.compile(r"^/api/v1/auth/forgot-password$"), "/api/v1/auth/forgot-password", EndpointCategory.PASSWORD_RESET),
    (re.compile(r"^/api/v1/auth/reset-password$"), "/api/v1/auth/reset-password", EndpointCategory.PASSWORD_RESET),
    (re.compile(r"^/api/v1/auth/refresh$"), "/api/v1/auth/refresh", EndpointCategory.REFRESH),
    (re.compile(r"^/api/v1/auth/cli/register$"), "/api/v1/auth/cli/register", EndpointCategory.LOGIN),
    (re.compile(r"^/api/v1/auth/cli/token$"), "/api/v1/auth/cli/token", EndpointCategory.LOGIN),
    (re.compile(r"^/api/v1/auth/cli/refresh$"), "/api/v1/auth/cli/refresh", EndpointCategory.REFRESH),
    (re.compile(r"^/api/v1/auth/cli/approve$"), "/api/v1/auth/cli/approve", EndpointCategory.GENERAL),
    (re.compile(r"^/api/v1/auth/cli/revoke$"), "/api/v1/auth/cli/revoke", EndpointCategory.LOGIN),
    (re.compile(r"^/api/v1/auth/github/callback$"), "/api/v1/auth/github/callback", EndpointCategory.LOGIN),
    (re.compile(r"^/api/v1/auth/gitlab/callback$"), "/api/v1/auth/gitlab/callback", EndpointCategory.LOGIN),
    (re.compile(r"^/api/v1/scan/start$"), "/api/v1/scan/start", EndpointCategory.SCAN_START),
    (re.compile(r"^/api/v1/scans$"), "/api/v1/scans", EndpointCategory.SCAN_START),
    (re.compile(r"^/api/v1/repositories/[^/]+/scan$"), "/api/v1/repositories/{repo_id}/scan", EndpointCategory.SCAN_START),
    (re.compile(r"^/api/v1/scans/[^/]+/progress$"), "/api/v1/scans/{scan_id}/progress", EndpointCategory.SCAN_POLL),
    (re.compile(r"^/api/v1/scan/status/[^/]+$"), "/api/v1/scan/status/{scan_id}", EndpointCategory.SCAN_POLL),
    (re.compile(r"^/api/v1/github/import-repos$"), "/api/v1/github/import-repos", EndpointCategory.REPOSITORY_SYNC),
    (re.compile(r"^/api/v1/repositories$"), "/api/v1/repositories", EndpointCategory.REPOSITORY_SYNC),
    (
        re.compile(r"^/api/v1/suggestions/generate/[^/]+$"),
        "/api/v1/suggestions/generate/{finding_id}",
        EndpointCategory.AI_EXPLANATION,
    ),
    (
        re.compile(r"^/api/v1/suggestions/[^/]+/create-pr$"),
        "/api/v1/suggestions/{suggestion_id}/create-pr",
        EndpointCategory.AI_REMEDIATION,
    ),
    (
        re.compile(r"^/api/v1/suggestions/[^/]+/apply$"),
        "/api/v1/suggestions/{suggestion_id}/apply",
        EndpointCategory.AI_REMEDIATION,
    ),
    (re.compile(r"^/api/v1/github/create-pr$"), "/api/v1/github/create-pr", EndpointCategory.AI_REMEDIATION),
]


def normalize_route(path: str) -> tuple[str, EndpointCategory]:
    if path in _SKIP_PATHS:
        return path, EndpointCategory.SKIP
    for pattern, template, category in _ROUTE_RULES:
        if pattern.match(path):
            return template, category or EndpointCategory.GENERAL
    return path, EndpointCategory.GENERAL


def _resolve_user_identity(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_token(auth[7:].strip())
        if payload and payload.get("type") == "access":
            sub = payload.get("sub")
            if sub:
                return str(sub)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"ak:{hash_token(api_key)}"
    return None


def _resolve_refresh_session_identity(request: Request) -> str | None:
    raw = read_refresh_token_from_request(request)
    if not raw:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            raw = auth[7:].strip()
    if raw:
        return f"rf:{hash_token(raw)}"
    return None


def build_rate_limit_specs(
    request: Request,
    route_template: str,
    category: EndpointCategory,
) -> list[RateLimitSpec]:
    if category is EndpointCategory.SKIP:
        return []

    client_ip = get_client_ip(request)
    user_id = _resolve_user_identity(request)
    method = request.method.upper()

    specs: list[RateLimitSpec] = []

    if category is EndpointCategory.LOGIN and method == "POST":
        specs.append(
            RateLimitSpec(
                redis_key=make_redis_key("login_ip", "ip", client_ip, route_template),
                max_requests=settings.RATE_LIMIT_LOGIN_IP,
                window_seconds=settings.RATE_LIMIT_LOGIN_IP_WINDOW,
                category="login_ip",
                identity_kind="ip",
            )
        )
        return specs

    if category is EndpointCategory.REGISTER and method == "POST":
        specs.append(
            RateLimitSpec(
                redis_key=make_redis_key("register_ip", "ip", client_ip, route_template),
                max_requests=settings.RATE_LIMIT_REGISTER_IP,
                window_seconds=settings.RATE_LIMIT_REGISTER_WINDOW,
                category="register_ip",
                identity_kind="ip",
            )
        )
        return specs

    if category is EndpointCategory.PASSWORD_RESET and method == "POST":
        specs.append(
            RateLimitSpec(
                redis_key=make_redis_key("password_reset_ip", "ip", client_ip, route_template),
                max_requests=settings.RATE_LIMIT_PASSWORD_RESET_IP,
                window_seconds=settings.RATE_LIMIT_PASSWORD_RESET_IP_WINDOW,
                category="password_reset_ip",
                identity_kind="ip",
            )
        )
        return specs

    if category is EndpointCategory.REFRESH and method == "POST":
        session_id = _resolve_refresh_session_identity(request)
        specs.append(
            RateLimitSpec(
                redis_key=make_redis_key("refresh_ip", "ip", client_ip, route_template),
                max_requests=settings.RATE_LIMIT_REFRESH_IP,
                window_seconds=settings.RATE_LIMIT_REFRESH_WINDOW,
                category="refresh_ip",
                identity_kind="ip",
            )
        )
        if session_id:
            specs.append(
                RateLimitSpec(
                    redis_key=make_redis_key("refresh_session", "session", session_id, route_template),
                    max_requests=settings.RATE_LIMIT_REFRESH_USER,
                    window_seconds=settings.RATE_LIMIT_REFRESH_WINDOW,
                    category="refresh_session",
                    identity_kind="session",
                )
            )
        return specs

    if category is EndpointCategory.SCAN_START and method == "POST":
        if user_id:
            specs.append(
                RateLimitSpec(
                    redis_key=make_redis_key("scan_start", "user", user_id, route_template),
                    max_requests=settings.RATE_LIMIT_SCAN_START_USER,
                    window_seconds=settings.RATE_LIMIT_SCAN_START_WINDOW,
                    category="scan_start",
                    identity_kind="user",
                )
            )
        else:
            specs.append(
                RateLimitSpec(
                    redis_key=make_redis_key("scan_start", "ip", client_ip, "/api/v1/scan/start"),
                    max_requests=settings.RATE_LIMIT_GENERAL_ANONYMOUS_IP,
                    window_seconds=settings.RATE_LIMIT_GENERAL_WINDOW,
                    category="scan_start_anonymous",
                    identity_kind="ip",
                )
            )
        return specs

    if category is EndpointCategory.SCAN_POLL and method == "GET":
        if user_id:
            specs.append(
                RateLimitSpec(
                    redis_key=make_redis_key("scan_poll", "user", user_id, route_template),
                    max_requests=settings.RATE_LIMIT_SCAN_POLL_USER,
                    window_seconds=settings.RATE_LIMIT_SCAN_POLL_WINDOW,
                    category="scan_poll",
                    identity_kind="user",
                )
            )
        else:
            specs.append(
                RateLimitSpec(
                    redis_key=make_redis_key("scan_poll", "ip", client_ip, route_template),
                    max_requests=settings.RATE_LIMIT_GENERAL_ANONYMOUS_IP,
                    window_seconds=settings.RATE_LIMIT_SCAN_POLL_WINDOW,
                    category="scan_poll_anonymous",
                    identity_kind="ip",
                )
            )
        return specs

    if category is EndpointCategory.AI_EXPLANATION and method == "POST":
        if user_id:
            specs.append(
                RateLimitSpec(
                    redis_key=make_redis_key("ai_explanation", "user", user_id, route_template),
                    max_requests=settings.RATE_LIMIT_AI_EXPLANATION_USER,
                    window_seconds=settings.RATE_LIMIT_AI_WINDOW,
                    category="ai_explanation",
                    identity_kind="user",
                )
            )
        return specs

    if category is EndpointCategory.AI_REMEDIATION and method == "POST":
        if user_id:
            specs.append(
                RateLimitSpec(
                    redis_key=make_redis_key("ai_remediation", "user", user_id, route_template),
                    max_requests=settings.RATE_LIMIT_AI_REMEDIATION_USER,
                    window_seconds=settings.RATE_LIMIT_AI_WINDOW,
                    category="ai_remediation",
                    identity_kind="user",
                )
            )
        return specs

    if category is EndpointCategory.REPOSITORY_SYNC and method == "POST":
        if user_id:
            specs.append(
                RateLimitSpec(
                    redis_key=make_redis_key("repository_sync", "user", user_id, route_template),
                    max_requests=settings.RATE_LIMIT_REPOSITORY_SYNC_USER,
                    window_seconds=settings.RATE_LIMIT_REPOSITORY_SYNC_WINDOW,
                    category="repository_sync",
                    identity_kind="user",
                )
            )
        return specs

    # General API: hybrid authenticated vs anonymous
    if user_id:
        specs.append(
            RateLimitSpec(
                redis_key=make_redis_key("general_user", "user", user_id, route_template),
                max_requests=settings.RATE_LIMIT_GENERAL_USER,
                window_seconds=settings.RATE_LIMIT_GENERAL_WINDOW,
                category="general_user",
                identity_kind="user",
            )
        )
        specs.append(
            RateLimitSpec(
                redis_key=make_redis_key("general_ip", "ip", client_ip, "_aggregate"),
                max_requests=settings.RATE_LIMIT_GENERAL_IP,
                window_seconds=settings.RATE_LIMIT_GENERAL_WINDOW,
                category="general_ip",
                identity_kind="ip",
            )
        )
    else:
        specs.append(
            RateLimitSpec(
                redis_key=make_redis_key("general_anonymous", "ip", client_ip, route_template),
                max_requests=settings.RATE_LIMIT_GENERAL_ANONYMOUS_IP,
                window_seconds=settings.RATE_LIMIT_GENERAL_WINDOW,
                category="general_anonymous",
                identity_kind="ip",
            )
        )
    return specs


def is_sensitive_failure(category: str) -> bool:
    return category in _SENSITIVE_CATEGORIES or category.startswith(
        ("login_", "register_", "refresh_", "password_reset_", "general_anonymous")
    )


def evaluate_request_limits(request: Request) -> tuple[list[RateLimitSpec], str, EndpointCategory]:
    path = request.url.path
    if path.startswith("/ws/"):
        return [], path, EndpointCategory.SKIP
    route_template, category = normalize_route(path)
    if category is EndpointCategory.SKIP:
        return [], route_template, category
    specs = build_rate_limit_specs(request, route_template, category)
    return specs, route_template, category