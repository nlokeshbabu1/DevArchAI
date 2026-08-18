"""Cloud AI Recommendation model — stores AI-generated recommendations."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class CloudAIRecommendation(Base):
    """AI-generated recommendation enriched with knowledge context.

    Each recommendation is tied to a scan session and contains the full
    structured output: executive summary, root cause, business/security/cost
    impact, official AWS best practice, documentation references, Terraform/CLI
    fixes, compliance mapping, and confidence scoring.
    """

    __tablename__ = "cloud_ai_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "scan_session_id", "service", "resource_id", "region", "rule_id",
            name="uq_cloud_ai_recs_conn_session_svc_res_region_rule",
        ),
        {"comment": "AI-generated recommendations enriched with knowledge context"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cloud_scan_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Source finding reference
    finding_id = Column(String(256), nullable=True, index=True)
    rule_id = Column(String(100), nullable=False, server_default=text("''"))
    service = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(512), nullable=False, server_default=text("''"))
    region = Column(String(30), nullable=False)

    # Recommendation content
    executive_summary = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=False)
    business_impact = Column(Text, nullable=False, server_default=text("''"))
    security_impact = Column(Text, nullable=False, server_default=text("''"))
    cost_impact = Column(Text, nullable=False, server_default=text("''"))

    # AWS official guidance
    official_best_practice = Column(Text, nullable=False, server_default=text("''"))
    documentation_references = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    documentation_retrieved_at = Column(DateTime(timezone=True), nullable=True)

    # Fixes
    cloudformation_fix = Column(Text, nullable=True)
    terraform_fix = Column(Text, nullable=True)
    aws_cli_fix = Column(Text, nullable=True)
    console_steps = Column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))

    # Compliance
    compliance_mapping = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    # Scoring
    confidence_score = Column(Float, nullable=False, server_default=text("0"))
    estimated_risk_reduction = Column(Float, nullable=True, server_default=text("0"))
    estimated_monthly_savings = Column(Float, nullable=True, server_default=text("0"))
    severity = Column(String(20), nullable=False, server_default=text("'medium'"))

    # Knowledge context metadata
    knowledge_sources_used = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    llm_provider = Column(String(50), nullable=True)

    status = Column(String(20), nullable=False, server_default=text("'active'"))
    last_scan_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    connection = relationship("CloudConnection")
