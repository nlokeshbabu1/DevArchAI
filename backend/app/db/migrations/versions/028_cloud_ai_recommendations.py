"""Add cloud_ai_recommendations table.

Revision ID: 028
Revises: 027
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cloud_ai_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cloud_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scan_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cloud_scan_sessions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("finding_id", sa.String(256), nullable=True),
        sa.Column("rule_id", sa.String(100), nullable=True),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(512), nullable=True),
        sa.Column("region", sa.String(30), nullable=False),
        # Recommendation content
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("business_impact", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("security_impact", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("cost_impact", sa.Text(), nullable=False, server_default=sa.text("''")),
        # AWS official guidance
        sa.Column("official_best_practice", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "documentation_references",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("documentation_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        # Fixes
        sa.Column("terraform_fix", sa.Text(), nullable=True),
        sa.Column("aws_cli_fix", sa.Text(), nullable=True),
        sa.Column(
            "console_steps",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # Compliance
        sa.Column(
            "compliance_mapping",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Scoring
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "estimated_risk_reduction", sa.Float(), nullable=True, server_default=sa.text("0")
        ),
        sa.Column(
            "estimated_monthly_savings", sa.Float(), nullable=True, server_default=sa.text("0")
        ),
        sa.Column("severity", sa.String(20), nullable=False, server_default=sa.text("'medium'")),
        # Knowledge metadata
        sa.Column(
            "knowledge_sources_used",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_cloud_ai_recommendations_connection_id",
        "cloud_ai_recommendations",
        ["connection_id"],
    )
    op.create_index(
        "ix_cloud_ai_recommendations_scan_session_id",
        "cloud_ai_recommendations",
        ["scan_session_id"],
    )
    op.create_index(
        "ix_cloud_ai_recommendations_finding_id",
        "cloud_ai_recommendations",
        ["finding_id"],
    )
    op.create_index(
        "ix_cloud_ai_recommendations_service",
        "cloud_ai_recommendations",
        ["service"],
    )


def downgrade() -> None:
    op.drop_table("cloud_ai_recommendations")
