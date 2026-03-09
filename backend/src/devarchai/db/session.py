"""Database engine and session management."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import structlog

from devarchai.config import settings
from devarchai.db.base import Base

logger = structlog.get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
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
                pool_pre_ping=True,  # Enable connection health checks
                echo=settings.DEBUG,
                pool_recycle=3600,  # Recycle connections after 1 hour
            )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
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


async def init_db() -> None:
    """Initialize database tables."""
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from devarchai.models import (  # noqa: F401
                User,
                Organization,
                OrganizationMember,
                Project,
                Repository,
                Scan,
                Finding,
                Report,
                Subscription,
                AuditLog,
            )

            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
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
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connections closed")
