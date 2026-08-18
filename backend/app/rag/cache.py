"""RAG + MCP result caching.

Small in-memory + Redis cache for retrieved RAG contexts and MCP live context.
Mirrors the knowledge cache pattern but is purpose-built for the RAG/MCP
layers, with distinct key namespaces so it never collides with existing keys:

- ``devarchai:rag:chunk:{hash}``
- ``devarchai:mcp:ctx:{technology}:{hash}``

Redis failures degrade to in-memory caching / cache-miss (never an error).
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


def _sha256(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def rag_cache_key(query: str, filters: dict[str, Any]) -> str:
    raw = json.dumps({"q": query, "f": filters}, sort_keys=True, default=str)
    return f"devarchai:rag:chunk:{_sha256(raw)}"


def mcp_cache_key(technology: str, provider: str, request_key: str) -> str:
    raw = f"{technology}:{provider}:{request_key}"
    return f"devarchai:mcp:ctx:{technology}:{_sha256(raw)}"


class RagCache:
    """In-memory + optional Redis cache for RAG/MCP results."""

    def __init__(
        self,
        rag_ttl_seconds: int | None = None,
        mcp_ttl_seconds: int | None = None,
    ) -> None:
        self._rag_ttl = rag_ttl_seconds or settings.RAG_CACHE_TTL_SECONDS
        self._mcp_ttl = mcp_ttl_seconds or settings.MCP_CACHE_TTL_SECONDS
        self._memory: dict[str, tuple[float, Any]] = {}
        self._redis: Any = None

    def _get_redis(self) -> Any:
        """Lazy-load the shared Redis cache client."""
        if self._redis is None:
            try:
                from app.cache.redis_cache import get_cache
                cache = get_cache()
                if cache._connected:
                    self._redis = cache
            except Exception:
                self._redis = None
        return self._redis

    async def get(self, key: str) -> Any | None:
        if key in self._memory:
            expires_at, value = self._memory[key]
            if time.time() < expires_at:
                logger.debug("RAG_CACHE_HIT_MEMORY", key=key)
                return value
            del self._memory[key]

        redis = self._get_redis()
        if redis:
            try:
                value = await redis.get(key)
                if value is not None:
                    self._memory[key] = (time.time() + self._rag_ttl, value)
                    logger.debug("RAG_CACHE_HIT_REDIS", key=key)
                    return value
            except Exception as exc:
                logger.debug("RAG_CACHE_REDIS_GET_ERROR", error=str(exc))
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds or self._rag_ttl
        self._memory[key] = (time.time() + ttl, value)

        redis = self._get_redis()
        if redis:
            try:
                await redis.set(key, value, ttl=ttl)
            except Exception as exc:
                logger.debug("RAG_CACHE_REDIS_SET_ERROR", error=str(exc))

    async def invalidate(self, pattern: str | None = None) -> int:
        """Invalidate cached entries. Returns count removed."""
        count = 0
        if pattern:
            keys = [k for k in self._memory if pattern in k]
        else:
            keys = list(self._memory.keys())
        for key in keys:
            del self._memory[key]
            count += 1
        redis = self._get_redis()
        if redis and pattern:
            try:
                count += await redis.invalidate_pattern(pattern)
            except Exception:
                pass
        return count

    async def stats(self) -> dict[str, Any]:
        return {
            "memory_entries": len(self._memory),
            "redis_connected": self._get_redis() is not None,
            "rag_ttl_seconds": self._rag_ttl,
            "mcp_ttl_seconds": self._mcp_ttl,
        }


# Singleton
_rag_cache: RagCache | None = None


def get_rag_cache() -> RagCache:
    """Get the global RAG/MCP cache singleton."""
    global _rag_cache
    if _rag_cache is None:
        _rag_cache = RagCache()
    return _rag_cache
