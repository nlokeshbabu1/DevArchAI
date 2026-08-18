"""Add resource_type column to cloud_cost_recommendations.

Revision ID: 025
Revises: 024
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "025"
down_revision: str | None = "024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("cloud_cost_recommendations", "resource_type"):
        op.add_column(
            "cloud_cost_recommendations",
            sa.Column("resource_type", sa.String(100), nullable=True),
        )


def downgrade() -> None:
    if _has_column("cloud_cost_recommendations", "resource_type"):
        op.drop_column("cloud_cost_recommendations", "resource_type")
