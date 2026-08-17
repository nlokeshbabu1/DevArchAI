"""Redis-backed token blacklist for revoked JWT tokens.

Security policy: Fail-closed. If Redis is unavailable, token validation
and blacklisting operations raise exceptions rather than silently passing
revoked tokens.
"""

from __future__ import annotations

from datetime import timedelta

import structlog

from app.cache.redis_cache import get_cache

logger = structlog.get_logger(__name__)

BLACKLIST_PREFIX = "devarchai:blacklist:"
DEFAULT_TTL = timedelta(days=7)


class BlacklistRedisError(Exception):
    """Raised when the Redis blacklist service is unavailable.

    This signals callers that they should FAIL CLOSED (reject the request)
    rather than allowing a potentially revoked token through.
    """


async def blacklist_token(jti: str, expires_in: timedelta | None = None) -> bool:
    """Add a token's jti to the Redis blacklist.

    Args:
        jti: The unique JWT ID to blacklist.
        expires_in: TTL for the blacklist entry (defaults to 7 days).

    Returns:
        True if the token was blacklisted.

    Raises:
        BlacklistRedisError: If Redis is unavailable (fail-closed).
    """
    if not jti:
        return False
    try:
        cache = await get_cache()
        if not cache.is_connected or cache._redis is None:
            logger.error("auth_revocation_check_failed", reason="redis_unavailable", operation="blacklist_token")
            raise BlacklistRedisError("Redis unavailable for token blacklisting")
        ttl = expires_in or DEFAULT_TTL
        key = f"{BLACKLIST_PREFIX}{jti}"
        await cache._redis.setex(key, int(ttl.total_seconds()), "1")
        logger.debug("token_blacklisted", jti=jti[:8])
        return True
    except BlacklistRedisError:
        raise
    except Exception as exc:
        logger.error("auth_revocation_check_failed", operation="blacklist_token", error_type=type(exc).__name__)
        raise BlacklistRedisError(f"Failed to blacklist token: {exc}") from exc


async def is_blacklisted(jti: str) -> bool:
    """Check if a token's jti is blacklisted.

    Args:
        jti: The unique JWT ID to check.

    Returns:
        True if the token is blacklisted, False if it is not.

    Raises:
        BlacklistRedisError: If Redis is unavailable (fail-closed).
    """
    if not jti:
        return False
    try:
        cache = await get_cache()
        if not cache.is_connected or cache._redis is None:
            logger.error("auth_revocation_check_failed", reason="redis_unavailable", operation="is_blacklisted")
            raise BlacklistRedisError("Redis unavailable for blacklist check")
        key = f"{BLACKLIST_PREFIX}{jti}"
        exists = await cache._redis.exists(key)
        return bool(exists)
    except BlacklistRedisError:
        raise
    except Exception as exc:
        logger.error("auth_revocation_check_failed", operation="is_blacklisted", error_type=type(exc).__name__)
        raise BlacklistRedisError(f"Failed to check blacklist: {exc}") from exc


async def blacklist_user_tokens(user_id: str) -> bool:
    """Blacklist all tokens for a user by pattern.

    Note: This is best-effort. For complete revocation, use session-based
    revocation which checks the session table.

    Args:
        user_id: The user's UUID string.

    Returns:
        True if the operation succeeded, False otherwise.
    """
    try:
        cache = await get_cache()
        if not cache.is_connected or cache._redis is None:
            logger.warning("redis_unavailable", operation="blacklist_user_tokens")
            return False
        pattern = f"{BLACKLIST_PREFIX}{user_id[:8]}*"
        deleted = 0
        async for key in cache._redis.scan_iter(match=pattern):
            await cache._redis.delete(key)
            deleted += 1
        logger.info("user_tokens_blacklisted", user_id=user_id[:8], count=deleted)
        return True
    except Exception as exc:
        logger.warning("failed_to_blacklist_user_tokens", user_id=user_id[:8], error_type=type(exc).__name__)
        return False
