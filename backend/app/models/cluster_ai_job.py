"""Cluster AI analysis job tracking."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ClusterAIJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COLLECTING = "collecting"
    CHECKING_CACHE = "checking_cache"
    RAG_RETRIEVING = "rag_retrieving"
    MCP_RETRIEVING = "mcp_retrieving"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ClusterAIJob(Base):
    """Background AI analysis job for a Kubernetes cluster."""

    __tablename__ = "cluster_ai_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("kubernetes_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(32), nullable=False, default=ClusterAIJobStatus.QUEUED.value)
    analysis_type = Column(String(32), nullable=False, default="cluster")
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    finding_count = Column(Integer, nullable=True)
    recommendation_count = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    connection = relationship("KubernetesConnection", backref="ai_jobs")
