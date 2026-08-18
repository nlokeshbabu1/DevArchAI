"""Schema check CLI.

Read-only report of the database connection, migration state, and schema
consistency.  Run with::

    cd backend && python -m app.db.check_schema

Add ``--migrate`` to run pending migrations (under the migration lock) before
verifying.
"""

import argparse
import sys

import structlog
from sqlalchemy import create_engine, inspect

from app.config import settings
from app.db.migrate import (
    _sync_url,
    check_db_connection,
    current_revision,
    detect_database_state,
    migration_lock,
    pending_migrations,
)
from app.db.verify import verify_schema

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger(__name__)


def _print(text_: str = "") -> None:
    print(text_)


def run() -> int:
    parser = argparse.ArgumentParser(description="DevArchAI database schema check")
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run pending migrations before verifying the schema.",
    )
    args = parser.parse_args()

    url = _sync_url()

    _print("=" * 60)
    _print("DevArchAI database schema check")
    _print("=" * 60)
    _print(f"Database URL: {url}")
    _print(f"Migration on startup: {settings.DB_MIGRATE_ON_STARTUP}")
    _print()

    if not check_db_connection():
        _print("[ERROR] Could not connect to the database.")
        return 1

    state = detect_database_state(url)
    rev = current_revision()
    pending = pending_migrations()
    _print(f"Database state: {state}")
    _print(f"Current migration revision: {rev or '(none)'}")
    _print(f"Pending migrations: {pending or '(none)'}")

    if args.migrate:
        _print()
        _print("Running migrations...")
        from app.db.migrate import migrate_database

        try:
            with migration_lock():
                migrate_database()
            _print("Migrations complete.")
        except Exception as exc:
            _print(f"[ERROR] Migration failed: {exc}")
            return 1
        rev = current_revision()
        pending = pending_migrations()
        _print(f"Current migration revision: {rev or '(none)'}")
        _print(f"Pending migrations: {pending or '(none)'}")

    _print()
    _print("Verifying schema against models...")
    report = verify_schema(url, database_revision=rev)

    tables = set()
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    _print(f"Tables found in database: {len(tables)}")
    _print(f"Model tables verified: {report.tables_checked}")
    _print(f"Model columns verified: {report.columns_checked}")
    if report.warnings:
        _print()
        _print(f"Warnings ({len(report.warnings)}):")
        for issue in report.warnings:
            loc = f"{issue.table}.{issue.column}" if issue.column else issue.table
            _print(f"  [WARN] {issue.kind}: {loc} — {issue.detail}")
    _print()

    if report.ok:
        _print("SCHEMA VALIDATION: PASSED")
        return 0

    _print("SCHEMA VALIDATION: FAILED")
    _print()
    for issue in report.errors:
        loc = f"{issue.table}.{issue.column}" if issue.column else issue.table
        _print(f"  [ERROR] {issue.kind}: {loc} — {issue.detail}")
    return 1


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
