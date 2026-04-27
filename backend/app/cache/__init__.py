"""
Redis Cache Service for DevArchAI.

Provides a high-level caching interface backed by Redis for:
- AI response caching
- Scan result caching
- General-purpose key/value caching with TTL support
"""

from app.cache.redis_cache import CacheBackend, RedisCache, get_cache

__all__ = [
    "CacheBackend",
    "RedisCache",
    "get_cache",
]
