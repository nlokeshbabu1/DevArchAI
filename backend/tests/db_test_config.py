"""Shared test PostgreSQL URLs (isolated test container / pytest-env).

Both sync (Alembic, psycopg2) and async (asyncpg) URLs must target the same
database. Do not fall back to DATABASE_URL from a developer ``.env`` file —
that often points at a different host credential set than TEST_DATABASE_URL.
"""

from __future__ import annotations

import os

# Default matches docker-compose.test.yml (port 5433, test-only credentials).
_DEFAULT_HOST = os.environ.get("TEST_POSTGRES_HOST", "127.0.0.1")
_DEFAULT_PORT = os.environ.get("TEST_POSTGRES_PORT", "5433")
_DEFAULT_USER = os.environ.get("TEST_POSTGRES_USER", "postgres")
_DEFAULT_DB = os.environ.get("TEST_POSTGRES_DB", "devarchai_test")

_DEFAULT_SYNC = (
    f"postgresql://{_DEFAULT_USER}:"
    f"{os.environ.get('TEST_POSTGRES_PASSWORD', 'postgres')}"
    f"@{_DEFAULT_HOST}:{_DEFAULT_PORT}/{_DEFAULT_DB}"
)


def get_test_sync_database_url() -> str:
    """SQLAlchemy/psycopg2 URL for migration and admin tests."""
    raw = os.environ.get("TEST_DATABASE_URL", _DEFAULT_SYNC)
    if raw.startswith("postgresql+asyncpg://"):
        return raw.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw


def get_test_async_database_url() -> str:
    """asyncpg URL for async integration fixtures."""
    raw = os.environ.get("TEST_DATABASE_URL", _DEFAULT_SYNC)
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw


def apply_test_database_env() -> None:
    """Point application settings at the test database when pytest loads."""
    sync = get_test_sync_database_url()
    async_url = get_test_async_database_url()
    os.environ["TEST_DATABASE_URL"] = sync
    os.environ["DATABASE_URL"] = async_url
    os.environ.setdefault("TESTING", "true")
