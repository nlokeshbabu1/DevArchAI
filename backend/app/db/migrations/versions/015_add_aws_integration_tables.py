"""add AWS integration tables

Revision ID: 015_add_aws_integration_tables
Revises: 014_add_settings_tables
Create Date: 2026-05-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "015_add_aws_integration_tables"
down_revision: str | None = "014_add_settings_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("aws_accounts"):
        op.create_table(
            "aws_accounts",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("account_id", sa.String(32), nullable=False, index=True),
            sa.Column("account_alias", sa.String(255), nullable=True),
            sa.Column("connection_type", sa.String(32), server_default="access_key", nullable=False),
            sa.Column("access_key_id_encrypted", sa.Text(), nullable=True),
            sa.Column("secret_access_key_encrypted", sa.Text(), nullable=True),
            sa.Column("role_arn_encrypted", sa.Text(), nullable=True),
            sa.Column("external_id_encrypted", sa.Text(), nullable=True),
            sa.Column("default_region", sa.String(32), server_default="us-east-1", nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("scan_status", sa.String(32), server_default="pending", nullable=False),
            sa.Column("scan_progress", sa.Integer(), server_default="0", nullable=False),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not _has_table("aws_inventory"):
        op.create_table(
            "aws_inventory",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("resource_type", sa.String(64), nullable=False, index=True),
            sa.Column("resource_id", sa.String(512), nullable=False, index=True),
            sa.Column("name", sa.String(512), nullable=True),
            sa.Column("region", sa.String(64), nullable=True),
            sa.Column("metadata_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
            sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not _has_table("aws_findings"):
        op.create_table(
            "aws_findings",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("category", sa.String(64), nullable=False, index=True),
            sa.Column("severity", sa.String(16), nullable=False, index=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("resource_type", sa.String(64), nullable=True),
            sa.Column("resource_id", sa.String(512), nullable=True),
            sa.Column("region", sa.String(64), nullable=True),
            sa.Column("recommendation", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
            sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not _has_table("aws_cost_recommendations"):
        op.create_table(
            "aws_cost_recommendations",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("recommendation_type", sa.String(64), nullable=False, index=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("resource_type", sa.String(64), nullable=True),
            sa.Column("resource_id", sa.String(512), nullable=True),
            sa.Column("region", sa.String(64), nullable=True),
            sa.Column("estimated_monthly_savings", sa.Float(), server_default="0", nullable=False),
            sa.Column("metadata_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
            sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    for table_name in ("aws_cost_recommendations", "aws_findings", "aws_inventory", "aws_accounts"):
        if _has_table(table_name):
            op.drop_table(table_name)
