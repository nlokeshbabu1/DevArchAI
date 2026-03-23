"""Add email encryption fields to users table

Revision ID: 005
Revises: 004
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add encrypted email fields to users table."""
    # Add new columns for encrypted email
    op.add_column('users', sa.Column('email_encrypted', sa.String(512), nullable=True))
    op.add_column('users', sa.Column('email_hash', sa.String(255), nullable=True))
    
    # Create index on email_hash for fast lookups
    op.create_index('ix_users_email_hash', 'users', ['email_hash'], unique=True)
    
    # Note: Existing users will need to be migrated manually or via script
    # For new installations, these fields will be populated on user creation


def downgrade() -> None:
    """Remove encrypted email fields."""
    op.drop_index('ix_users_email_hash', table_name='users')
    op.drop_column('users', 'email_hash')
    op.drop_column('users', 'email_encrypted')
