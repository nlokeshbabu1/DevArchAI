"""Add scanner_execution_records table for per-scanner execution tracking.

Stores ScannerExecutionRecord for each scanner adapter that runs during
a scan, including status, duration, findings count, and error info.

Revision ID: 020
Revises: 019
Create Date: 2026-07-02 14:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision = "020"
down_revision = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scanner_execution_records",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("scan_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("scanner_name", sa.String(100), nullable=False),
        sa.Column("scanner_id", sa.String(50), nullable=False),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="DISCOVERED"),
        sa.Column("applicable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("execution_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("files_scanned", sa.Integer(), nullable=True),
        sa.Column("rules_executed", sa.Integer(), nullable=True),
        sa.Column("findings_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("skipped_reason", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("scanner_execution_records")
