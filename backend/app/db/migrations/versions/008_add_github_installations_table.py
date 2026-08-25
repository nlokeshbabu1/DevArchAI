"""add github installations table

Revision ID: 008_add_github_installations_table
Revises: 007_add_pull_request_table
Create Date: 2026-04-15 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create github_installations mapping table."""
    op.create_table(
        "github_installations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repo_full_name", sa.String(length=255), nullable=False),
        sa.Column("installation_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_github_installations_id", "github_installations", ["id"], unique=False)
    op.create_index("ix_github_installations_user_id", "github_installations", ["user_id"], unique=False)
    op.create_index("ix_github_installations_repo_full_name", "github_installations", ["repo_full_name"], unique=False)
    op.create_index("ix_github_installations_installation_id", "github_installations", ["installation_id"], unique=False)


def downgrade() -> None:
    """Drop github_installations mapping table."""
    op.drop_index("ix_github_installations_installation_id", table_name="github_installations")
    op.drop_index("ix_github_installations_repo_full_name", table_name="github_installations")
    op.drop_index("ix_github_installations_user_id", table_name="github_installations")
    op.drop_index("ix_github_installations_id", table_name="github_installations")
    op.drop_table("github_installations")

