"""
Redis Cache Service
Provides caching for GitHub API responses and analysis results.
"""

import json
from datetime import timedelta
from typing import Any

import redis.asyncio as redis
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class RedisCache:
    """Redis caching service for GitHub API and analysis results."""

    # Key prefixes
    KEY_PREFIX = "devarchai:"
    GITHUB_TREE_PREFIX = f"{KEY_PREFIX}github:tree:"
    GITHUB_INFO_PREFIX = f"{KEY_PREFIX}github:info:"
    ANALYSIS_PREFIX = f"{KEY_PREFIX}analysis:"
    VALIDATION_PREFIX = f"{KEY_PREFIX}validation:"

    # Default TTLs
    GITHUB_TREE_TTL = timedelta(hours=1)  # File tree cached for 1 hour
    GITHUB_INFO_TTL = timedelta(hours=6)  # Repo info cached for 6 hours
    ANALYSIS_TTL = timedelta(days=7)  # Analysis results cached for 7 days
    VALIDATION_TTL = timedelta(days=1)  # Validation results cached for 1 day

    def __init__(self):
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
                logger.info("Connected to Redis", url=settings.REDIS_URL)
            except Exception as e:
                logger.warning("Failed to connect to Redis", error=str(e))
                self._redis = None

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if not self._redis:
            return None

        try:
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("Failed to get from cache", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: timedelta | None = None,
    ) -> bool:
        """Set value in cache."""
        if not self._redis:
            return False

        try:
            serialized = json.dumps(value)
            if ttl:
                await self._redis.setex(key, int(ttl.total_seconds()), serialized)
            else:
                await self._redis.set(key, serialized)
            return True
        except Exception as e:
            logger.warning("Failed to set cache", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self._redis:
            return False

        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning("Failed to delete from cache", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._redis:
            return False

        try:
            return bool(await self._redis.exists(key))
        except Exception as e:
            logger.warning("Failed to check cache existence", key=key, error=str(e))
            return False

    # GitHub tree caching
    async def get_github_tree(self, owner: str, repo: str, branch: str) -> list[str] | None:
        """Get cached GitHub repository file tree."""
        key = f"{self.GITHUB_TREE_PREFIX}{owner}/{repo}:{branch}"
        return await self.get(key)

    async def set_github_tree(
        self,
        owner: str,
        repo: str,
        branch: str,
        files: list[str],
    ) -> bool:
        """Cache GitHub repository file tree."""
        key = f"{self.GITHUB_TREE_PREFIX}{owner}/{repo}:{branch}"
        return await self.set(key, files, self.GITHUB_TREE_TTL)

    # GitHub repo info caching
    async def get_github_info(self, owner: str, repo: str) -> dict[str, Any] | None:
        """Get cached GitHub repository info."""
        key = f"{self.GITHUB_INFO_PREFIX}{owner}/{repo}"
        return await self.get(key)

    async def set_github_info(
        self,
        owner: str,
        repo: str,
        info: dict[str, Any],
    ) -> bool:
        """Cache GitHub repository info."""
        key = f"{self.GITHUB_INFO_PREFIX}{owner}/{repo}"
        return await self.set(key, info, self.GITHUB_INFO_TTL)

    # Analysis result caching
    async def get_analysis(self, repo_url: str) -> dict[str, Any] | None:
        """Get cached analysis result."""
        key = f"{self.ANALYSIS_PREFIX}{repo_url}"
        return await self.get(key)

    async def set_analysis(
        self,
        repo_url: str,
        result: dict[str, Any],
    ) -> bool:
        """Cache analysis result."""
        key = f"{self.ANALYSIS_PREFIX}{repo_url}"
        return await self.set(key, result, self.ANALYSIS_TTL)

    # Validation result caching
    async def get_validation(self, url: str) -> dict[str, Any] | None:
        """Get cached validation result."""
        key = f"{self.VALIDATION_PREFIX}{url}"
        return await self.get(key)

    async def set_validation(
        self,
        url: str,
        result: dict[str, Any],
    ) -> bool:
        """Cache validation result."""
        key = f"{self.VALIDATION_PREFIX}{url}"
        return await self.set(key, result, self.VALIDATION_TTL)

    # Cache invalidation
    async def invalidate_repo_cache(self, owner: str, repo: str) -> bool:
        """Invalidate all cache entries for a repository."""
        if not self._redis:
            return False

        try:
            patterns = [
                f"{self.GITHUB_TREE_PREFIX}{owner}/{repo}:*",
                f"{self.GITHUB_INFO_PREFIX}{owner}/{repo}",
                f"{self.ANALYSIS_PREFIX}*{owner}/{repo}*",
            ]

            deleted = 0
            for pattern in patterns:
                async for key in self._redis.scan_iter(match=pattern):
                    await self._redis.delete(key)
                    deleted += 1

            logger.info("Invalidated repo cache", owner=owner, repo=repo, deleted=deleted)
            return True

        except Exception as e:
            logger.warning("Failed to invalidate cache", error=str(e))
            return False


# Singleton instance
_cache = RedisCache()


async def get_cache() -> RedisCache:
    """Get cache instance, connecting if necessary."""
    if _cache._redis is None:
        await _cache.connect()
    return _cache


async def close_cache() -> None:
    """Close cache connection."""
    await _cache.close()
