"""Add last_scan_id, status, unique constraints for UPSERT tracking.

Adds to findings/costs/compliance/AI recommendations the same
scan-tracking columns that resources have (last_scan_id, lifecycle status)
so all entity types can use UPSERT + soft-delete instead of DELETE ALL + INSERT.

Revision ID: 029
Revises: 028
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def _deduplicate(table: str, keys: list[str]) -> None:
    """Remove duplicate rows keeping only the one with the highest id.

    Uses PostgreSQL ctid-based dedup — keeps the first row per unique key group.
    This is a one-time migration step; the unique constraint prevents future dupes.
    """
    key_cols = ", ".join(keys)
    op.execute(f"""
        DELETE FROM {table}
        WHERE ctid NOT IN (
            SELECT min(ctid)
            FROM {table}
            GROUP BY {key_cols}
        )
    """)


def upgrade() -> None:
    # ── Cloud Findings ──
    # Backfill NULL resource_id / rule_id before adding NOT NULL
    op.execute(
        "UPDATE cloud_findings SET resource_id = '' WHERE resource_id IS NULL"
    )
    op.execute(
        "UPDATE cloud_findings SET rule_id = '' WHERE rule_id IS NULL"
    )
    op.alter_column("cloud_findings", "resource_id",
                    existing_type=sa.String(512),
                    nullable=False,
                    server_default=sa.text("''"))
    op.alter_column("cloud_findings", "rule_id",
                    existing_type=sa.String(100),
                    nullable=False,
                    server_default=sa.text("''"))
    op.add_column("cloud_findings",
                  sa.Column("last_scan_id", sa.String(64), nullable=True))
    op.create_index("ix_cloud_findings_last_scan_id", "cloud_findings", ["last_scan_id"])
    _deduplicate("cloud_findings", [
        "connection_id", "provider", "service", "region", "resource_id", "rule_id",
    ])
    op.create_unique_constraint(
        "uq_cloud_findings_conn_prov_svc_region_res_rule",
        "cloud_findings",
        ["connection_id", "provider", "service", "region", "resource_id", "rule_id"],
    )

    # ── Cloud Cost Recommendations ──
    op.execute(
        "UPDATE cloud_cost_recommendations SET resource_id = '' WHERE resource_id IS NULL"
    )
    op.alter_column("cloud_cost_recommendations", "resource_id",
                    existing_type=sa.String(512),
                    nullable=False,
                    server_default=sa.text("''"))
    op.add_column("cloud_cost_recommendations",
                  sa.Column("last_scan_id", sa.String(64), nullable=True))
    op.create_index("ix_cloud_cost_recommendations_last_scan_id",
                    "cloud_cost_recommendations", ["last_scan_id"])
    _deduplicate("cloud_cost_recommendations", [
        "connection_id", "provider", "service", "region", "resource_id", "recommendation_type",
    ])
    op.create_unique_constraint(
        "uq_cloud_costs_conn_prov_svc_region_res_type",
        "cloud_cost_recommendations",
        ["connection_id", "provider", "service", "region", "resource_id", "recommendation_type"],
    )

    # ── Cloud Compliance Results ──
    op.add_column("cloud_compliance_results",
                  sa.Column("status", sa.String(20), nullable=False,
                            server_default=sa.text("'active'")))
    op.add_column("cloud_compliance_results",
                  sa.Column("last_scan_id", sa.String(64), nullable=True))
    op.create_index("ix_cloud_compliance_results_last_scan_id",
                    "cloud_compliance_results", ["last_scan_id"])
    _deduplicate("cloud_compliance_results", [
        "connection_id", "provider", "framework",
    ])
    op.create_unique_constraint(
        "uq_cloud_compliance_conn_prov_framework",
        "cloud_compliance_results",
        ["connection_id", "provider", "framework"],
    )

    # ── Cloud AI Recommendations ──
    op.execute(
        "UPDATE cloud_ai_recommendations SET resource_id = '' WHERE resource_id IS NULL"
    )
    op.execute(
        "UPDATE cloud_ai_recommendations SET rule_id = '' WHERE rule_id IS NULL"
    )
    op.alter_column("cloud_ai_recommendations", "resource_id",
                    existing_type=sa.String(512),
                    nullable=False,
                    server_default=sa.text("''"))
    op.alter_column("cloud_ai_recommendations", "rule_id",
                    existing_type=sa.String(100),
                    nullable=False,
                    server_default=sa.text("''"))
    op.add_column("cloud_ai_recommendations",
                  sa.Column("status", sa.String(20), nullable=False,
                            server_default=sa.text("'active'")))
    op.add_column("cloud_ai_recommendations",
                  sa.Column("last_scan_id", sa.String(64), nullable=True))
    op.create_index("ix_cloud_ai_recommendations_last_scan_id",
                    "cloud_ai_recommendations", ["last_scan_id"])
    _deduplicate("cloud_ai_recommendations", [
        "connection_id", "scan_session_id", "service", "resource_id", "region", "rule_id",
    ])
    op.create_unique_constraint(
        "uq_cloud_ai_recs_conn_session_svc_res_region_rule",
        "cloud_ai_recommendations",
        ["connection_id", "scan_session_id", "service", "resource_id", "region", "rule_id"],
    )


def downgrade() -> None:
    # Cloud Findings
    op.drop_constraint("uq_cloud_findings_conn_prov_svc_region_res_rule",
                       "cloud_findings")
    op.drop_index("ix_cloud_findings_last_scan_id", table_name="cloud_findings")
    op.drop_column("cloud_findings", "last_scan_id")
    op.alter_column("cloud_findings", "rule_id",
                    existing_type=sa.String(100),
                    nullable=True,
                    server_default=None)
    op.alter_column("cloud_findings", "resource_id",
                    existing_type=sa.String(512),
                    nullable=True,
                    server_default=None)

    # Cloud Cost Recommendations
    op.drop_constraint("uq_cloud_costs_conn_prov_svc_region_res_type",
                       "cloud_cost_recommendations")
    op.drop_index("ix_cloud_cost_recommendations_last_scan_id",
                  table_name="cloud_cost_recommendations")
    op.drop_column("cloud_cost_recommendations", "last_scan_id")
    op.alter_column("cloud_cost_recommendations", "resource_id",
                    existing_type=sa.String(512),
                    nullable=True,
                    server_default=None)

    # Cloud Compliance Results
    op.drop_constraint("uq_cloud_compliance_conn_prov_framework",
                       "cloud_compliance_results")
    op.drop_index("ix_cloud_compliance_results_last_scan_id",
                  table_name="cloud_compliance_results")
    op.drop_column("cloud_compliance_results", "last_scan_id")
    op.drop_column("cloud_compliance_results", "status")

    # Cloud AI Recommendations
    op.drop_constraint("uq_cloud_ai_recs_conn_session_svc_res_region_rule",
                       "cloud_ai_recommendations")
    op.drop_index("ix_cloud_ai_recommendations_last_scan_id",
                  table_name="cloud_ai_recommendations")
    op.drop_column("cloud_ai_recommendations", "last_scan_id")
    op.drop_column("cloud_ai_recommendations", "status")
    op.alter_column("cloud_ai_recommendations", "rule_id",
                    existing_type=sa.String(100),
                    nullable=True,
                    server_default=None)
    op.alter_column("cloud_ai_recommendations", "resource_id",
                    existing_type=sa.String(512),
                    nullable=True,
                    server_default=None)
