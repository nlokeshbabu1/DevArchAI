"""Add ScanStage enum and current_stage column to scans table.

Adds granular stage tracking for real-time scan progress.
The backend is the single source of truth for scan state.

Revision ID: 021
Revises: 020
Create Date: 2026-07-13 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision = "021"
down_revision = "020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create the ScanStage enum type
    scanstage_enum = sa.Enum(
        "connecting",
        "cloning",
        "technology_detection",
        "scanner_selection",
        "scanning",
        "normalization",
        "deduplication",
        "ai_generation",
        "report_generation",
        name="scanstage",
    )
    scanstage_enum.create(op.get_bind(), checkfirst=True)

    # Add current_stage column to scans table
    op.add_column(
        "scans",
        sa.Column("current_stage", scanstage_enum, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scans", "current_stage")
    sa.Enum(name="scanstage").drop(op.get_bind(), checkfirst=True)
