"""Add documentation_url column to findings table

Revision ID: 003
Revises: 002
Create Date: 2026-03-22

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add documentation_url column to findings table."""
    op.add_column(
        'findings',
        sa.Column('documentation_url', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Remove documentation_url column from findings table."""
    op.drop_column('findings', 'documentation_url')
