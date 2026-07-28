"""Create ai_recommendations table — production single source of truth.

This replaces the legacy cloud_ai_recommendations table with a clean,
focused schema backing the Overview dashboard, AI Recommendations tab,
PDF reports, email digests, and future integrations.

Every finding in a scan produces at least one row here. Dashboard summary
counts are computed from this table directly, never from findings.

Revision ID: 031
Revises: 030
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_recommendations",
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cloud_connections.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cloud_scan_sessions.id", ondelete="SET NULL"),
                  nullable=True, index=True),
        sa.Column("provider", sa.String(20), nullable=False, server_default=sa.text("'aws'")),
        sa.Column("service", sa.String(50), nullable=False, index=True),
        sa.Column("resource_id", sa.String(512), nullable=False, server_default=sa.text("''")),
        sa.Column("resource_name", sa.String(256), nullable=False, server_default=sa.text("''")),
        sa.Column("category", sa.String(30), nullable=False, index=True),
        sa.Column("severity", sa.String(20), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("technical_explanation", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("business_impact", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("estimated_monthly_savings", sa.Float, nullable=True, server_default=sa.text("0")),
        sa.Column("estimated_risk_reduction", sa.Float, nullable=True, server_default=sa.text("0")),
        sa.Column("aws_cli_fix", sa.Text, nullable=True),
        sa.Column("terraform_fix", sa.Text, nullable=True),
        sa.Column("cloudformation_fix", sa.Text, nullable=True),
        sa.Column("console_steps", postgresql.JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("official_documentation_url", sa.String(1024), nullable=True),
        sa.Column("recommendation_source", sa.String(20), nullable=False,
                  server_default=sa.text("'ai_generated'")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'open'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        comment="AI-generated cloud recommendations — production single source of truth",
    )


def downgrade() -> None:
    op.drop_table("ai_recommendations")
