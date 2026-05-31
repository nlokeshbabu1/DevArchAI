"""Redis-backed token blacklist for revoked JWT tokens."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

import structlog

from app.cache.redis_cache import get_cache

logger = structlog.get_logger(__name__)

BLACKLIST_PREFIX = "devarchai:blacklist:"
DEFAULT_TTL = timedelta(days=7)


async def blacklist_token(jti: str, expires_in: Optional[timedelta] = None) -> bool:
    """Add a token's jti to the Redis blacklist.

    Args:
        jti: The unique JWT ID to blacklist.
        expires_in: TTL for the blacklist entry (defaults to 7 days).

    Returns:
        True if the token was blacklisted, False if Redis is unavailable.
    """
    if not jti:
        return False
    try:
        cache = await get_cache()
        if not cache.is_connected:
            logger.warning("Redis unavailable, skipping token blacklist")
            return False
        ttl = expires_in or DEFAULT_TTL
        key = f"{BLACKLIST_PREFIX}{jti}"
        await cache._redis.setex(key, int(ttl.total_seconds()), "1")
        logger.debug("Token blacklisted", jti=jti[:8])
        return True
    except Exception as exc:
        logger.warning("Failed to blacklist token", jti=jti[:8], error=str(exc))
        return False


async def is_blacklisted(jti: str) -> bool:
    """Check if a token's jti is blacklisted.

    Args:
        jti: The unique JWT ID to check.

    Returns:
        True if the token is blacklisted, False otherwise.
    """
    if not jti:
        return False
    try:
        cache = await get_cache()
        if not cache.is_connected:
            return False
        key = f"{BLACKLIST_PREFIX}{jti}"
        exists = await cache._redis.exists(key)
        return bool(exists)
    except Exception as exc:
        logger.warning("Failed to check blacklist", jti=jti[:8], error=str(exc))
        return False


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
        if not cache.is_connected:
            return False
        pattern = f"{BLACKLIST_PREFIX}{user_id[:8]}*"
        deleted = 0
        async for key in cache._redis.scan_iter(match=pattern):
            await cache._redis.delete(key)
            deleted += 1
        logger.info("Blacklisted user tokens", user_id=user_id, count=deleted)
        return True
    except Exception as exc:
        logger.warning("Failed to blacklist user tokens", user_id=user_id, error=str(exc))
        return False
