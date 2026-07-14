"""Database migration runner using Alembic.

Handles stamping existing databases and running pending migrations
on application startup.
"""

import structlog
from sqlalchemy import create_engine, inspect

from app.config import settings

logger = structlog.get_logger(__name__)

_ALEMBIC_CFG_PATH = "alembic.ini"

# Tables that should exist after migrations are applied (any one will do)
_APP_TABLES = {"users", "scans", "findings"}


def _sync_url() -> str:
    """Convert async DATABASE_URL to a sync-compatible URL."""
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    elif url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite+aiosqlite://", "sqlite:///")
    return url


def check_db_connection() -> bool:
    """Verify the database is reachable with a simple query."""
    from sqlalchemy import text

    engine = None
    try:
        engine = create_engine(_sync_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        if engine is not None:
            engine.dispose()


def _schema_is_at_head(inspector) -> bool:
    """Verify the database schema actually matches the head migration.

    Checks for key columns added by recent migrations to avoid incorrectly
    stamping a database that was created with create_all() before later
    migrations were added.
    """
    try:
        scans_columns = {col["name"] for col in inspector.get_columns("scans")}
        # Migration 021 adds current_stage — the latest schema change.
        # If this column exists, assume the schema is at head.
        return "current_stage" in scans_columns
    except Exception:
        return False


def stamp_if_needed() -> bool:
    """Stamp the database at the latest migration if alembic_version is missing.

    Returns True if a stamp was applied, False if alembic_version already existed.
    """
    import alembic.command
    import alembic.config

    url = _sync_url()
    engine = create_engine(url)
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    has_version_table = "alembic_version" in existing_tables
    has_app_tables = bool(existing_tables & _APP_TABLES)

    # Fresh database (no tables at all): create everything from models,
    # then stamp at head.  This avoids the problem where migrations 002-006
    # try to ALTER tables that were never created by an earlier migration.
    if not has_version_table and not has_app_tables:
        engine.dispose()
        _bootstrap_fresh_database(url)
        cfg = alembic.config.Config(_ALEMBIC_CFG_PATH)
        cfg.set_main_option("sqlalchemy.url", url)
        alembic.command.stamp(cfg, "head")
        logger.info("Fresh database bootstrapped: all tables created, stamped at head")
        return True

    # Verify schema completeness BEFORE disposing the engine — the inspector
    # needs a live connection to read column metadata.
    schema_ok = True
    if has_app_tables and not has_version_table:
        schema_ok = _schema_is_at_head(inspector)

    engine.dispose()

    if has_version_table:
        return False

    if not has_app_tables:
        return False

    if not schema_ok:
        logger.error(
            "Database has app tables but no alembic_version table, and the "
            "schema is missing columns from recent migrations. "
            "Cannot automatically determine the correct Alembic revision. "
            "Please add the missing columns manually and then run: "
            "alembic stamp head"
        )
        return False

    cfg = alembic.config.Config(_ALEMBIC_CFG_PATH)
    cfg.set_main_option("sqlalchemy.url", url)
    alembic.command.stamp(cfg, "head")
    logger.info("Stamped existing database at head migration")
    return True


def _bootstrap_fresh_database(url: str) -> None:
    """Create all tables from SQLAlchemy models on a completely empty database."""
    from sqlalchemy import create_engine as _create

    import app.models  # noqa: F401 — ensure every model is registered on Base.metadata
    from app.db.base import Base

    sync_url = url
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")
    elif sync_url.startswith("sqlite+aiosqlite://"):
        sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite:///")

    engine = _create(sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    logger.info("Created all tables from SQLAlchemy models")


def run_migrations() -> None:
    """Run all pending Alembic migrations."""
    import alembic.command
    import alembic.config

    url = _sync_url()
    cfg = alembic.config.Config(_ALEMBIC_CFG_PATH)
    cfg.set_main_option("sqlalchemy.url", url)

    stamp_if_needed()

    alembic.command.upgrade(cfg, "head")
    logger.info("Database migrations up to date")


def current_revision() -> str | None:
    """Return the current Alembic revision of the database, or None."""
    import alembic.command
    import alembic.config

    url = _sync_url()
    cfg = alembic.config.Config(_ALEMBIC_CFG_PATH)
    cfg.set_main_option("sqlalchemy.url", url)
    try:
        result = alembic.command.current(cfg)
        return result.strip() if result else None
    except Exception:
        return None


def pending_migrations() -> list[str]:
    """Return a list of migration revisions that have not been applied yet."""
    import alembic.config

    url = _sync_url()
    cfg = alembic.config.Config(_ALEMBIC_CFG_PATH)
    cfg.set_main_option("sqlalchemy.url", url)

    try:
        from sqlalchemy import create_engine

        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(cfg)
        head = script.get_current_head()

        if head:
            engine = create_engine(url)
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current = context.get_current_revision()
            engine.dispose()

            if current == head:
                return []
            pending = []
            for rev in script.walk_revisions(base=current, head=head):
                pending.append(rev.revision)
            return pending
        return []
    except Exception:
        return []
