"""add pull request table

Revision ID: 007_add_pull_request_table
Revises: 006_add_detected_stack_to_scans
Create Date: 2026-04-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007_add_pull_request_table'
down_revision: Union[str, None] = '006_add_detected_stack_to_scans'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pull_requests table for tracking automated GitHub PRs."""
    
    # Create PR status enum
    op.execute("CREATE TYPE prstatus AS ENUM ('open', 'merged', 'closed', 'draft')")
    
    # Create pull_requests table
    op.create_table(
        'pull_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scans.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # GitHub PR information
        sa.Column('github_pr_number', sa.Integer(), nullable=False),
        sa.Column('github_pr_url', sa.String(500), nullable=False, unique=True),
        sa.Column('branch_name', sa.String(255), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Status and metadata
        sa.Column('status', postgresql.ENUM('open', 'merged', 'closed', 'draft', name='prstatus', create_type=False), nullable=False, server_default='open'),
        sa.Column('findings_fixed', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('score_before', sa.Float(), nullable=True),
        sa.Column('score_after', sa.Float(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('merged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_pull_requests_scan_id', 'pull_requests', ['scan_id'])
    op.create_index('ix_pull_requests_user_id', 'pull_requests', ['user_id'])
    op.create_index('ix_pull_requests_status', 'pull_requests', ['status'])
    op.create_index('ix_pull_requests_created_at', 'pull_requests', ['created_at'])


def downgrade() -> None:
    """Remove pull_requests table."""
    op.drop_table('pull_requests')
    op.execute("DROP TYPE IF EXISTS prstatus")
