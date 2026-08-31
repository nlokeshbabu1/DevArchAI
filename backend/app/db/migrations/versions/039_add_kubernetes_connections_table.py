"""Add kubernetes_connections table.

Additive migration. Creates the table that persists Kubernetes cluster
connections, both generic kubeconfig-based connections and managed EKS
clusters discovered via an AWS connection.

Kubeconfig payloads are stored encrypted and are never returned to the client.

Revision ID: 039
Revises: 038
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kubernetes_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False, server_default="kubernetes"),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="generic"),
        sa.Column("kubeconfig_encrypted", sa.Text(), nullable=True),
        sa.Column("context_name", sa.String(length=200), nullable=True),
        sa.Column("cluster_endpoint", sa.String(length=500), nullable=True),
        sa.Column("aws_account_id", sa.String(length=128), nullable=True),
        sa.Column("aws_region", sa.String(length=64), nullable=True),
        sa.Column("eks_cluster_name", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="connected"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_kubernetes_connections_id", "kubernetes_connections", ["id"], unique=False)
    op.create_index("ix_kubernetes_connections_user_id", "kubernetes_connections", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_kubernetes_connections_user_id", table_name="kubernetes_connections")
    op.drop_index("ix_kubernetes_connections_id", table_name="kubernetes_connections")
    op.drop_table("kubernetes_connections")
