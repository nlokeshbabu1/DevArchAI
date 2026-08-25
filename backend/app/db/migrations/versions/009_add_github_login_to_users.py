"""add github_login field to users table

Revision ID: 009_add_github_login_to_users
Revises: 008_add_github_installations_table
Create Date: 2026-04-15 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add github_login column to users table."""
    op.add_column("users", sa.Column("github_login", sa.String(length=100), nullable=True))
    op.create_index("ix_users_github_login", "users", ["github_login"], unique=False)


def downgrade() -> None:
    """Remove github_login column from users table."""
    op.drop_index("ix_users_github_login", table_name="users")
    op.drop_column("users", "github_login")
