"""Migration integration tests.

Verifies that Alembic migrations produce the expected schema and can be
applied/reverted cleanly.  Requires the isolated test PostgreSQL instance
(``TEST_DATABASE_URL``; see ``docker-compose.test.yml``).
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

import alembic.command
import alembic.config
import pytest
from sqlalchemy import create_engine, inspect, text

from tests.db_test_config import get_test_sync_database_url

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_current_sync_url = get_test_sync_database_url()


def _alembic_cfg() -> alembic.config.Config:
    cfg = alembic.config.Config("alembic.ini")
    # env.py ignores alembic.ini's placeholder URL; the programmatic
    # override in attributes is the supported way to target a database.
    cfg.attributes["sqlalchemy_url"] = _current_sync_url
    return cfg


@pytest.fixture()
def alembic_cfg():
    """Yield a fresh alembic config pointing at the test database."""
    return _alembic_cfg()


@pytest.fixture()
def engine():
    engine = create_engine(_current_sync_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def scratch_database():
    """Run all migration tests against an isolated, disposable database.

    Migrations run ``base -> head`` and ``downgrade``, which is destructive.
    Pointing them at a shared database destroys its data and leaves seed rows
    that break FK constraints on downgrade.  Each session therefore gets a
    dedicated scratch database (dropped afterwards).
    """
    global _current_sync_url

    parsed = urlparse(_current_sync_url)
    scratch_name = f"{parsed.path.lstrip('/')}_migrations"
    admin_url = urlunparse(parsed._replace(path="/postgres"))
    scratch_url = urlunparse(parsed._replace(path=f"/{scratch_name}"))

    def _admin_exec(statement: str) -> None:
        eng = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        try:
            with eng.connect() as conn:
                conn.execute(text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :db AND pid <> pg_backend_pid()"
                ), {"db": scratch_name})
                conn.execute(text(statement))
        finally:
            eng.dispose()

    _admin_exec(f'DROP DATABASE IF EXISTS "{scratch_name}"')
    _admin_exec(f'CREATE DATABASE "{scratch_name}"')

    original_url = _current_sync_url
    _current_sync_url = scratch_url
    yield
    _current_sync_url = original_url
    _admin_exec(f'DROP DATABASE IF EXISTS "{scratch_name}"')


# ---------------------------------------------------------------------------
# Expected schema (tables & key columns)
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {
    "users",
    "scans",
    "findings",
    "pull_requests",
    "github_installations",
    "subscriptions",
    "reports",
    "enterprise_audit_logs",
    "repo_analysis",
    "scanner_execution_records",
    "ai_suggestions",
    "organizations",
}

# table → set of columns that must exist
EXPECTED_COLUMNS: dict[str, set[str]] = {
    # User stores encrypted email (email_encrypted + SHA256 email_hash), not plaintext email
    "users": {"id", "hashed_password", "is_active", "github_login", "email_encrypted", "email_hash"},
    "scans": {
        "id",
        "repository_url",
        "status",
        "current_stage",
        "ai_status",
    },
    "findings": {
        "id",
        "scan_id",
        "rule_id",
        "severity",
        "category",
        "description",
        "ai_generated",
    },
    "pull_requests": {"id", "scan_id", "github_pr_url", "branch_name"},
    "github_installations": {"id", "installation_id", "user_id", "repo_full_name"},
    "repo_analysis": {"id", "user_id", "repo_url", "detected_stack"},
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
class TestMigrations:
    """Test suite for Alembic migration integrity."""

    def test_fresh_database_upgrade(self, alembic_cfg):
        """Upgrade a clean database from base to head without errors."""
        alembic.command.upgrade(alembic_cfg, "base")
        alembic.command.upgrade(alembic_cfg, "head")

        engine = create_engine(_current_sync_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        engine.dispose()

        assert "alembic_version" in tables
        assert tables & EXPECTED_TABLES, "Expected application tables to exist"

    def test_downgrade_and_reupgrade(self, alembic_cfg):
        """Downgrade one step then re-upgrade to head."""
        alembic.command.upgrade(alembic_cfg, "head")
        alembic.command.downgrade(alembic_cfg, "-1")
        alembic.command.upgrade(alembic_cfg, "head")

        engine = create_engine(_current_sync_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
        engine.dispose()

        assert result == 1

    def test_expected_tables_exist(self, alembic_cfg):
        """After upgrading to head all expected tables are present."""
        alembic.command.upgrade(alembic_cfg, "head")

        engine = create_engine(_current_sync_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        engine.dispose()

        missing = EXPECTED_TABLES - tables
        assert not missing, f"Missing tables after migration: {missing}"

    def test_expected_columns_exist(self, alembic_cfg):
        """After upgrading to head, key columns on critical tables exist."""
        alembic.command.upgrade(alembic_cfg, "head")

        engine = create_engine(_current_sync_url)
        inspector = inspect(engine)

        for table, expected_cols in EXPECTED_COLUMNS.items():
            if table not in inspector.get_table_names():
                pytest.fail(f"Table '{table}' does not exist")
            actual_cols = {col["name"] for col in inspector.get_columns(table)}
            missing = expected_cols - actual_cols
            assert not missing, (
                f"Table '{table}' is missing columns: {missing}"
            )

        engine.dispose()

    def test_no_pending_migrations(self, alembic_cfg):
        """After upgrade to head there are zero pending migrations."""
        alembic.command.upgrade(alembic_cfg, "head")

        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(alembic_cfg)
        head = script.get_current_head()

        engine = create_engine(_current_sync_url)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current = context.get_current_revision()
        engine.dispose()

        assert current == head, (
            f"Database revision '{current}' does not match head '{head}'"
        )
