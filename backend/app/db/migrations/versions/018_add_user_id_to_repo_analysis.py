"""add user_id to repo_analysis for tenant isolation

Revision ID: 018
Revises: 017
Create Date: 2026-06-26

"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('repo_analysis', sa.Column('user_id', UUID(as_uuid=True), nullable=True, index=True))
    op.create_foreign_key(
        'fk_repo_analysis_user_id',
        'repo_analysis', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('fk_repo_analysis_user_id', 'repo_analysis', type_='foreignkey')
    op.drop_column('repo_analysis', 'user_id')
