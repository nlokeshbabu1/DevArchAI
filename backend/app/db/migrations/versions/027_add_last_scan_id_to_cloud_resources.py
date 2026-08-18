"""Add last_scan_id to cloud_resources for scan-based soft-deletion.

Instead of using NOT IN clauses with large resource ID lists, each scan
gets a unique scan_id. Resources are soft-deleted by comparing last_scan_id
against the current scan_id. This scales to millions of resources.

Revision ID: 027
Revises: 026
Create Date: 2025-02-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "027"
down_revision: str | None = "026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cloud_resources",
        sa.Column(
            "last_scan_id",
            sa.String(64),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_cloud_resources_last_scan_id",
        "cloud_resources",
        ["last_scan_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cloud_resources_last_scan_id", table_name="cloud_resources")
    op.drop_column("cloud_resources", "last_scan_id")
