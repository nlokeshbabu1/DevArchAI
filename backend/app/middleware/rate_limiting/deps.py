"""Route-level rate limits (account identifiers, post-auth buckets)."""

from __future__ import annotations

from fastapi import Request

from app.config import settings
from app.core.security import hash_email
from app.middleware.rate_limiting.client_ip import get_client_ip
from app.middleware.rate_limiting.sliding_window import (
    RateLimitResult,
    RateLimitSpec,
    check_sliding_window,
    count_in_window,
    is_over_limit,
    make_redis_key,
)


def _login_account_spec(email: str) -> RateLimitSpec:
    account_id = hash_email(email)
    return RateLimitSpec(
        redis_key=make_redis_key("login_account", "account", account_id, "/api/v1/auth/login"),
        max_requests=settings.RATE_LIMIT_LOGIN_ACCOUNT,
        window_seconds=settings.RATE_LIMIT_LOGIN_ACCOUNT_WINDOW,
        category="login_account",
        identity_kind="account",
    )


async def block_if_login_account_limited(email: str) -> None:
    """Reject login when the account bucket is already exhausted (no new hit recorded)."""
    spec = _login_account_spec(email)
    if await is_over_limit(spec):
        count = await count_in_window(spec)
        result = RateLimitResult(
            allowed=False,
            count=count,
            limit=spec.max_requests,
            window_seconds=spec.window_seconds,
            retry_after=max(1, spec.window_seconds),
            spec=spec,
        )
        _raise_rate_limit(result)


async def record_failed_login_account_attempt(email: str) -> None:
    """Record a failed login against the hashed account identifier."""
    spec = _login_account_spec(email)
    result = await check_sliding_window(spec)
    if not result.allowed:
        _raise_rate_limit(result)


async def enforce_password_reset_account_limit(email: str, request: Request) -> None:
    account_id = hash_email(email)
    spec = RateLimitSpec(
        redis_key=make_redis_key(
            "password_reset_account",
            "account",
            account_id,
            "/api/v1/auth/forgot-password",
        ),
        max_requests=settings.RATE_LIMIT_PASSWORD_RESET_ACCOUNT,
        window_seconds=settings.RATE_LIMIT_PASSWORD_RESET_ACCOUNT_WINDOW,
        category="password_reset_account",
        identity_kind="account",
    )
    result = await check_sliding_window(spec)
    if not result.allowed:
        _raise_rate_limit(result)


async def enforce_password_reset_ip_limit(request: Request) -> None:
    client_ip = get_client_ip(request)
    spec = RateLimitSpec(
        redis_key=make_redis_key(
            "password_reset_ip",
            "ip",
            client_ip,
            "/api/v1/auth/forgot-password",
        ),
        max_requests=settings.RATE_LIMIT_PASSWORD_RESET_IP,
        window_seconds=settings.RATE_LIMIT_PASSWORD_RESET_IP_WINDOW,
        category="password_reset_ip",
        identity_kind="ip",
    )
    result = await check_sliding_window(spec)
    if not result.allowed:
        _raise_rate_limit(result)


def _raise_rate_limit(result) -> None:
    from fastapi import HTTPException

    from app.middleware.rate_limiting.sliding_window import rate_limit_headers

    raise HTTPException(
        status_code=429,
        detail="Too many requests. Please try again later.",
        headers=rate_limit_headers(result),
    )