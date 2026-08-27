"""Per-scan AI recommendation job tracking (independent of scan completion)."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class FindingAIJobStatus(str, enum.Enum):
    """Independent AI recommendation lifecycle for a finding group."""

    NOT_STARTED = "not_started"
    QUEUED = "queued"
    CHECKING_CACHE = "checking_cache"
    CACHE_HIT = "cache_hit"
    RAG_RETRIEVING = "rag_retrieving"
    MCP_RETRIEVING = "mcp_retrieving"
    GENERATING = "generating"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


# User-facing source labels (no sensitive implementation detail).
SOURCE_DISPLAY = {
    "cache": "Internal DevSecOps Knowledge Base (cached)",
    "rag": "Internal DevSecOps Knowledge Base",
    "mcp": "Live Documentation",
    "rag_mcp": "Internal RAG + Live Documentation",
    "llm": "AI-generated",
    "fallback": "Static remediation guidance",
}


class FindingAIJob(Base):
    """Tracks one AI recommendation job for a deduplicated finding group within a scan."""

    __tablename__ = "finding_ai_jobs"
    __table_args__ = (
        UniqueConstraint("scan_id", "cache_key", name="uq_finding_ai_jobs_scan_cache_key"),
        {"comment": "Per-scan AI recommendation job state (parallel, observable)"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    scan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cache_key = Column(String(64), nullable=False, index=True)
    representative_finding_id = Column(
        UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_ids = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, server_default=text("'[]'"))
    rule_id = Column(String(50), nullable=False, index=True)
    technology = Column(String(100), nullable=True)

    status = Column(
        String(32),
        nullable=False,
        server_default=FindingAIJobStatus.QUEUED.value,
        index=True,
    )
    source = Column(String(32), nullable=True)
    recommendation = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    model = Column(String(64), nullable=True)
    prompt_version = Column(String(32), nullable=True)
    rag_context_version = Column(String(32), nullable=True)

    celery_task_id = Column(String(255), nullable=True)
    retry_count = Column(Integer, nullable=False, server_default=text("0"))
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    scan = relationship("Scan", backref="ai_jobs")
    representative_finding = relationship("Finding", foreign_keys=[representative_finding_id])

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            FindingAIJobStatus.COMPLETED.value,
            FindingAIJobStatus.FAILED.value,
        )

    def __repr__(self) -> str:
        return f"<FindingAIJob(scan_id={self.scan_id}, rule_id={self.rule_id}, status={self.status})>"
