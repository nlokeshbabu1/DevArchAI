"""add user_preferences, user_sessions, and api_keys tables

Revision ID: 014_add_settings_tables
Revises: 013_add_report_storage_columns
Create Date: 2026-05-14 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "014_add_settings_tables"
down_revision: Union[str, None] = "013_add_report_storage_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("user_preferences"):
        op.create_table(
            "user_preferences",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                unique=True,
                nullable=False,
            ),
            sa.Column("email_notifications", sa.Boolean(), default=True, nullable=False),
            sa.Column("critical_findings_alerts", sa.Boolean(), default=True, nullable=False),
            sa.Column("weekly_reports", sa.Boolean(), default=False, nullable=False),
            sa.Column("product_updates", sa.Boolean(), default=False, nullable=False),
            sa.Column("scan_completion_alerts", sa.Boolean(), default=True, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _has_table("user_sessions"):
        op.create_table(
            "user_sessions",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("token_prefix", sa.String(20), nullable=True),
            sa.Column("device_info", sa.String(500), nullable=True),
            sa.Column("ip_address", sa.String(50), nullable=True),
            sa.Column("is_current", sa.Boolean(), default=False, nullable=False),
            sa.Column(
                "last_active_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _has_table("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("name", sa.String(255), nullable=True),
            sa.Column("prefix", sa.String(20), nullable=False),
            sa.Column("key_hash", sa.String(255), nullable=False),
            sa.Column("key_preview", sa.String(10), nullable=False),
            sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    if _has_table("api_keys"):
        op.drop_table("api_keys")
    if _has_table("user_sessions"):
        op.drop_table("user_sessions")
    if _has_table("user_preferences"):
        op.drop_table("user_preferences")
