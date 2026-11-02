"""OAuth CSRF state — Redis-backed, single-use, TTL-bound (multi-replica safe)."""

from __future__ import annotations

import secrets
import time

import structlog

logger = structlog.get_logger(__name__)

_OAUTH_STATE_TTL_SECONDS = 600
_OAUTH_STATE_PREFIX = "devarchai:oauth:state:"

_LOCAL_STATES: dict[str, float] = {}


async def generate_oauth_state() -> str:
    """Create a cryptographically random OAuth state and register it."""
    state = secrets.token_urlsafe(32)
    registered = await _register_state_redis(state)
    if not registered:
        _register_state_local(state)
    return state


async def validate_oauth_state(state: str) -> bool:
    """Validate and consume a state (single-use)."""
    if not state:
        return False
    if await _consume_state_redis(state):
        return True
    return _consume_state_local(state)


async def _register_state_redis(state: str) -> bool:
    from app.cache.redis_cache import get_cache

    try:
        cache = await get_cache()
        if not cache.is_connected or cache._redis is None:
            return False
        key = f"{_OAUTH_STATE_PREFIX}{state}"
        await cache._redis.setex(key, _OAUTH_STATE_TTL_SECONDS, "1")
        return True
    except Exception as exc:
        logger.warning("oauth_state_redis_register_failed", error_type=type(exc).__name__)
        return False


async def _consume_state_redis(state: str) -> bool:
    from app.cache.redis_cache import get_cache

    try:
        cache = await get_cache()
        if not cache.is_connected or cache._redis is None:
            return False
        key = f"{_OAUTH_STATE_PREFIX}{state}"
        pipe = cache._redis.pipeline(transaction=True)
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()
        return results[0] is not None
    except Exception as exc:
        logger.warning("oauth_state_redis_consume_failed", error_type=type(exc).__name__)
        return False


def _register_state_local(state: str) -> None:
    _LOCAL_STATES[state] = time.time()
    _clean_expired_states()


def _consume_state_local(state: str) -> bool:
    now = time.time()
    created_at = _LOCAL_STATES.pop(state, None)
    if created_at is None:
        _clean_expired_states(now)
        return False
    if now - created_at >= _OAUTH_STATE_TTL_SECONDS:
        return False
    _clean_expired_states(now)
    return True


def _clean_expired_states(now: float | None = None) -> None:
    if now is None:
        now = time.time()
    expired = [s for s, t in _LOCAL_STATES.items() if now - t >= _OAUTH_STATE_TTL_SECONDS]
    for key in expired:
        _LOCAL_STATES.pop(key, None)


# Sync helpers for unit tests (local store only).
def generate_oauth_state_sync() -> str:
    state = secrets.token_urlsafe(32)
    _register_state_local(state)
    return state


def validate_oauth_state_sync(state: str) -> bool:
    return _consume_state_local(state)
