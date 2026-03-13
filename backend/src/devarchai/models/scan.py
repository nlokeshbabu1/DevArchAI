"""Scan model for tracking analysis jobs."""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from devarchai.db.base import Base
from devarchai.models.mixins import OrganizationMixin, TimestampMixin


class ScanStatus(str, enum.Enum):
    """Scan status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Scan(Base, TimestampMixin, OrganizationMixin):
    """
    Scan model for tracking repository analysis jobs.

    Each scan represents a single analysis run against a repository.
    """

    __tablename__ = "scans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign keys
    repository_id = Column(PG_UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True, index=True)
    creator_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Scan configuration
    branch = Column(String(100), default="main", nullable=False)
    commit_hash = Column(String(40), nullable=True)
    repository_url = Column(String(500), nullable=False)  # Denormalized for quick access

    # Status tracking
    status = Column(SQLEnum(ScanStatus), default=ScanStatus.PENDING, nullable=False, index=True)
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    status_message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Results
    overall_score = Column(Float, nullable=True)
    security_score = Column(Float, nullable=True)
    scalability_score = Column(Float, nullable=True)
    reliability_score = Column(Float, nullable=True)
    cost_score = Column(Float, nullable=True)
    observability_score = Column(Float, nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    analysis_duration_seconds = Column(Float, nullable=True)

    # Celery task tracking
    celery_task_id = Column(String(255), nullable=True, index=True)

    # Relationships
    organization = relationship("Organization", back_populates="scans")
    repository = relationship("Repository", back_populates="scans")
    creator = relationship("User", foreign_keys=[creator_id], back_populates="scans")
    findings = relationship(
        "Finding",
        back_populates="scan",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    report = relationship(
        "Report",
        back_populates="scan",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, status={self.status})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "status": self.status.value,
            "progress": self.progress,
            "status_message": self.status_message,
            "error_message": self.error_message,
            "overall_score": self.overall_score,
            "security_score": self.security_score,
            "scalability_score": self.scalability_score,
            "reliability_score": self.reliability_score,
            "cost_score": self.cost_score,
            "observability_score": self.observability_score,
            "branch": self.branch,
            "commit_hash": self.commit_hash,
            "repository_url": self.repository_url,
            "repository_id": str(self.repository_id) if self.repository_id else None,
            "organization_id": str(self.organization_id),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "analysis_duration_seconds": self.analysis_duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
