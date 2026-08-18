"""Add ai_generated column to findings table

Revision ID: 002
Revises: 001
Create Date: 2026-03-22

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ai_generated column to findings table."""
    op.add_column(
        'findings',
        sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    """Remove ai_generated column from findings table."""
    op.drop_column('findings', 'ai_generated')
