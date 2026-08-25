"""enterprise auth: mfa fields, enhanced sessions, enterprise audit logs

Revision ID: 016_enterprise_auth
Revises: 015_add_aws_integration_tables
Create Date: 2026-05-31 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "016"
down_revision = "022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply enterprise auth schema changes."""

    # ---- Users: MFA fields ----
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("mfa_secret", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("backup_codes", sa.String(length=1000), nullable=True))

    # ---- UserSessions: enhanced fields ----
    op.add_column("user_sessions", sa.Column("refresh_token_hash", sa.String(length=255), nullable=True))
    op.add_column("user_sessions", sa.Column("device_name", sa.String(length=255), nullable=True))
    op.add_column("user_sessions", sa.Column("browser", sa.String(length=100), nullable=True))
    op.add_column("user_sessions", sa.Column("user_agent", sa.String(length=500), nullable=True))
    op.add_column("user_sessions", sa.Column("location", sa.String(length=255), nullable=True))
    op.add_column("user_sessions", sa.Column("revoked", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("user_sessions", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    # Drop old columns that have been replaced
    op.drop_column("user_sessions", "token_prefix")
    op.drop_column("user_sessions", "device_info")

    # ---- Enterprise audit logs table ----
    op.create_table(
        "enterprise_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_enterprise_audit_logs_actor_id", "enterprise_audit_logs", ["actor_id"])
    op.create_index("ix_enterprise_audit_logs_org_id", "enterprise_audit_logs", ["org_id"])
    op.create_index("ix_enterprise_audit_logs_action", "enterprise_audit_logs", ["action"])
    op.create_index("ix_enterprise_audit_logs_timestamp", "enterprise_audit_logs", ["timestamp"])


def downgrade() -> None:
    """Revert enterprise auth schema changes."""
    op.drop_column("users", "backup_codes")
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "mfa_enabled")

    op.add_column("user_sessions", sa.Column("device_info", sa.String(length=500), nullable=True))
    op.add_column("user_sessions", sa.Column("token_prefix", sa.String(length=20), nullable=True))
    op.drop_column("user_sessions", "expires_at")
    op.drop_column("user_sessions", "revoked")
    op.drop_column("user_sessions", "location")
    op.drop_column("user_sessions", "user_agent")
    op.drop_column("user_sessions", "browser")
    op.drop_column("user_sessions", "device_name")
    op.drop_column("user_sessions", "refresh_token_hash")

    op.drop_index("ix_enterprise_audit_logs_timestamp", table_name="enterprise_audit_logs")
    op.drop_index("ix_enterprise_audit_logs_action", table_name="enterprise_audit_logs")
    op.drop_index("ix_enterprise_audit_logs_org_id", table_name="enterprise_audit_logs")
    op.drop_index("ix_enterprise_audit_logs_actor_id", table_name="enterprise_audit_logs")
    op.drop_table("enterprise_audit_logs")
