"""Database initialization integration tests.

Verifies the startup database flow (lock -> migrate -> verify -> fail fast)
against a dedicated throwaway database.  The schema is reset before every
test, so destructive mutations never leak between tests.

Requires a running PostgreSQL instance with credentials that can create
databases (parsed from ``DATABASE_URL`` / ``app.config.settings``).
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
import structlog
from sqlalchemy import create_engine, inspect, text

from app.config import settings
from app.db.base import Base
from app.db.init import initialize_database
from app.db.migrate import DatabaseInitializationError, current_revision, migration_lock
from app.db.verify import verify_schema

structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    logger_factory=structlog.PrintLoggerFactory(),
)

_TEST_DB_NAME = "devarchai_init_test"
_MIGRATION_LOCK_KEY = 0x44424132


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _maintenance_connect():
    import psycopg2

    url = sa.make_url(settings.DATABASE_URL)
    kwargs = {
        "host": url.host,
        "port": url.port,
        "user": url.username,
        "password": url.password,
        "connect_timeout": 5,
    }
    return psycopg2.connect(dbname="postgres", **kwargs)


@pytest.fixture(scope="module")
def init_test_db():
    """Create a dedicated throwaway database and point settings at it."""
    base_url = sa.make_url(settings.DATABASE_URL)
    original_url = settings.DATABASE_URL
    original_timeout = settings.DB_MIGRATION_LOCK_TIMEOUT

    conn = _maintenance_connect()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB_NAME}"')
            cur.execute(f'CREATE DATABASE "{_TEST_DB_NAME}" OWNER {base_url.username}')
    finally:
        conn.close()

    test_url = (
        f"postgresql://{base_url.username}:{base_url.password}"
        f"@{base_url.host}:{base_url.port}/{_TEST_DB_NAME}"
    )
    settings.DATABASE_URL = test_url
    try:
        yield test_url
    finally:
        settings.DATABASE_URL = original_url
        settings.DB_MIGRATION_LOCK_TIMEOUT = original_timeout
        conn = _maintenance_connect()
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    f"WHERE datname = '{_TEST_DB_NAME}' AND pid <> pg_backend_pid()"
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB_NAME}"')
        finally:
            conn.close()


def _reset_schema(url: str) -> None:
    """Drop and recreate the public schema for a clean slate."""
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("DROP SCHEMA public CASCADE")
            conn.exec_driver_sql("CREATE SCHEMA public")
            conn.commit()
    finally:
        engine.dispose()


@pytest.fixture()
def initialized(init_test_db):
    """Reset the database and run the full startup initialization."""
    _reset_schema(init_test_db)
    initialize_database()
    return init_test_db


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _columns(url: str, table: str) -> set[str]:
    engine = create_engine(url)
    try:
        return {col["name"] for col in inspect(engine).get_columns(table)}
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.requires_db
class TestDatabaseInitialization:
    def test_fresh_database_creates_all_model_tables(self, initialized):
        """A fresh database gets every model table plus alembic_version."""
        import app.models  # noqa: F401

        tables = _tables(initialized)
        expected = {t for t in Base.metadata.tables if t != "alembic_version"}
        missing = expected - tables
        assert not missing, f"Missing tables after fresh init: {missing}"
        assert "alembic_version" in tables

    def test_ai_recommendation_tables_created(self, initialized):
        """Regression: the three previously-unimported models must be created."""
        for table in (
            "ai_recommendations",
            "anonymous_scans",
            "cloud_ai_recommendations",
        ):
            assert table in _tables(initialized), f"{table} not created on fresh DB"

        assert "cloudformation_fix" in _columns(initialized, "cloud_ai_recommendations")

    def test_initialization_is_idempotent(self, initialized):
        """Running initialization twice is a no-op."""
        initialize_database()
        assert current_revision() == "032"
        assert _tables(initialized) == _tables(initialized)

    def test_orphan_database_is_restamped(self, initialized):
        """App tables with no alembic_version get re-stamped and verified."""
        engine = create_engine(initialized)
        with engine.connect() as conn:
            conn.exec_driver_sql("DROP TABLE alembic_version")
            conn.commit()
        engine.dispose()

        initialize_database()
        assert current_revision() == "032"
        assert "alembic_version" in _tables(initialized)

    def test_newer_database_is_refused(self, initialized):
        """A database ahead of the app's migrations fails startup (no downgrade)."""
        engine = create_engine(initialized)
        with engine.connect() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num='999'"))
            conn.commit()
        engine.dispose()

        with pytest.raises(DatabaseInitializationError, match="newer than this application"):
            initialize_database()

    def test_missing_column_fails_startup(self, initialized):
        """Drift after migrations aborts startup with a clear message."""
        engine = create_engine(initialized)
        with engine.connect() as conn:
            conn.exec_driver_sql("ALTER TABLE scans DROP COLUMN current_stage")
            conn.commit()
        engine.dispose()

        with pytest.raises(DatabaseInitializationError, match="scans\\.current_stage"):
            initialize_database()

    def test_missing_column_is_repaired_via_migrations(self, initialized):
        """An orphan DB with drift is repaired by the pending migrations."""
        engine = create_engine(initialized)
        with engine.connect() as conn:
            conn.exec_driver_sql("DROP TABLE alembic_version")
            conn.exec_driver_sql(
                "ALTER TABLE cloud_ai_recommendations DROP COLUMN cloudformation_fix"
            )
            conn.exec_driver_sql("DROP TABLE ai_recommendations")
            conn.exec_driver_sql("DROP TABLE mcp_context")
            conn.exec_driver_sql("DROP TABLE rag_chunks")
            conn.exec_driver_sql("DROP TABLE knowledge_documents")
            conn.commit()
        engine.dispose()

        initialize_database()
        assert current_revision() == "032"
        assert "ai_recommendations" in _tables(initialized)
        assert "cloudformation_fix" in _columns(initialized, "cloud_ai_recommendations")
        assert "knowledge_documents" in _tables(initialized)
        assert "rag_chunks" in _tables(initialized)
        assert "mcp_context" in _tables(initialized)

    def test_migration_lock_contention(self, initialized):
        """A concurrent instance holding the lock blocks then fails clearly."""
        from app.db.migrate import _sync_url

        holder = create_engine(_sync_url(), isolation_level="AUTOCOMMIT").connect()
        try:
            acquired = holder.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": _MIGRATION_LOCK_KEY},
            ).scalar()
            assert acquired
            settings.DB_MIGRATION_LOCK_TIMEOUT = 2
            with pytest.raises(DatabaseInitializationError, match="migration lock"):
                initialize_database()
        finally:
            holder.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": _MIGRATION_LOCK_KEY},
            )
            holder.close()


