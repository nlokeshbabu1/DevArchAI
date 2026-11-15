"""Redis-backed sliding window rate limiting."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RateLimitSpec:
    """One limit bucket to evaluate."""

    redis_key: str
    max_requests: int
    window_seconds: int
    category: str
    identity_kind: str  # user | ip | account | session


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    count: int
    limit: int
    window_seconds: int
    retry_after: int
    spec: RateLimitSpec


async def get_redis():
    from app.cache.redis_cache import get_cache

    cache = await get_cache()
    if not cache._connected or cache._redis is None:
        raise ConnectionError("Redis unavailable")
    return cache._redis


async def count_in_window(spec: RateLimitSpec) -> int:
    """Count events in the current window without recording a new hit."""
    now = time.time()
    window_start = now - spec.window_seconds
    redis = await get_redis()
    pipe = redis.pipeline(transaction=True)
    pipe.zremrangebyscore(spec.redis_key, 0, window_start)
    pipe.zcard(spec.redis_key)
    results = await pipe.execute()
    return int(results[1])


async def is_over_limit(spec: RateLimitSpec) -> bool:
    return await count_in_window(spec) >= spec.max_requests


async def check_sliding_window(spec: RateLimitSpec) -> RateLimitResult:
    """Atomically trim, count (pre-insert), and record one hit in the window."""
    now = time.time()
    window_start = now - spec.window_seconds

    redis = await get_redis()
    pipe = redis.pipeline(transaction=True)
    pipe.zremrangebyscore(spec.redis_key, 0, window_start)
    pipe.zcard(spec.redis_key)
    member = f"{now}:{id(spec)}"
    pipe.zadd(spec.redis_key, {member: now})
    pipe.expire(spec.redis_key, spec.window_seconds + 1)
    results = await pipe.execute()
    count = int(results[1])

    if count >= spec.max_requests:
        await redis.zrem(spec.redis_key, member)
        retry_after = max(1, int(spec.window_seconds))
        return RateLimitResult(
            allowed=False,
            count=count,
            limit=spec.max_requests,
            window_seconds=spec.window_seconds,
            retry_after=retry_after,
            spec=spec,
        )

    remaining = max(0, spec.max_requests - count - 1)
    return RateLimitResult(
        allowed=True,
        count=count + 1,
        limit=spec.max_requests,
        window_seconds=spec.window_seconds,
        retry_after=0,
        spec=spec,
    )


def rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(max(0, result.limit - result.count)),
        "X-RateLimit-Policy": result.spec.category,
    }
    if not result.allowed:
        headers["Retry-After"] = str(result.retry_after)
    return headers


def rate_limit_json_response(result: RateLimitResult):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
            }
        },
        headers=rate_limit_headers(result),
    )


def service_unavailable_response(retry_after: int = 30):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "SERVICE_UNAVAILABLE",
                "message": "Service temporarily unavailable. Please try again later.",
            }
        },
        headers={"Retry-After": str(retry_after)},
    )


async def enforce_specs(specs: list[RateLimitSpec]) -> RateLimitResult | None:
    """Evaluate limits in order; return blocking result or None if all pass."""
    last_ok: RateLimitResult | None = None
    for spec in specs:
        result = await check_sliding_window(spec)
        if not result.allowed:
            logger.warning(
                "rate_limit_exceeded",
                category=spec.category,
                identity_kind=spec.identity_kind,
                limit=spec.max_requests,
                window_seconds=spec.window_seconds,
            )
            return result
        last_ok = result
    return None


def make_redis_key(category: str, identity_kind: str, identity: str, route_template: str) -> str:
    """Build a versioned key without embedding raw PII."""
    return f"ratelimit:v2:{category}:{identity_kind}:{identity}:{route_template}"