"""Add Kubernetes resource count columns and AI job metrics (prod-safe)."""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def _safe_add_column(table: str, column: sa.Column) -> None:
    if not _column_exists(table, column.name):
        op.add_column(table, column)


def upgrade() -> None:
    _safe_add_column("kubernetes_connections", sa.Column("namespace_count", sa.Integer(), nullable=True))
    _safe_add_column("kubernetes_connections", sa.Column("deployment_count", sa.Integer(), nullable=True))
    _safe_add_column("kubernetes_connections", sa.Column("ingress_count", sa.Integer(), nullable=True))

    if "cluster_ai_jobs" in inspect(op.get_bind()).get_table_names():
        _safe_add_column("cluster_ai_jobs", sa.Column("finding_count", sa.Integer(), nullable=True))
        _safe_add_column("cluster_ai_jobs", sa.Column("recommendation_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    if _column_exists("cluster_ai_jobs", "recommendation_count"):
        op.drop_column("cluster_ai_jobs", "recommendation_count")
    if _column_exists("cluster_ai_jobs", "finding_count"):
        op.drop_column("cluster_ai_jobs", "finding_count")
    if _column_exists("kubernetes_connections", "ingress_count"):
        op.drop_column("kubernetes_connections", "ingress_count")
    if _column_exists("kubernetes_connections", "deployment_count"):
        op.drop_column("kubernetes_connections", "deployment_count")
    if _column_exists("kubernetes_connections", "namespace_count"):
        op.drop_column("kubernetes_connections", "namespace_count")
