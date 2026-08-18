"""Database Session Management."""

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.init import initialize_database

logger = structlog.get_logger(__name__)

_engine = None
_session_factory = None
_sync_engine = None
_sync_session_factory = None


def get_engine():
    """Get or create async engine."""
    global _engine
    if _engine is None:
        connect_args = {}

        # Special handling for SQLite (useful for testing)
        if settings.DATABASE_URL.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            _engine = create_async_engine(
                settings.DATABASE_URL,
                connect_args=connect_args,
                echo=settings.DEBUG,
            )
        else:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections every hour
                echo=settings.DEBUG,
            )

    return _engine


def get_session_factory():
    """Get or create session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


def get_sync_session_factory():
    """Get or create synchronous session factory for Celery tasks."""
    global _sync_session_factory, _sync_engine
    if _sync_session_factory is None:
        # Convert async URL to sync URL
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("+aiomysql", "+pymysql")

        _sync_engine = create_engine(
            sync_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )

        _sync_session_factory = sessionmaker(
            bind=_sync_engine,
            class_=Session,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _sync_session_factory


# Alias for compatibility
SessionLocal = get_sync_session_factory


async def init_db() -> None:
    """Initialize and verify the database schema before serving traffic.

    Runs migrations under a cross-instance lock and verifies the resulting
    schema against the SQLAlchemy models, failing fast with a clear error if
    the database cannot be brought to a consistent state.
    """
    import asyncio

    try:
        await asyncio.to_thread(initialize_database)
        logger.info("Database initialized via Alembic migrations")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_factory, _sync_engine, _sync_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None
        _sync_session_factory = None
        logger.info("Database connections closed")