@pytest.mark.requires_db
class TestSchemaVerification:
    def test_type_mismatch_reported(self, initialized):
        """Incompatible column types are reported as blocking errors."""
        engine = create_engine(initialized)
        with engine.connect() as conn:
            conn.exec_driver_sql(
                "ALTER TABLE users ALTER COLUMN is_active TYPE integer USING is_active::int"
            )
            conn.commit()
        engine.dispose()

        report = verify_schema(initialized, database_revision="032")
        assert not report.ok
        type_errors = [i for i in report.errors if i.kind == "type_mismatch"]
        assert any(i.table == "users" and i.column == "is_active" for i in type_errors)

    def test_missing_table_reported(self, initialized):
        """Missing tables are reported as blocking errors."""
        engine = create_engine(initialized)
        with engine.connect() as conn:
            conn.exec_driver_sql("DROP TABLE findings CASCADE")
            conn.commit()
        engine.dispose()

        report = verify_schema(initialized, database_revision="032")
        assert not report.ok
        assert any(i.kind == "missing_table" and i.table == "findings" for i in report.errors)

    def test_missing_primary_key_reported(self, initialized):
        """A table without its model primary key is reported as blocking."""
        engine = create_engine(initialized)
        with engine.connect() as conn:
            conn.exec_driver_sql("ALTER TABLE users DROP CONSTRAINT users_pkey CASCADE")
            conn.commit()
        engine.dispose()

        report = verify_schema(initialized, database_revision="032")
        assert not report.ok
        assert any(i.kind == "primary_key_mismatch" and i.table == "users" for i in report.errors)


@pytest.mark.requires_db
class TestMigrationLock:
    def test_lock_is_reentrant_across_runs(self, initialized):
        """The lock acquires and releases cleanly around initialization."""
        with migration_lock():
            pass
        with migration_lock():
            pass
