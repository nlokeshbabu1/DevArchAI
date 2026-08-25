"""Shared fixtures for integration tests.

Resets application singletons (Redis cache, DB engine) before each test
so connections are established in the current event loop, not a stale one.
"""

import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def _reset_app_singletons():
    """Reset Redis cache and DB engine singletons before each test.

    The Redis cache and SQLAlchemy engine are module-level singletons.  When
    pytest-asyncio creates a new event loop per test, connections from the
    previous loop become stale and cause ``RuntimeError: Event loop is closed``.
    Resetting the singletons forces fresh connections in the current loop.
    """
    import app.cache.redis_cache as redis_mod
    import app.db.session as session_mod

    # Save originals
    orig_cache = redis_mod._cache_instance
    orig_engine = session_mod._engine
    orig_session_factory = session_mod._session_factory

    # Reset
    redis_mod._cache_instance = None
    session_mod._engine = None
    session_mod._session_factory = None

    yield

    # Restore originals (for cleanup if needed)
    redis_mod._cache_instance = orig_cache
    session_mod._engine = orig_engine
    session_mod._session_factory = orig_session_factory


@pytest_asyncio.fixture
async def client():
    """Async HTTP client bound to the FastAPI ASGI app."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def test_db():
    """Async DB session using the same engine as the application's get_db."""
    from app.db.session import get_session_factory

    session = get_session_factory()()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


@pytest.fixture
def sample_repo_data():
    """Minimal repository metadata for scan API requests."""
    return {
        "repository_url": "https://github.com/test/sample-repo",
        "branch": "main",
        "include_ai_explanations": True,
    }
