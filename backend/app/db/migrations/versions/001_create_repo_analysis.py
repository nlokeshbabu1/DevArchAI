"""create repo_analysis table

Revision ID: 001
Revises:
Create Date: 2026-03-05

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create repo_analysis table
    op.create_table(
        'repo_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repo_url', sa.String(length=500), nullable=False),
        sa.Column('repo_owner', sa.String(length=100), nullable=False),
        sa.Column('repo_name', sa.String(length=100), nullable=False),
        sa.Column('repo_full_name', sa.String(length=255), nullable=False),
        sa.Column('detected_stack', sa.JSON(), nullable=True),
        sa.Column('has_docker', sa.Boolean(), nullable=False, default=False),
        sa.Column('has_terraform', sa.Boolean(), nullable=False, default=False),
        sa.Column('has_kubernetes', sa.Boolean(), nullable=False, default=False),
        sa.Column('has_cicd', sa.Boolean(), nullable=False, default=False),
        sa.Column('has_monitoring', sa.Boolean(), nullable=False, default=False),
        sa.Column('has_helm', sa.Boolean(), nullable=False, default=False),
        sa.Column('has_ansible', sa.Boolean(), nullable=False, default=False),
        sa.Column('cicd_type', sa.String(length=50), nullable=True),
        sa.Column('devops_score', sa.Float(), nullable=True),
        sa.Column('files_analyzed', sa.Integer(), nullable=False, default=0),
        sa.Column('analysis_version', sa.String(length=20), nullable=False, default='1.0'),
        sa.Column('status', sa.String(length=20), nullable=False, default='completed'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_repo_analysis_id', 'repo_analysis', ['id'], unique=False)
    op.create_index('ix_repo_analysis_repo_url', 'repo_analysis', ['repo_url'], unique=False)
    op.create_index('ix_repo_analysis_created_at', 'repo_analysis', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_repo_analysis_created_at', table_name='repo_analysis')
    op.drop_index('ix_repo_analysis_repo_url', table_name='repo_analysis')
    op.drop_index('ix_repo_analysis_id', table_name='repo_analysis')
    op.drop_table('repo_analysis')
