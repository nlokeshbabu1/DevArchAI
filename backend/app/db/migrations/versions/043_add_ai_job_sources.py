"""Add strict per-source provenance to finding_ai_jobs.

Stores the normalized list of RAG / MCP sources that actually informed each
recommendation, plus a documentation-status classification, so every finding
can be attributed to the exact evidence used.

Revision ID: 043
Revises: 042
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "043"
down_revision = "042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "finding_ai_jobs",
        sa.Column("documentation_status", sa.String(32), nullable=True),
    )
    op.add_column(
        "finding_ai_jobs",
        sa.Column(
            "sources",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("finding_ai_jobs", "sources")
    op.drop_column("finding_ai_jobs", "documentation_status")
