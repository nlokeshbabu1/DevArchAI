"""Database migration runner using Alembic.

Handles the three database states that can exist at application startup:

1. **Fresh database** (no tables at all): bootstrap the full schema from the
   SQLAlchemy models, then stamp the head migration. This avoids the problem
   where early migrations try to ALTER tables that were never created.
2. **Orphan database** (app tables present, but no ``alembic_version`` table):
   estimate the effective revision from schema markers, stamp it, and then run
   pending migrations.
3. **Migrated database**: run pending migrations only. Refuses to downgrade if
   the database revision is ahead of this application's migrations.

Concurrent instance startups are serialized with a PostgreSQL advisory lock
(see ``migration_lock``); schema drift is verified after migrating (see
``app.db.init``).
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager

import structlog
from sqlalchemy import create_engine, inspect, text

from app.config import settings

logger = structlog.get_logger(__name__)

_ALEMBIC_CFG_PATH = "alembic.ini"

# Advisory lock key used to serialize concurrent database migrations.
# Must fit in a 63-bit PostgreSQL bigint.
_MIGRATION_LOCK_KEY = 0x44424132  # "DBA2"

# Tables that should exist after migrations are applied (any one will do)
_APP_TABLES = {"users", "scans", "findings"}

# Schema markers used to estimate the effective Alembic revision of an orphan
# database (app tables present, but no alembic_version table).  Each entry is
# ``(revision, table, column_or_None)``; a column of ``None`` means "table
# exists".  This mirrors the operations performed by each migration.
#
# Special sentinels:
# - ``column="_has_rows"``: checks whether the table has any rows (for seed
#   migrations that don't alter schema).
# - ``table="_enum:<type_name>"``: checks whether a PostgreSQL enum type
#   contains the given ``column`` value (for enum-altering migrations).
_MIGRATION_MARKERS: list[tuple[str, str, str | None]] = [
    ("001", "repo_analysis", None),
    ("002", "findings", "ai_generated"),
    ("003", "findings", "documentation_url"),
    ("004", "findings", "summary"),
    ("005", "users", "email_hash"),
    ("006", "scans", "detected_stack"),
    ("007", "pull_requests", None),
    ("008", "github_installations", None),
    ("009", "users", "github_login"),
    ("010", "users", "selected_country"),
    ("011", "users", "subscription_status"),
    ("012", "scans", "ai_status"),
    ("013", "reports", "pdf_s3_key"),
    ("014", "user_preferences", None),
    ("015", "aws_accounts", None),
    ("016", "users", "mfa_enabled"),
    ("017", "users", "failed_login_attempts"),
    ("018", "repo_analysis", "user_id"),
    ("019", "findings", "scanner_name"),
    ("020", "scanner_execution_records", None),
    ("021", "scans", "current_stage"),
    ("022", "organizations", None),
    ("023", "cloud_connections", None),
    ("024", "cloud_compliance_results", "provider"),
    ("025", "cloud_cost_recommendations", "resource_type"),
    ("027", "cloud_resources", "last_scan_id"),
    ("028", "cloud_ai_recommendations", None),
    ("029", "cloud_findings", "last_scan_id"),
    ("030", "cloud_ai_recommendations", "cloudformation_fix"),
    ("031", "ai_recommendations", None),
    ("032", "knowledge_documents", None),
    ("033", "scan_ai_recommendations", None),
    ("034", "users", "token_encryption_version"),
    ("035", "plans", "_has_rows"),
    ("036", "user_sessions", "token_family"),
    ("037", "finding_ai_jobs", None),
    ("038", "_enum:scanstage", "analyzing_findings"),
    ("039", "kubernetes_connections", None),
    ("040", "_enum:membershiprole", "owner"),
]


class DatabaseInitializationError(RuntimeError):
    """Raised when the database cannot be brought to a consistent state."""


def _sync_url() -> str:
    """Convert async DATABASE_URL to a sync-compatible URL."""
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    elif url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://")
    elif url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite+aiosqlite://", "sqlite:///")
    return url


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql://")


def _alembic_config(url: str):
    import alembic.config

    cfg = alembic.config.Config(_ALEMBIC_CFG_PATH)
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def check_db_connection() -> bool:
    """Verify the database is reachable with a simple query."""
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


@contextmanager
def migration_lock(timeout: int | None = None) -> Iterator[None]:
    """Serialize database migrations across concurrent application instances.

    Uses a PostgreSQL advisory lock so that only one instance runs schema
    changes at a time.  On non-PostgreSQL backends (e.g. SQLite) this is a
    no-op.
    """
    if timeout is None:
        timeout = settings.DB_MIGRATION_LOCK_TIMEOUT

    url = _sync_url()
    if not _is_postgres(url):
        yield
        return

    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    conn = engine.connect()
    acquired = False
    try:
        deadline = time.monotonic() + timeout
        while not acquired:
            acquired = bool(
                conn.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": _MIGRATION_LOCK_KEY},
                ).scalar()
            )
            if not acquired:
                if time.monotonic() >= deadline:
                    raise DatabaseInitializationError(
                        "Timed out waiting for the database migration lock. "
                        "Another application instance may be holding it. "
                        "Increase DB_MIGRATION_LOCK_TIMEOUT if this persists."
                    )
                time.sleep(0.5)
        logger.info("Acquired database migration lock", timeout=timeout)
        yield
    finally:
        if acquired:
            try:
                conn.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": _MIGRATION_LOCK_KEY},
                )
            except Exception:
                pass
        conn.close()
        engine.dispose()


def detect_database_state(url: str) -> str:
    """Classify the database state.

    Returns one of:
    - ``"fresh"``: no tables at all — bootstrap from models and stamp head.
    - ``"orphan"``: app tables exist but ``alembic_version`` is missing.
    - ``"migrated"``: ``alembic_version`` exists (version tracked by Alembic).
    """
    engine = create_engine(url)
    try:
        existing_tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    has_version_table = "alembic_version" in existing_tables
    has_app_tables = bool(existing_tables & _APP_TABLES)

    if not has_version_table and not has_app_tables:
        return "fresh"
    if has_app_tables and not has_version_table:
        return "orphan"
    return "migrated"


def estimate_revision(url: str) -> str | None:
    """Estimate the effective Alembic revision of an orphan database.

    Checks schema markers (tables/columns introduced by each migration) and
    returns the highest revision whose markers are present.  Returns ``None``
    if no markers match.

    Markers are validated for continuity: a marker only counts if the marker
    for the preceding revision is also present.  This prevents a partial
    upgrade from being misidentified — e.g. an orphan database that reached a
    later additive table while earlier revisions' tables/columns were dropped
    must be estimated at the highest contiguous revision so the pending
    migrations can repair it.
    """
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        column_cache: dict[str, set[str]] = {}

        def has_marker(table: str, column: str | None) -> bool:
            # Special sentinel: check if a table has any rows (for seed migrations).
            if column == "_has_rows":
                if table not in table_names:
                    return False
                try:
                    with engine.connect() as conn:
                        return conn.execute(
                            text(f"SELECT 1 FROM {table} LIMIT 1")
                        ).scalar() is not None
                except Exception:
                    return False
            # Special sentinel: check if a PostgreSQL enum type contains a value.
            if table.startswith("_enum:"):
                enum_type = table[len("_enum:"):]
                try:
                    with engine.connect() as conn:
                        return conn.execute(
                            text(
                                "SELECT 1 FROM pg_enum e "
                                "JOIN pg_type t ON e.enumtypid = t.oid "
                                "WHERE t.typname = :typname AND e.enumlabel = :label"
                            ),
                            {"typname": enum_type, "label": column},
                        ).scalar() is not None
                except Exception:
                    return False
            if table not in table_names:
                return False
            if column is None:
                return True
            if table not in column_cache:
                try:
                    column_cache[table] = {col["name"] for col in inspector.get_columns(table)}
                except Exception:
                    return False
            return column in column_cache[table]

        estimated: str | None = None
        previous_present = True
        for revision, table, column in _MIGRATION_MARKERS:
            if previous_present and has_marker(table, column):
                estimated = revision
                previous_present = True
            else:
                previous_present = False
        return estimated
    finally:
        engine.dispose()


def _bootstrap_fresh_database(cfg) -> None:
    """Bring a completely empty database to the head revision.

    On PostgreSQL this runs the full Alembic migration chain from scratch so
    the resulting schema exactly mirrors the migrations (no drift by
    construction).  The pgvector extension is ensured up front; the RAG
    migration also issues ``CREATE EXTENSION IF NOT EXISTS vector``.

    Non-PostgreSQL backends (e.g. SQLite test harnesses) can't run the
    PostgreSQL-specific migration chain, so they fall back to
    ``Base.metadata.create_all`` + ``stamp head``.
    """
    import alembic.command

    url = cfg.get_main_option("sqlalchemy.url")
    if _is_postgres(url):
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
        finally:
            engine.dispose()
        alembic.command.upgrade(cfg, "head")
        logger.info("Fresh database migrated to head from scratch")
        return

    import app.models  # noqa: F401 — ensure every model is registered on Base.metadata
    from app.db.base import Base

    engine = create_engine(url)
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    alembic.command.stamp(cfg, "head")
    logger.info("Fresh database bootstrapped from models and stamped at head")


def _check_not_newer_than_head(cfg, current: str | None) -> None:
    """Refuse to proceed if the database is ahead of this application's migrations."""
    if not current:
        return

    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(cfg)
    try:
        revision = script.get_revision(current)
    except Exception:
        revision = None
    if revision is None:
        raise DatabaseInitializationError(
            f"Database is at Alembic revision '{current}', which is not part of "
            "this application's migration history (head is "
            f"'{script.get_current_head()}'). The database appears to be newer "
            "than this application. Refusing to downgrade. Upgrade the "
            "application or point it at the correct database."
        )


