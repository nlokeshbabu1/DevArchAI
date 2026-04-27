"""add billing country and gateway columns to users

Revision ID: 010_add_billing_country_gateway_columns
Revises: 009_add_github_login_to_users
Create Date: 2026-04-19 17:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "010_add_billing_country_gateway_columns"
down_revision: Union[str, None] = "009_add_github_login_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Add missing billing routing columns to users table."""
    if not _has_column("users", "selected_country"):
        op.add_column("users", sa.Column("selected_country", sa.String(length=2), nullable=True))

    if not _has_column("users", "selected_gateway"):
        op.add_column("users", sa.Column("selected_gateway", sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Remove billing routing columns from users table."""
    if _has_column("users", "selected_gateway"):
        op.drop_column("users", "selected_gateway")

    if _has_column("users", "selected_country"):
        op.drop_column("users", "selected_country")
