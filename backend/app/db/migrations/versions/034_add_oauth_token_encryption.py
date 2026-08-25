"""Add encrypted OAuth token columns to users table

Revision ID: 034
Revises: 033
Create Date: 2026-08-17

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add encrypted OAuth token columns to users table."""
    # Add encrypted columns for GitHub OAuth tokens
    op.add_column('users', sa.Column('github_access_token_encrypted', sa.Text(), nullable=True))
    
    # Add encrypted columns for GitLab OAuth tokens
    op.add_column('users', sa.Column('gitlab_access_token_encrypted', sa.Text(), nullable=True))
    
    # Add encryption version column for future key rotation support
    op.add_column('users', sa.Column('token_encryption_version', sa.Integer(), nullable=True, server_default='1'))


def downgrade() -> None:
    """Remove encrypted OAuth token columns."""
    op.drop_column('users', 'token_encryption_version')
    op.drop_column('users', 'gitlab_access_token_encrypted')
    op.drop_column('users', 'github_access_token_encrypted')