def _current_revision_impl(cfg) -> str | None:
    from alembic.runtime.migration import MigrationContext

    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current = context.get_current_revision()
            if isinstance(current, tuple | list):
                return ",".join(sorted(current))
            return current
    finally:
        engine.dispose()


def migrate_database() -> None:
    """Bring the database to the head migration, in place.

    Handles fresh, orphan, and migrated databases.  Must be called while
    holding ``migration_lock``.
    """
    import alembic.command

    url = _sync_url()
    cfg = _alembic_config(url)

    state = detect_database_state(url)
    if state == "fresh":
        _bootstrap_fresh_database(cfg)
    elif state == "orphan":
        current = _current_revision_impl(cfg)
        if current:
            raise DatabaseInitializationError(
                "Database has no alembic_version table but the revision could "
                f"not be determined: '{current}'."
            )
        estimated = estimate_revision(url)
        if estimated is None:
            raise DatabaseInitializationError(
                "Database has application tables but no alembic_version table, "
                "and the effective schema revision could not be determined from "
                "schema markers. Cannot safely migrate. Inspect the database "
                "manually and stamp the correct revision with "
                "'alembic stamp <revision>'."
            )
        alembic.command.stamp(cfg, estimated)
        logger.info("Orphan database stamped at estimated revision", revision=estimated)
        try:
            _upgrade_to_head(cfg)
        except Exception as exc:
            raise DatabaseInitializationError(
                "Database had application tables but no alembic_version table, "
                f"and the estimated revision '{estimated}' could not be upgraded "
                f"to head: {exc}. This usually means the schema was created "
                "outside Alembic (e.g. with create_all) and conflicts with "
                "pending migrations. The migration was rolled back and the "
                "database was left unchanged. Reconcile the schema (for example "
                "with 'alembic revision --autogenerate') or recreate the "
                "database from migrations, then retry."
            ) from exc
    else:
        _upgrade_to_head(cfg)


def _upgrade_to_head(cfg) -> None:
    import alembic.command

    current = _current_revision_impl(cfg)
    _check_not_newer_than_head(cfg, current)
    alembic.command.upgrade(cfg, "head")
    logger.info("Database migrations up to date")


def run_migrations() -> None:
    """Run all pending Alembic migrations (no verification).

    Prefer ``app.db.init.initialize_database`` for application startup, which
    additionally serializes concurrency and verifies the resulting schema.
    """
    with migration_lock():
        migrate_database()


def current_revision() -> str | None:
    """Return the current Alembic revision of the database, or None."""
    cfg = _alembic_config(_sync_url())
    try:
        return _current_revision_impl(cfg)
    except Exception:
        return None


def pending_migrations() -> list[str]:
    """Return a list of migration revisions that have not been applied yet."""
    import alembic.config

    url = _sync_url()
    cfg = alembic.config.Config(_ALEMBIC_CFG_PATH)
    cfg.set_main_option("sqlalchemy.url", url)

    try:
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
            for rev in script.walk_revisions(base=current or "base", head=head):
                pending.append(rev.revision)
            return pending
        return []
    except Exception:
        return []
