"""Unit tests for the Redis-backed token blacklist (fail-closed)."""
import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBlacklistRedisError:
    """Verify BlacklistRedisError is a proper exception subclass."""

    def test_is_exception(self):
        from app.services.token_blacklist import BlacklistRedisError
        assert issubclass(BlacklistRedisError, Exception)

    def test_can_be_caught(self):
        from app.services.token_blacklist import BlacklistRedisError
        try:
            raise BlacklistRedisError("test")
        except BlacklistRedisError as e:
            assert str(e) == "test"


def _make_connected_cache():
    """Create a mock Redis cache that is connected with async methods."""
    cache = MagicMock()
    cache.is_connected = True
    cache._redis = MagicMock()
    cache._redis.setex = AsyncMock(return_value=True)
    cache._redis.get = AsyncMock(return_value=None)
    cache._redis.exists = AsyncMock(return_value=False)
    cache._redis.delete = AsyncMock(return_value=1)
    return cache


def _make_disconnected_cache():
    """Create a mock Redis cache that is NOT connected."""
    cache = MagicMock()
    cache.is_connected = False
    cache._redis = None
    return cache


class TestBlacklistToken:
    """Tests for blacklist_token()."""

    @pytest.mark.asyncio
    async def test_blacklist_token_success(self):
        """Token is successfully blacklisted with TTL."""
        cache = _make_connected_cache()
        with patch("app.services.token_blacklist.get_cache", new_callable=AsyncMock, return_value=cache):
            from app.services.token_blacklist import blacklist_token
            result = await blacklist_token("test-jti-123", expires_in=timedelta(hours=1))
            assert result is True

    @pytest.mark.asyncio
    async def test_blacklist_token_empty_jti_returns_false(self):
        """Empty or falsy jti returns False without touching Redis."""
        from app.services.token_blacklist import blacklist_token
        result = await blacklist_token("")
        assert result is False
        result = await blacklist_token(None)
        assert result is False

    @pytest.mark.asyncio
    async def test_blacklist_token_redis_down_raises(self):
        """Redis unavailable => BlacklistRedisError (fail closed)."""
        cache = _make_disconnected_cache()
        with patch("app.services.token_blacklist.get_cache", new_callable=AsyncMock, return_value=cache):
            from app.services.token_blacklist import blacklist_token, BlacklistRedisError
            with pytest.raises(BlacklistRedisError):
                await blacklist_token("test-jti-123")

    @pytest.mark.asyncio
    async def test_blacklist_token_redis_exception_raises(self):
        """Redis exception during set => BlacklistRedisError."""
        cache = _make_connected_cache()
        cache._redis.setex = AsyncMock(side_effect=Exception("connection lost"))
        with patch("app.services.token_blacklist.get_cache", new_callable=AsyncMock, return_value=cache):
            from app.services.token_blacklist import blacklist_token, BlacklistRedisError
            with pytest.raises(BlacklistRedisError):
                await blacklist_token("test-jti-123")


class TestIsBlacklisted:
    """Tests for is_blacklisted()."""

    @pytest.mark.asyncio
    async def test_not_blacklisted(self):
        """Token not in blacklist returns False."""
        cache = _make_connected_cache()
        cache._redis.exists = AsyncMock(return_value=False)
        with patch("app.services.token_blacklist.get_cache", new_callable=AsyncMock, return_value=cache):
            from app.services.token_blacklist import is_blacklisted
            result = await is_blacklisted("test-jti-123")
            assert result is False

    @pytest.mark.asyncio
    async def test_is_blacklisted(self):
        """Token in blacklist returns True."""
        cache = _make_connected_cache()
        cache._redis.exists = AsyncMock(return_value=True)
        with patch("app.services.token_blacklist.get_cache", new_callable=AsyncMock, return_value=cache):
            from app.services.token_blacklist import is_blacklisted
            result = await is_blacklisted("test-jti-123")
            assert result is True

    @pytest.mark.asyncio
    async def test_empty_jti_returns_false(self):
        """Empty jti returns False without touching Redis."""
        from app.services.token_blacklist import is_blacklisted
        result = await is_blacklisted("")
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_down_raises(self):
        """Redis unavailable => BlacklistRedisError (fail closed)."""
        cache = _make_disconnected_cache()
        with patch("app.services.token_blacklist.get_cache", new_callable=AsyncMock, return_value=cache):
            from app.services.token_blacklist import is_blacklisted, BlacklistRedisError
            with pytest.raises(BlacklistRedisError):
                await is_blacklisted("test-jti-123")

    @pytest.mark.asyncio
    async def test_redis_exception_raises(self):
        """Redis exception during get => BlacklistRedisError."""
        cache = _make_connected_cache()
        cache._redis.exists = AsyncMock(side_effect=Exception("connection lost"))
        with patch("app.services.token_blacklist.get_cache", new_callable=AsyncMock, return_value=cache):
            from app.services.token_blacklist import is_blacklisted, BlacklistRedisError
            with pytest.raises(BlacklistRedisError):
                await is_blacklisted("test-jti-123")


class TestBlacklistUserTokens:
    """Tests for blacklist_user_tokens() (best-effort, fail-open)."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Successfully blacklists all user tokens."""
        cache = _make_connected_cache()
        with patch("app.services.token_blacklist.get_cache", new_callable=AsyncMock, return_value=cache):
            from app.services.token_blacklist import blacklist_user_tokens
            result = await blacklist_user_tokens("user-123")
            assert result is True

    @pytest.mark.asyncio
    async def test_redis_down_returns_false(self):
        """Redis unavailable returns False (fail-open for bulk ops)."""
        cache = _make_disconnected_cache()
        with patch("app.services.token_blacklist.get_cache", new_callable=AsyncMock, return_value=cache):
            from app.services.token_blacklist import blacklist_user_tokens
            result = await blacklist_user_tokens("user-123")
            assert result is False

    @pytest.mark.asyncio
    async def test_exception_returns_false(self):
        """Generic exception returns False (best-effort)."""
        cache = _make_connected_cache()
        cache._redis.scan_iter = AsyncMock(side_effect=Exception("boom"))
        with patch("app.services.token_blacklist.get_cache", new_callable=AsyncMock, return_value=cache):
            from app.services.token_blacklist import blacklist_user_tokens
            result = await blacklist_user_tokens("user-123")
            assert result is False
