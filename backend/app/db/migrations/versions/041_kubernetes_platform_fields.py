"""Add Kubernetes platform fields and cluster AI jobs table."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("kubernetes_connections", sa.Column("cluster_name", sa.String(length=200), nullable=True))
    op.add_column("kubernetes_connections", sa.Column("kubernetes_version", sa.String(length=32), nullable=True))
    op.add_column("kubernetes_connections", sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("kubernetes_connections", sa.Column("health_status", sa.String(length=32), nullable=True))
    op.add_column("kubernetes_connections", sa.Column("node_count", sa.Integer(), nullable=True))
    op.add_column("kubernetes_connections", sa.Column("pod_count", sa.Integer(), nullable=True))
    op.add_column("kubernetes_connections", sa.Column("service_count", sa.Integer(), nullable=True))

    op.create_table(
        "cluster_ai_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("kubernetes_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("analysis_type", sa.String(length=32), nullable=False, server_default="cluster"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cluster_ai_jobs_connection_id", "cluster_ai_jobs", ["connection_id"])
    op.create_index("ix_cluster_ai_jobs_user_id", "cluster_ai_jobs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_cluster_ai_jobs_user_id", table_name="cluster_ai_jobs")
    op.drop_index("ix_cluster_ai_jobs_connection_id", table_name="cluster_ai_jobs")
    op.drop_table("cluster_ai_jobs")
    op.drop_column("kubernetes_connections", "service_count")
    op.drop_column("kubernetes_connections", "pod_count")
    op.drop_column("kubernetes_connections", "node_count")
    op.drop_column("kubernetes_connections", "health_status")
    op.drop_column("kubernetes_connections", "last_verified_at")
    op.drop_column("kubernetes_connections", "kubernetes_version")
    op.drop_column("kubernetes_connections", "cluster_name")
