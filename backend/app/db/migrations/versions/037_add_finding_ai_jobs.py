"""Add finding_ai_jobs table for observable per-group AI recommendation state.

Revision ID: 037
Revises: 036
Create Date: 2026-08-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "037"
down_revision = "036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "finding_ai_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column(
            "representative_finding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("finding_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("technology", sa.String(100), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("source", sa.String(32), nullable=True),
        sa.Column("recommendation", postgresql.JSONB(), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("rag_context_version", sa.String(32), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scan_id", "cache_key", name="uq_finding_ai_jobs_scan_cache_key"),
    )
    op.create_index("ix_finding_ai_jobs_scan_id", "finding_ai_jobs", ["scan_id"])
    op.create_index("ix_finding_ai_jobs_cache_key", "finding_ai_jobs", ["cache_key"])
    op.create_index("ix_finding_ai_jobs_status", "finding_ai_jobs", ["status"])
    op.create_index("ix_finding_ai_jobs_rule_id", "finding_ai_jobs", ["rule_id"])
    op.create_index(
        "ix_finding_ai_jobs_representative_finding_id",
        "finding_ai_jobs",
        ["representative_finding_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_finding_ai_jobs_representative_finding_id", table_name="finding_ai_jobs")
    op.drop_index("ix_finding_ai_jobs_rule_id", table_name="finding_ai_jobs")
    op.drop_index("ix_finding_ai_jobs_status", table_name="finding_ai_jobs")
    op.drop_index("ix_finding_ai_jobs_cache_key", table_name="finding_ai_jobs")
    op.drop_index("ix_finding_ai_jobs_scan_id", table_name="finding_ai_jobs")
    op.drop_table("finding_ai_jobs")
