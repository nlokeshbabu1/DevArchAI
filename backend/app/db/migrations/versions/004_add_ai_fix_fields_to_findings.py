"""add_ai_fix_fields_to_findings

Revision ID: 004
Revises: 003
Create Date: 2026-03-22

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add AI fix generator fields to findings table."""
    op.add_column('findings', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('findings', sa.Column('fix_code', sa.Text(), nullable=True))
    op.add_column('findings', sa.Column('full_example', sa.Text(), nullable=True))
    op.add_column('findings', sa.Column('best_practices', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove AI fix generator fields from findings table."""
    op.drop_column('findings', 'best_practices')
    op.drop_column('findings', 'full_example')
    op.drop_column('findings', 'fix_code')
    op.drop_column('findings', 'summary')
