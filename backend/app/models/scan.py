"""Scan model."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid

from app.db.base import Base


class ScanStatus(str, enum.Enum):
    """Scan status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Scan(Base):
    """Scan model for tracking repository analysis jobs."""

    __tablename__ = "scans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    repository_id = Column(PG_UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True, index=True)

    # Scan configuration
    repository_url = Column(String(500), nullable=False)
    branch = Column(String(100), default="main", nullable=False)
    commit_hash = Column(String(40), nullable=True)

    # Status tracking
    status = Column(SQLEnum(ScanStatus), default=ScanStatus.PENDING, nullable=False)
    progress = Column(Integer, default=0, nullable=False)  # 0-100
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

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("app.models.user.User", back_populates="scans")
    repository = relationship("Repository", back_populates="scans")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="scan", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, status={self.status})>"
