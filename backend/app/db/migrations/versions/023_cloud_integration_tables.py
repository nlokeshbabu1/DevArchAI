"""Cloud integration tables — multi-cloud support.

Revision ID: 023_cloud_integration_tables
Revises: 022
Create Date: 2025-01-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "023"
down_revision = "021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _has_table("cloud_connections"):
        return

    op.create_table(
        "cloud_connections",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("provider", sa.String(20), nullable=False, index=True),
        sa.Column("account_id", sa.String(128), nullable=False),
        sa.Column(
            "connection_name", sa.String(100), nullable=False, server_default=""
        ),
        sa.Column("role_arn", sa.Text(), nullable=False),
        sa.Column("external_id_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "regions",
            JSONB(),
            nullable=False,
            server_default='["us-east-1"]',
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="connected"
        ),
        sa.Column(
            "scan_status", sa.String(20), nullable=False, server_default="idle"
        ),
        sa.Column("scan_progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resource_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finding_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("security_score", sa.Float(), nullable=True),
        sa.Column(
            "estimated_monthly_cost",
            sa.Float(),
            nullable=True,
            server_default="0",
        ),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "cloud_scan_sessions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "connection_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cloud_connections.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="queued"
        ),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "current_stage", sa.String(100), nullable=False, server_default=""
        ),
        sa.Column(
            "stages_completed",
            JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "stages_total", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "resources_scanned", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "findings_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "cloud_resources",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "connection_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cloud_connections.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("service", sa.String(50), nullable=False, index=True),
        sa.Column("resource_id", sa.String(512), nullable=False),
        sa.Column(
            "resource_name", sa.String(512), nullable=False, server_default=""
        ),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("region", sa.String(30), nullable=False, index=True),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="active"
        ),
        sa.Column("configuration", JSONB(), nullable=True),
        sa.Column("tags", JSONB(), nullable=True),
        sa.Column("cost_monthly", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_cloud_resources_conn_service",
        "cloud_resources",
        ["connection_id", "service"],
    )

    op.create_table(
        "cloud_findings",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "connection_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cloud_connections.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("service", sa.String(50), nullable=False, index=True),
        sa.Column("category", sa.String(30), nullable=False, index=True),
        sa.Column("severity", sa.String(20), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column(
            "description", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column("resource_id", sa.String(512), nullable=True),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("region", sa.String(30), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=True),
        sa.Column("compliance_frameworks", JSONB(), nullable=True),
        sa.Column("remediation", sa.Text(), nullable=True),
        sa.Column("remediation_url", sa.String(1000), nullable=True),
        sa.Column("evidence", JSONB(), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="open"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_cloud_findings_conn_severity",
        "cloud_findings",
        ["connection_id", "severity"],
    )

    op.create_table(
        "cloud_cost_recommendations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "connection_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cloud_connections.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column(
            "description", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column("resource_id", sa.String(512), nullable=True),
        sa.Column("region", sa.String(30), nullable=False),
        sa.Column(
            "monthly_savings",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "current_cost", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "priority", sa.String(20), nullable=False, server_default="medium"
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("recommendation_type", sa.String(100), nullable=False),
        sa.Column(
            "estimated_impact",
            sa.String(200),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="open"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "cloud_compliance_results",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "connection_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cloud_connections.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("framework", sa.String(50), nullable=False),
        sa.Column(
            "total_controls", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "not_applicable", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "last_checked",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_cloud_compliance_conn_framework",
        "cloud_compliance_results",
        ["connection_id", "framework"],
    )


def downgrade() -> None:
    op.drop_table("cloud_compliance_results")
    op.drop_table("cloud_cost_recommendations")
    op.drop_table("cloud_findings")
    op.drop_table("cloud_resources")
    op.drop_table("cloud_scan_sessions")
    op.drop_table("cloud_connections")
