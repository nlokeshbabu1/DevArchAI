"""Database initialization orchestrator for application startup.

Sequence on startup:

1. Check the database is reachable.
2. Acquire a PostgreSQL advisory lock (serializes concurrent instances).
3. Run migrations (``migrate_database``) — handles fresh, orphan, and
   migrated databases, and refuses to downgrade a newer database.
4. Verify the resulting schema against the SQLAlchemy models.
5. Fail fast with a clear message if anything is inconsistent.

Disabled entirely with ``DB_MIGRATE_ON_STARTUP=false``.
"""

import structlog

from app.config import settings
from app.db.migrate import (
    DatabaseInitializationError,
    _sync_url,
    check_db_connection,
    current_revision,
    migrate_database,
    migration_lock,
)
from app.db.verify import verify_schema

logger = structlog.get_logger(__name__)


def initialize_database() -> None:
    """Initialize and verify the database schema before serving traffic."""
    logger.info("Initializing database", migrate_on_startup=settings.DB_MIGRATE_ON_STARTUP)

    if not settings.DB_MIGRATE_ON_STARTUP:
        logger.warning(
            "DB_MIGRATE_ON_STARTUP=false — skipping migrations. "
            "The schema is NOT verified; the application may fail at runtime."
        )
        return

    if not check_db_connection():
        raise DatabaseInitializationError(
            "Could not connect to the database. Check DATABASE_URL and that "
            "the database server is running."
        )

    with migration_lock():
        migrate_database()
        report = verify_schema(_sync_url(), database_revision=current_revision())

    if not report.ok:
        raise DatabaseInitializationError(report.format_banner())

    if report.warnings:
        for issue in report.warnings:
            logger.warning(
                "Schema warning",
                kind=issue.kind,
                table=issue.table,
                column=issue.column,
                detail=issue.detail,
            )

    logger.info(
        "Database initialization complete",
        tables_verified=report.tables_checked,
        columns_verified=report.columns_checked,
    )
