"""add github_access_token to users

Revision ID: add_github_access_token
Revises: 
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_github_access_token'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add github_access_token column to users table."""
    op.add_column('users', sa.Column('github_access_token', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Remove github_access_token column from users table."""
    op.drop_column('users', 'github_access_token')
