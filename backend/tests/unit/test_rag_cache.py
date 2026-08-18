"""Unit tests for the RAG cache (two-tier: memory + Redis)."""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.cache import rag_cache_key, mcp_cache_key, _sha256, RagCache


class TestSha256:
    """Tests for the _sha256 helper."""

    def test_deterministic(self):
        """Same input always produces same hash."""
        h1 = _sha256("hello world")
        h2 = _sha256("hello world")
        assert h1 == h2

    def test_different_inputs(self):
        """Different inputs produce different hashes."""
        h1 = _sha256("hello")
        h2 = _sha256("world")
        assert h1 != h2

    def test_length(self):
        """Hash is 32 hex characters (truncated SHA-256)."""
        h = _sha256("test")
        assert len(h) == 32


class TestCacheKeyBuilders:
    """Tests for rag_cache_key and mcp_cache_key."""

    def test_rag_cache_key_format(self):
        """RAG cache key has correct prefix."""
        key = rag_cache_key("terraform S3", {"technology": "aws"})
        assert key.startswith("devarchai:rag:chunk:")

    def test_rag_cache_key_same_query_same_filters(self):
        """Same query + filters => same cache key."""
        k1 = rag_cache_key("test", {"a": 1})
        k2 = rag_cache_key("test", {"a": 1})
        assert k1 == k2

    def test_rag_cache_key_different_query(self):
        """Different queries => different cache keys."""
        k1 = rag_cache_key("query1", {})
        k2 = rag_cache_key("query2", {})
        assert k1 != k2

    def test_mcp_cache_key_format(self):
        """MCP cache key has correct prefix."""
        key = mcp_cache_key("aws", "live_aws", "key1")
        assert key.startswith("devarchai:mcp:ctx:")

    def test_mcp_cache_key_deterministic(self):
        """Same inputs => same key."""
        k1 = mcp_cache_key("aws", "live_aws", "q")
        k2 = mcp_cache_key("aws", "live_aws", "q")
        assert k1 == k2


class TestRagCache:
    """Tests for the RagCache two-tier cache."""

    @pytest.fixture
    def cache(self):
        """Provide a fresh RagCache with mock Redis."""
        cache = RagCache(rag_ttl_seconds=60, mcp_ttl_seconds=120)
        cache._redis = MagicMock()
        cache._redis.get = AsyncMock(return_value=None)
        cache._redis.set = AsyncMock(return_value=True)
        cache._redis.delete = AsyncMock(return_value=1)
        cache._redis.keys = AsyncMock(return_value=[])
        return cache

    @pytest.mark.asyncio
    async def test_get_memory_hit(self, cache):
        """In-memory hit skips Redis."""
        import time as _time
        cache._memory["key1"] = (_time.time() + 100, {"data": "value"})
        result = await cache.get("key1")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_get_memory_miss_redis_hit(self, cache):
        """Memory miss, Redis hit => populates memory."""
        cache._redis.get = AsyncMock(return_value={"data": "from_redis"})
        result = await cache.get("key1")
        assert result == {"data": "from_redis"}
        assert "key1" in cache._memory

    @pytest.mark.asyncio
    async def test_get_memory_miss_redis_miss(self, cache):
        """Memory miss, Redis miss => returns None."""
        cache._redis.get = AsyncMock(return_value=None)
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_expired_memory_entry(self, cache):
        """Expired memory entry is removed and Redis is checked."""
        cache._memory["key1"] = (0.0, {"data": "old"})  # expired
        cache._redis.get = AsyncMock(return_value=None)
        result = await cache.get("key1")
        assert result is None
        assert "key1" not in cache._memory

    @pytest.mark.asyncio
    async def test_set_stores_in_memory_and_redis(self, cache):
        """set() stores in both memory and Redis."""
        await cache.set("key1", {"data": "value"}, ttl_seconds=60)
        assert "key1" in cache._memory
        cache._redis.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_with_none_value(self, cache):
        """set() with None value still stores (no special None handling)."""
        await cache.set("key1", None)
        # Memory stores any value including None
        assert "key1" in cache._memory

    @pytest.mark.asyncio
    async def test_invalidate_removes_from_memory(self, cache):
        """invalidate removes from memory."""
        cache._memory["key1"] = (100.0, {"data": "x"})
        count = await cache.invalidate("key1")
        assert count == 1
        assert "key1" not in cache._memory

    @pytest.mark.asyncio
    async def test_invalidate_all(self, cache):
        """invalidate() with None pattern clears all memory entries."""
        cache._memory["a"] = (100.0, {"data": "1"})
        cache._memory["b"] = (100.0, {"data": "2"})
        count = await cache.invalidate()
        assert count == 2
        assert len(cache._memory) == 0

    @pytest.mark.asyncio
    async def test_stats(self, cache):
        """stats returns cache statistics."""
        cache._memory["k1"] = (100.0, {"data": "v"})
        stats = await cache.stats()
        assert "memory_entries" in stats
        assert stats["memory_entries"] >= 1

    @pytest.mark.asyncio
    async def test_redis_down_get_returns_none(self, cache):
        """Redis failure during get => returns None (fail-open)."""
        cache._redis.get = AsyncMock(side_effect=Exception("redis down"))
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_down_set_continues(self, cache):
        """Redis failure during set => memory still works (fail-open)."""
        cache._redis.set = AsyncMock(side_effect=Exception("redis down"))
        await cache.set("key1", {"data": "value"}, ttl_seconds=60)
        # Memory should still store the value
        assert "key1" in cache._memory
