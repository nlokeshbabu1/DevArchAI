"""Redis-backed cluster snapshot and recommendation cache."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import timedelta
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

SNAPSHOT_TTL = 60
VERSION_ADVISOR_TTL = 3600
RECOMMENDATION_TTL = 86400


def snapshot_key(connection_id: str) -> str:
    return f"devarchai:k8s:snapshot:{connection_id}"


def version_advisor_key(connection_id: str, version: str) -> str:
    raw = f"{connection_id}:{version}"
    return f"devarchai:k8s:version:{hashlib.sha256(raw.encode()).hexdigest()[:24]}"


def recommendation_key(rule_id: str, fingerprint: str) -> str:
    return f"devarchai:k8s:recommendation:{rule_id}:{fingerprint}"


def ai_job_key(connection_id: str, job_id: str) -> str:
    return f"devarchai:k8s:ai:{connection_id}:{job_id}"


def upgrade_analysis_key(connection_id: str, version: str, target: str) -> str:
    raw = f"{connection_id}:{version}:{target}"
    return f"devarchai:k8s:upgrade:{hashlib.sha256(raw.encode()).hexdigest()[:24]}"


class ClusterCache:
    """Cache cluster snapshots, version advisor, and AI recommendations."""

    def __init__(self) -> None:
        self._memory: dict[str, tuple[float, Any]] = {}

    async def _redis(self) -> Any | None:
        try:
            from app.cache.redis_cache import get_cache

            cache = await get_cache()
            if cache.is_connected:
                return cache
        except Exception as exc:
            logger.debug("k8s_redis_unavailable", error=str(exc))
        return None

    def _mem_get(self, key: str) -> Any | None:
        if key in self._memory:
            expires, value = self._memory[key]
            if time.time() < expires:
                return value
            del self._memory[key]
        return None

    def _mem_set(self, key: str, value: Any, ttl: int) -> None:
        self._memory[key] = (time.time() + ttl, value)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        cached = self._mem_get(key)
        if cached is not None:
            return cached
        redis = await self._redis()
        if redis:
            try:
                value = await redis.get(key)
                if value is not None:
                    parsed = json.loads(value) if isinstance(value, str) else value
                    self._mem_set(key, parsed, SNAPSHOT_TTL)
                    return parsed
            except Exception as exc:
                logger.debug("k8s_cache_get_failed", key=key, error=str(exc))
        return None

    def _ttl_seconds(self, ttl: int | timedelta) -> int:
        if isinstance(ttl, timedelta):
            return max(1, int(ttl.total_seconds()))
        return max(1, int(ttl))

    def _ttl_timedelta(self, ttl: int | timedelta) -> timedelta:
        if isinstance(ttl, timedelta):
            return ttl
        return timedelta(seconds=self._ttl_seconds(ttl))

    async def set_json(self, key: str, value: dict[str, Any], ttl: int | timedelta) -> None:
        ttl_seconds = self._ttl_seconds(ttl)
        self._mem_set(key, value, ttl_seconds)
        redis = await self._redis()
        if redis:
            try:
                # RedisCache.set expects timedelta, not raw seconds.
                await redis.set(key, value, ttl=self._ttl_timedelta(ttl))
            except Exception as exc:
                logger.debug("k8s_cache_set_failed", key=key, error=str(exc))

    async def get_snapshot(self, connection_id: str) -> dict[str, Any] | None:
        return await self.get_json(snapshot_key(connection_id))

    async def set_snapshot(self, connection_id: str, snapshot: dict[str, Any]) -> None:
        await self.set_json(snapshot_key(connection_id), snapshot, SNAPSHOT_TTL)

    async def get_version_advisor(self, connection_id: str, version: str) -> dict[str, Any] | None:
        return await self.get_json(version_advisor_key(connection_id, version))

    async def set_version_advisor(
        self,
        connection_id: str,
        version: str,
        data: dict[str, Any],
    ) -> None:
        await self.set_json(version_advisor_key(connection_id, version), data, VERSION_ADVISOR_TTL)

    async def get_recommendation(self, rule_id: str, fingerprint: str) -> dict[str, Any] | None:
        return await self.get_json(recommendation_key(rule_id, fingerprint))

    async def set_recommendation(
        self,
        rule_id: str,
        fingerprint: str,
        data: dict[str, Any],
    ) -> None:
        await self.set_json(
            recommendation_key(rule_id, fingerprint),
            data,
            RECOMMENDATION_TTL,
        )

    async def get_ai_result(self, connection_id: str, job_id: str) -> dict[str, Any] | None:
        return await self.get_json(ai_job_key(connection_id, job_id))

    async def set_ai_result(
        self,
        connection_id: str,
        job_id: str,
        result: dict[str, Any],
    ) -> None:
        await self.set_json(
            ai_job_key(connection_id, job_id),
            result,
            settings.RAG_CACHE_TTL_SECONDS,
        )

    async def get_upgrade_analysis(
        self,
        connection_id: str,
        version: str,
        target: str,
    ) -> dict[str, Any] | None:
        return await self.get_json(upgrade_analysis_key(connection_id, version, target))

    async def set_upgrade_analysis(
        self,
        connection_id: str,
        version: str,
        target: str,
        data: dict[str, Any],
    ) -> None:
        await self.set_json(
            upgrade_analysis_key(connection_id, version, target),
            data,
            VERSION_ADVISOR_TTL,
        )


_cluster_cache: ClusterCache | None = None


def get_cluster_cache() -> ClusterCache:
    global _cluster_cache
    if _cluster_cache is None:
        _cluster_cache = ClusterCache()
    return _cluster_cache
