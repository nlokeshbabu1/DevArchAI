"""Create scan_ai_recommendations table (AI recommendation cache, Phase 2).

Additive migration. Creates the persisted (L2) layer of the layered AI
recommendation cache for repository scan findings.

- ``scan_ai_recommendations`` — one row per deterministic, versioned
  recommendation cache key; scan-independent so identical findings share a
  single cached recommendation across scans.

No existing tables are modified.

Revision ID: 033
Revises: 032
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_ai_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("finding_fingerprint", sa.String(64), nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("technology", sa.String(100), nullable=True),
        sa.Column("rag_version", sa.String(32), nullable=False, server_default=""),
        sa.Column("mcp_version", sa.String(32), nullable=False, server_default=""),
        sa.Column("prompt_version", sa.String(32), nullable=False, server_default=""),
        sa.Column("model_version", sa.String(64), nullable=False, server_default=""),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="llm"),
        sa.Column("ai_generated", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "origin_finding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ttl_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Cached AI recommendations for repository scan findings",
    )
    op.create_index("ix_scan_ai_recommendations_cache_key", "scan_ai_recommendations", ["cache_key"], unique=True)
    op.create_index("ix_scan_ai_recommendations_finding_fingerprint", "scan_ai_recommendations", ["finding_fingerprint"])
    op.create_index("ix_scan_ai_recommendations_rule_id", "scan_ai_recommendations", ["rule_id"])
    op.create_index("ix_scan_ai_recommendations_technology", "scan_ai_recommendations", ["technology"])
    op.create_index("ix_scan_ai_recommendations_origin_finding_id", "scan_ai_recommendations", ["origin_finding_id"])
    op.create_index("ix_scan_ai_recommendations_expires_at", "scan_ai_recommendations", ["expires_at"])


def downgrade() -> None:
    op.drop_table("scan_ai_recommendations")
