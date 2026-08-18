"""Migration integration tests.

Verifies that Alembic migrations produce the expected schema and can be
applied/reverted cleanly.  Requires a running PostgreSQL instance
(configured via TEST_DATABASE_URL or DATABASE_URL).
"""

from __future__ import annotations

import os

import alembic.command
import alembic.config
import pytest
from sqlalchemy import create_engine, inspect, text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SYNC_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/devarchai_test"),
)
if _SYNC_URL.startswith("postgresql+asyncpg://"):
    _SYNC_URL = _SYNC_URL.replace("postgresql+asyncpg://", "postgresql://")


def _alembic_cfg() -> alembic.config.Config:
    cfg = alembic.config.Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _SYNC_URL)
    return cfg


@pytest.fixture()
def alembic_cfg():
    """Yield a fresh alembic config pointing at the test database."""
    return _alembic_cfg()


@pytest.fixture()
def engine():
    engine = create_engine(_SYNC_URL)
    yield engine
    engine.dispose()


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
    "aws_integrations",
    "audit_logs",
    "settings",
    "repo_analysis",
    "scanner_executions",
    "ai_suggestions",
    "organizations",
}

# table → set of columns that must exist
EXPECTED_COLUMNS: dict[str, set[str]] = {
    "users": {"id", "email", "hashed_password", "is_active", "github_login"},
    "scans": {
        "id",
        "repo_url",
        "status",
        "current_stage",
        "ai_status",
        "report_s3_key",
        "report_gcs_path",
    },
    "findings": {
        "id",
        "scan_id",
        "rule_id",
        "severity",
        "category",
        "description",
        "ai_generated",
        "ai_fix_suggestion",
        "scanner_metadata",
    },
    "pull_requests": {"id", "scan_id", "pr_url", "branch_name"},
    "github_installations": {"id", "installation_id", "github_app_id", "account_login"},
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

        engine = create_engine(_SYNC_URL)
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

        engine = create_engine(_SYNC_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
        engine.dispose()

        assert result == 1

    def test_expected_tables_exist(self, alembic_cfg):
        """After upgrading to head all expected tables are present."""
        alembic.command.upgrade(alembic_cfg, "head")

        engine = create_engine(_SYNC_URL)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        engine.dispose()

        missing = EXPECTED_TABLES - tables
        assert not missing, f"Missing tables after migration: {missing}"

    def test_expected_columns_exist(self, alembic_cfg):
        """After upgrading to head, key columns on critical tables exist."""
        alembic.command.upgrade(alembic_cfg, "head")

        engine = create_engine(_SYNC_URL)
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

        engine = create_engine(_SYNC_URL)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current = context.get_current_revision()
        engine.dispose()

        assert current == head, (
            f"Database revision '{current}' does not match head '{head}'"
        )
