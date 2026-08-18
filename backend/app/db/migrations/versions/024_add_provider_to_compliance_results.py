"""Fix missing/mismatched columns on cloud tables.

Revision ID: 024
Revises: 023_cloud_integration_tables
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "024"
down_revision: str | None = "023_cloud_integration_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # ── cloud_compliance_results: add provider column ──
    if not _has_column("cloud_compliance_results", "provider"):
        op.add_column(
            "cloud_compliance_results",
            sa.Column("provider", sa.String(20), nullable=False, server_default="'aws'"),
        )

    # ── cloud_scan_sessions: rename error_message → error ──
    if _has_column("cloud_scan_sessions", "error_message") and not _has_column("cloud_scan_sessions", "error"):
        op.alter_column("cloud_scan_sessions", "error_message", new_column_name="error")

    # ── cloud_scan_sessions: rename completed_at → finished_at ──
    if _has_column("cloud_scan_sessions", "completed_at") and not _has_column("cloud_scan_sessions", "finished_at"):
        op.alter_column("cloud_scan_sessions", "completed_at", new_column_name="finished_at")

    # ── cloud_scan_sessions: change progress from Integer → Float ──
    if _has_column("cloud_scan_sessions", "progress"):
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        col = next(c for c in inspector.get_columns("cloud_scan_sessions") if c["name"] == "progress")
        col_type_name = type(col["type"]).__name__
        if col_type_name == "Integer":
            op.alter_column(
                "cloud_scan_sessions",
                "progress",
                type_=sa.Float(),
                server_default="0",
            )


def downgrade() -> None:
    if _has_column("cloud_scan_sessions", "progress"):
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        col = next(c for c in inspector.get_columns("cloud_scan_sessions") if c["name"] == "progress")
        col_type_name = type(col["type"]).__name__
        if col_type_name == "Float":
            op.alter_column(
                "cloud_scan_sessions",
                "progress",
                type_=sa.Integer(),
                server_default="0",
            )

    if _has_column("cloud_scan_sessions", "finished_at") and not _has_column("cloud_scan_sessions", "completed_at"):
        op.alter_column("cloud_scan_sessions", "finished_at", new_column_name="completed_at")

    if _has_column("cloud_scan_sessions", "error") and not _has_column("cloud_scan_sessions", "error_message"):
        op.alter_column("cloud_scan_sessions", "error", new_column_name="error_message")

    if _has_column("cloud_compliance_results", "provider"):
        op.drop_column("cloud_compliance_results", "provider")
