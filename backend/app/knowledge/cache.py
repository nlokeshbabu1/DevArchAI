"""Knowledge caching layer.

Caches KnowledgeDocuments with configurable TTL to avoid redundant
API calls. Uses in-memory cache as primary with Redis as distributed
cache when available.

Cache key structure: devarchai:knowledge:{provider}:{query_hash}

Supports automatic refresh of stale content before expiration.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections.abc import Callable, Coroutine
from typing import Any

from app.knowledge.base import KnowledgeDocument

logger = logging.getLogger(__name__)


class KnowledgeCache:
    """In-memory + optional Redis cache for knowledge documents.

    Falls back gracefully to in-memory only if Redis is unavailable.
    Supports automatic refresh of stale content before expiration.
    """

    def __init__(
        self,
        default_ttl_seconds: int = 3600,
        refresh_threshold_seconds: int = 300,
    ):
        self._memory: dict[str, tuple[float, list[KnowledgeDocument]]] = {}
        self._default_ttl = default_ttl_seconds
        self._refresh_threshold = refresh_threshold_seconds
        self._redis: Any = None
        self._refresh_tasks: dict[str, asyncio.Task] = {}
        self._cleanup_task: asyncio.Task | None = None

    def _get_redis(self) -> Any:
        """Lazy-load Redis connection.

        Peeks at the global cache singleton without connecting: this runs in
        sync contexts, so awaiting the async ``get_cache()`` factory here is
        impossible (and would produce un-awaited coroutine warnings).
        """
        if self._redis is None:
            try:
                from app.cache import redis_cache as redis_mod

                cache = redis_mod._cache_instance
                if cache is not None and cache._connected:
                    self._redis = cache
            except Exception:
                pass
        return self._redis

    @staticmethod
    def _make_key(provider: str, query: str, service: str = "", region: str = "") -> str:
        raw = f"{provider}:{query}:{service}:{region}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    async def get(
        self,
        provider: str,
        query: str,
        service: str = "",
        region: str = "",
        auto_refresh: bool = False,
        refresh_func: Callable[..., Coroutine[Any, Any, list[KnowledgeDocument]]] | None = None,
    ) -> list[KnowledgeDocument] | None:
        """Retrieve cached documents if not expired.

        Args:
            provider: Provider name.
            query: Query string.
            service: AWS service name.
            region: AWS region.
            auto_refresh: If True, trigger background refresh when near expiration.
            refresh_func: Async function to refresh documents if auto_refresh is True.

        Returns:
            Cached documents or None if not found/expired.
        """
        key = self._make_key(provider, query, service, region)

        # 1. Check memory cache
        if key in self._memory:
            expires_at, docs = self._memory[key]
            now = time.time()

            if now < expires_at:
                # Check if nearing expiration and auto-refresh is enabled
                if auto_refresh and refresh_func and (
                    expires_at - now
                ) < self._refresh_threshold:
                    self._trigger_background_refresh(
                        key, provider, query, service, region, refresh_func
                    )

                logger.debug("KNOWLEDGE_CACHE_HIT_MEMORY", provider=provider, key=key)
                return docs
            del self._memory[key]

        # 2. Check Redis
        redis = self._get_redis()
        if redis:
            try:
                cached = await redis.get(f"devarchai:knowledge:{key}")
                if cached:
                    docs = [KnowledgeDocument(**d) for d in cached]
                    # Re-populate memory cache
                    self._memory[key] = (time.time() + self._default_ttl, docs)
                    logger.debug("KNOWLEDGE_CACHE_HIT_REDIS", provider=provider, key=key)
                    return docs
            except Exception as exc:
                logger.debug("KNOWLEDGE_CACHE_REDIS_ERROR", error=str(exc))

        return None

    async def set(
        self,
        provider: str,
        query: str,
        documents: list[KnowledgeDocument],
        service: str = "",
        region: str = "",
        ttl_seconds: int | None = None,
    ) -> None:
        """Cache documents with TTL."""
        key = self._make_key(provider, query, service, region)
        ttl = ttl_seconds or self._default_ttl
        expires_at = time.time() + ttl

        # 1. Store in memory
        self._memory[key] = (expires_at, documents)

        # 2. Store in Redis
        redis = self._get_redis()
        if redis:
            try:
                doc_dicts = [
                    {
                        "source": d.source,
                        "title": d.title,
                        "content": d.content,
                        "url": d.url,
                        "version": d.version,
                        "retrieved_at": d.retrieved_at.isoformat(),
                        "relevance_score": d.relevance_score,
                        "metadata": d.metadata,
                    }
                    for d in documents
                ]
                await redis.set(
                    f"devarchai:knowledge:{key}",
                    doc_dicts,
                    ttl=ttl,
                )
            except Exception as exc:
                logger.debug("KNOWLEDGE_CACHE_REDIS_SET_ERROR", error=str(exc))

        logger.debug(
            "KNOWLEDGE_CACHE_SET",
            provider=provider,
            key=key,
            doc_count=len(documents),
            ttl=ttl,
        )

    async def invalidate(self, provider: str | None = None) -> int:
        """Invalidate cached entries. Returns count of entries removed."""
        count = 0
        if provider:
            provider_hash = hashlib.sha256(provider.encode()).hexdigest()[:8]
            keys_to_remove = [
                k for k in self._memory
                if k.startswith(provider_hash)
            ]
        else:
            keys_to_remove = list(self._memory.keys())

        for key in keys_to_remove:
            del self._memory[key]
            count += 1

        # Also cancel any pending refresh tasks for these keys
        for key in keys_to_remove:
            if key in self._refresh_tasks:
                self._refresh_tasks[key].cancel()
                del self._refresh_tasks[key]

        logger.info(f"KNOWLEDGE_CACHE_INVALIDATED provider={provider} count={count}")
        return count

    async def get_stale_entries(self) -> list[dict[str, Any]]:
        """Get entries that are expired or near expiration.

        Returns list of dicts with key info and staleness status.
        """
        now = time.time()
        stale_entries = []

        for key, (expires_at, docs) in self._memory.items():
            time_until_expiry = expires_at - now
            is_expired = time_until_expiry < 0
            is_stale = 0 < time_until_expiry < self._refresh_threshold

            if is_expired or is_stale:
                stale_entries.append({
                    "key": key,
                    "provider": docs[0].source if docs else "unknown",
                    "expires_at": expires_at,
                    "time_until_expiry": round(time_until_expiry, 1),
                    "is_expired": is_expired,
                    "is_stale": is_stale,
                    "doc_count": len(docs),
                })

        return stale_entries

    async def refresh_entry(
        self,
        key: str,
        refresh_func: Callable[..., Coroutine[Any, Any, list[KnowledgeDocument]]],
        *args: Any,
        **kwargs: Any,
    ) -> list[KnowledgeDocument] | None:
        """Refresh a specific cache entry using the provided function.

        Args:
            key: Cache key to refresh.
            refresh_func: Async function to call for fresh data.
            *args, **kwargs: Arguments to pass to refresh_func.

        Returns:
            Fresh documents if refresh succeeded, None otherwise.
        """
        try:
            logger.info("KNOWLEDGE_CACHE_REFRESH_START", key=key)
            fresh_docs = await refresh_func(*args, **kwargs)

            if fresh_docs:
                # Extract provider from first doc
                provider = fresh_docs[0].source if fresh_docs else "unknown"
                # Re-cache with fresh data
                await self.set(provider, key, fresh_docs)
                logger.info(
                    "KNOWLEDGE_CACHE_REFRESH_COMPLETE",
                    key=key,
                    doc_count=len(fresh_docs),
                )
                return fresh_docs

        except Exception as exc:
            logger.error(
                "KNOWLEDGE_CACHE_REFRESH_FAILED",
                key=key,
                error=str(exc),
            )

        return None

    def _trigger_background_refresh(
        self,
        key: str,
        provider: str,
        query: str,
        service: str,
        region: str,
        refresh_func: Callable[..., Coroutine[Any, Any, list[KnowledgeDocument]]],
    ) -> None:
        """Trigger a background refresh task for stale content."""
        # Don't trigger if already refreshing
        if key in self._refresh_tasks and not self._refresh_tasks[key].done():
            return

        async def _refresh_task() -> None:
            try:
                docs = await refresh_func(query=query, service=service, region=region)
                if docs:
                    await self.set(provider, query, docs, service, region)
                    logger.info(
                        "KNOWLEDGE_CACHE_BACKGROUND_REFRESH_COMPLETE",
                        key=key,
                        doc_count=len(docs),
                    )
            except Exception as exc:
                logger.warning(
                    "KNOWLEDGE_CACHE_BACKGROUND_REFRESH_FAILED",
                    key=key,
                    error=str(exc),
                )
            finally:
                self._refresh_tasks.pop(key, None)

        # Create task but don't await it (fire and forget)
        task = asyncio.create_task(_refresh_task())
        self._refresh_tasks[key] = task

        logger.debug("KNOWLEDGE_CACHE_BACKGROUND_REFRESH_TRIGGERED", key=key)

    async def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        now = time.time()
        active = sum(1 for exp, _ in self._memory.values() if now < exp)
        stale = sum(
            1
            for exp, _ in self._memory.values()
            if 0 < exp - now < self._refresh_threshold
        )
        expired = len(self._memory) - active
        return {
            "total_entries": len(self._memory),
            "active_entries": active,
            "stale_entries": stale,
            "expired_entries": expired,
            "redis_connected": self._get_redis() is not None,
            "pending_refresh_tasks": len(self._refresh_tasks),
        }

    def start_cleanup_task(self, interval_seconds: int = 300) -> None:
        """Start periodic cleanup task for expired cache entries.

        Args:
            interval_seconds: How often to run cleanup (default 5 minutes).
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            return

        async def _cleanup_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    await self._cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.warning(f"KNOWLEDGE_CACHE_CLEANUP_ERROR: {exc}")

        self._cleanup_task = asyncio.create_task(_cleanup_loop())
        logger.info(
            f"KNOWLEDGE_CACHE_CLEANUP_STARTED interval_seconds={interval_seconds}"
        )

    def stop_cleanup_task(self) -> None:
        """Stop the periodic cleanup task."""
        if self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            logger.info("KNOWLEDGE_CACHE_CLEANUP_STOPPED")

    async def _cleanup_expired(self) -> int:
        """Remove expired entries from memory cache.

        Returns:
            Number of entries removed.
        """
        now = time.time()
        expired_keys = [
            key for key, (expires_at, _) in self._memory.items()
            if expires_at < now
        ]

        for key in expired_keys:
            del self._memory[key]
            # Also cancel any pending refresh tasks
            if key in self._refresh_tasks:
                self._refresh_tasks[key].cancel()
                del self._refresh_tasks[key]

        if expired_keys:
            logger.info(
                f"KNOWLEDGE_CACHE_CLEANUP completed removed={len(expired_keys)} "
                f"remaining={len(self._memory)}"
            )

        return len(expired_keys)


# Singleton
_knowledge_cache: KnowledgeCache | None = None


def get_knowledge_cache() -> KnowledgeCache:
    global _knowledge_cache
    if _knowledge_cache is None:
        from app.config import settings
        _knowledge_cache = KnowledgeCache(
            default_ttl_seconds=settings.KNOWLEDGE_CACHE_TTL_SECONDS,
        )
    return _knowledge_cache
