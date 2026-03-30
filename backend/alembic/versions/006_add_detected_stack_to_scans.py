"""add detected_stack to scans table

Revision ID: 006
Revises: 005
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add detected_stack column to scans table
    op.add_column('scans', sa.Column('detected_stack', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove detected_stack column from scans table
    op.drop_column('scans', 'detected_stack')
