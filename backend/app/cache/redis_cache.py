"""
Redis Cache Service.

Connects to Redis using settings.REDIS_URL and provides:
- get / set / delete methods with TTL support
- Graceful handling of connection failures
- Specialised caching for AI responses and scan results
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Optional

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Abstract backend interface (allows swapping Redis for another backend later)
# ---------------------------------------------------------------------------

class CacheBackend:
    """Abstract cache backend interface."""

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from the cache."""
        raise NotImplementedError

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """Store a value in the cache with optional TTL."""
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        """Remove a value from the cache."""
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        """Check whether a key exists in the cache."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Redis implementation
# ---------------------------------------------------------------------------

class RedisCache(CacheBackend):
    """
    Redis-backed cache with graceful failure handling.

    All public methods return safe defaults (None / False) when Redis is
    unavailable, so the application continues to function without caching.
    """

    # Key prefixes to avoid collisions with other applications on the same Redis
    _KEY_PREFIX = "devarchai:"
    _AI_PREFIX = f"{_KEY_PREFIX}ai:"
    _SCAN_PREFIX = f"{_KEY_PREFIX}scan:"
    _FINDING_PREFIX = f"{_KEY_PREFIX}finding:"

    # Default TTLs
    _AI_RESPONSE_TTL = timedelta(minutes=30)
    _SCAN_RESULT_TTL = timedelta(hours=1)
    _DEFAULT_TTL = timedelta(hours=1)

    def __init__(self) -> None:
        self._redis: Any = None
        self._connected: bool = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Establish connection to Redis using settings.REDIS_URL.

        If the connection fails, the cache operates in degraded mode
        (all operations become no-ops) and a warning is logged.
        """
        if self._connected:
            return

        try:
            import asyncio

            import redis.asyncio as redis

            self._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
            )
            # Ping to verify connectivity (bounded wait — never block startup indefinitely)
            await asyncio.wait_for(
                self._redis.ping(),
                timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
            )
            self._connected = True
            logger.info("Redis cache connected", url=settings.REDIS_URL)
        except ImportError:
            logger.warning(
                "redis package not installed -- cache disabled. "
                "Install with: pip install redis"
            )
            self._redis = None
            self._connected = False
        except Exception as exc:
            logger.warning(
                "Failed to connect to Redis -- cache disabled",
                url=settings.REDIS_URL,
                error=str(exc),
            )
            self._redis = None
            self._connected = False

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis and self._connected:
            try:
                await self._redis.close()
                self._connected = False
                logger.info("Redis cache connection closed")
            except Exception as exc:
                logger.warning("Error closing Redis connection", error=str(exc))
            finally:
                self._redis = None

    @property
    def is_connected(self) -> bool:
        """Whether the cache is currently connected to Redis."""
        return self._connected

    # ------------------------------------------------------------------
    # Core cache operations
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The deserialized value, or None if the key is missing or
            the cache is unavailable.
        """
        if not self._connected or self._redis is None:
            return None

        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Cache value is not valid JSON", key=key)
            return None
        except Exception as exc:
            logger.warning("Failed to get from cache", key=key, error=str(exc))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """
        Store a value in the cache with an optional TTL.

        Args:
            key: The cache key.
            value: The value to cache (must be JSON-serializable).
            ttl: Time-to-live.  Defaults to _DEFAULT_TTL.

        Returns:
            True if the value was stored, False on failure.
        """
        if not self._connected or self._redis is None:
            return False

        try:
            serialized = json.dumps(value, default=str)
            effective_ttl = ttl or self._DEFAULT_TTL
            ttl_seconds = int(effective_ttl.total_seconds())

            await self._redis.setex(key, ttl_seconds, serialized)
            return True
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Cache value is not JSON-serializable",
                key=key,
                error=str(exc),
            )
            return False
        except Exception as exc:
            logger.warning("Failed to set cache", key=key, error=str(exc))
            return False

    async def delete(self, key: str) -> bool:
        """
        Remove a key from the cache.

        Args:
            key: The cache key to delete.

        Returns:
            True if the key was deleted, False on failure or if cache is down.
        """
        if not self._connected or self._redis is None:
            return False

        try:
            await self._redis.delete(key)
            return True
        except Exception as exc:
            logger.warning("Failed to delete from cache", key=key, error=str(exc))
            return False

    async def exists(self, key: str) -> bool:
        """
        Check whether a key exists in the cache.

        Returns:
            False when the cache is unavailable (safe default).
        """
        if not self._connected or self._redis is None:
            return False

        try:
            return bool(await self._redis.exists(key))
        except Exception as exc:
            logger.warning(
                "Failed to check cache existence",
                key=key,
                error=str(exc),
            )
            return False

    # ------------------------------------------------------------------
    # Domain-specific caching helpers
    # ------------------------------------------------------------------

    # -- AI response caching --

    async def get_ai_response(self, prompt_hash: str) -> Optional[dict[str, Any]]:
        """
        Retrieve a cached AI response.

        Args:
            prompt_hash: A hash of the prompt to use as the cache key.
        """
        key = f"{self._AI_PREFIX}response:{prompt_hash}"
        return await self.get(key)

    async def set_ai_response(
        self,
        prompt_hash: str,
        response: dict[str, Any],
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """
        Cache an AI response.

        Args:
            prompt_hash: A hash of the prompt to use as the cache key.
            response: The AI response to cache.
            ttl: Optional TTL override.
        """
        key = f"{self._AI_PREFIX}response:{prompt_hash}"
        return await self.set(key, response, ttl or self._AI_RESPONSE_TTL)

    async def invalidate_ai_response(self, prompt_hash: str) -> bool:
        """Remove a cached AI response."""
        key = f"{self._AI_PREFIX}response:{prompt_hash}"
        return await self.delete(key)

    # -- Scan result caching --

    async def get_scan_result(self, scan_id: str) -> Optional[dict[str, Any]]:
        """Retrieve cached scan results."""
        key = f"{self._SCAN_PREFIX}result:{scan_id}"
        return await self.get(key)

    async def set_scan_result(
        self,
        scan_id: str,
        result: dict[str, Any],
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """
        Cache scan results.

        Args:
            scan_id: The unique scan identifier.
            result: The scan result payload.
            ttl: Optional TTL override.
        """
        key = f"{self._SCAN_PREFIX}result:{scan_id}"
        return await self.set(key, result, ttl or self._SCAN_RESULT_TTL)

    async def invalidate_scan_result(self, scan_id: str) -> bool:
        """Remove cached scan results."""
        key = f"{self._SCAN_PREFIX}result:{scan_id}"
        return await self.delete(key)

    # -- Finding caching --

    async def get_findings(self, repo_key: str) -> Optional[list[dict[str, Any]]]:
        """Retrieve cached findings for a repository."""
        key = f"{self._FINDING_PREFIX}findings:{repo_key}"
        return await self.get(key)

    async def set_findings(
        self,
        repo_key: str,
        findings: list[dict[str, Any]],
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """Cache findings for a repository."""
        key = f"{self._FINDING_PREFIX}findings:{repo_key}"
        return await self.set(key, findings, ttl or self._SCAN_RESULT_TTL)

    # -- Bulk invalidation --

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a glob pattern.

        Args:
            pattern: A Redis glob pattern (e.g. "devarchai:scan:*").

        Returns:
            The number of keys deleted.
        """
        if not self._connected or self._redis is None:
            return 0

        try:
            deleted = 0
            async for key in self._redis.scan_iter(match=pattern):
                await self._redis.delete(key)
                deleted += 1
            logger.info("Bulk cache invalidation", pattern=pattern, deleted=deleted)
            return deleted
        except Exception as exc:
            logger.warning(
                "Failed to invalidate cache pattern",
                pattern=pattern,
                error=str(exc),
            )
            return 0


# ---------------------------------------------------------------------------
# Singleton instance and dependency-injection helpers
# ---------------------------------------------------------------------------

_cache_instance: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """
    Get the global RedisCache singleton, connecting if necessary.

    This function is safe to call multiple times -- it will only connect once.
    """
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = RedisCache()

    if not _cache_instance.is_connected:
        await _cache_instance.connect()

    return _cache_instance


async def close_cache() -> None:
    """Close the global cache connection."""
    global _cache_instance

    if _cache_instance is not None:
        await _cache_instance.close()
        _cache_instance = None
