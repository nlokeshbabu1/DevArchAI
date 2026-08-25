"""add ai status tracking columns to scans

Revision ID: 012_add_ai_status_to_scans
Revises: 011_add_user_subscription_state_columns
Create Date: 2026-05-02 13:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "012"
down_revision = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("scans", "ai_status"):
        op.add_column(
            "scans",
            sa.Column("ai_status", sa.String(length=32), nullable=False, server_default="pending"),
        )

    if not _has_column("scans", "ai_error_message"):
        op.add_column("scans", sa.Column("ai_error_message", sa.Text(), nullable=True))

    if not _has_column("scans", "ai_completed_at"):
        op.add_column("scans", sa.Column("ai_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    if _has_column("scans", "ai_completed_at"):
        op.drop_column("scans", "ai_completed_at")

    if _has_column("scans", "ai_error_message"):
        op.drop_column("scans", "ai_error_message")

    if _has_column("scans", "ai_status"):
        op.drop_column("scans", "ai_status")
