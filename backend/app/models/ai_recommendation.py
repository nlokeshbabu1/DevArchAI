"""AI Recommendation model — production-grade single source of truth."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AIRecommendation(Base):
    """AI-generated recommendation — single source of truth for the entire system.

    This table backs the Overview dashboard summary counts, the AI Recommendations
    tab, PDF reports, email digests, and future Jira/Slack integrations.
    Every finding in a scan produces at least one row here.
    """

    __tablename__ = "ai_recommendations"
    __table_args__ = (
        {"comment": "AI-generated cloud recommendations — production single source of truth"},
    )

    recommendation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cloud_scan_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider = Column(String(20), nullable=False, server_default=text("'aws'"))
    service = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(512), nullable=False, server_default=text("''"))
    resource_name = Column(String(256), nullable=False, server_default=text("''"))
    category = Column(String(30), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=False)
    technical_explanation = Column(Text, nullable=False, server_default=text("''"))
    business_impact = Column(Text, nullable=False, server_default=text("''"))
    estimated_monthly_savings = Column(Float, nullable=True, server_default=text("0"))
    estimated_risk_reduction = Column(Float, nullable=True, server_default=text("0"))
    aws_cli_fix = Column(Text, nullable=True)
    terraform_fix = Column(Text, nullable=True)
    cloudformation_fix = Column(Text, nullable=True)
    console_steps = Column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    official_documentation_url = Column(String(1024), nullable=True)
    recommendation_source = Column(String(20), nullable=False, server_default=text("'ai_generated'"))
    status = Column(String(20), nullable=False, server_default=text("'open'"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=_utcnow,
        nullable=False,
    )

    connection = relationship("CloudConnection", back_populates="ai_recommendations")
