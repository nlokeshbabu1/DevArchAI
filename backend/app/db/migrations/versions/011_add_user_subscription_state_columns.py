"""add user subscription state columns

Revision ID: 011_add_user_subscription_state_columns
Revises: 010_add_billing_country_gateway_columns
Create Date: 2026-04-19 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "011_add_user_subscription_state_columns"
down_revision: str | None = "010_add_billing_country_gateway_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("users", "subscription_status"):
        op.add_column(
            "users",
            sa.Column("subscription_status", sa.String(length=50), nullable=False, server_default="inactive"),
        )

    if not _has_column("users", "payment_provider"):
        op.add_column("users", sa.Column("payment_provider", sa.String(length=50), nullable=True))


def downgrade() -> None:
    if _has_column("users", "payment_provider"):
        op.drop_column("users", "payment_provider")

    if _has_column("users", "subscription_status"):
        op.drop_column("users", "subscription_status")
