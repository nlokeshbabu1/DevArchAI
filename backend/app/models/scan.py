"""Scan model."""

import enum
import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ScanStatus(str, enum.Enum):
    """Scan status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanStage(str, enum.Enum):
    """Granular scan stage enumeration for real-time progress tracking."""

    CONNECTING = "connecting"
    CLONING = "cloning"
    TECHNOLOGY_DETECTION = "technology_detection"
    SCANNER_SELECTION = "scanner_selection"
    SCANNING = "scanning"
    NORMALIZATION = "normalization"
    DEDUPLICATION = "deduplication"
    AI_GENERATION = "ai_generation"
    REPORT_GENERATION = "report_generation"

    @classmethod
    def metadata(cls) -> dict["ScanStage", dict]:
        """Display metadata for each stage. Frontend renders these directly — no hardcoding."""
        return {
            cls.CONNECTING: {"label": "Connecting to repository", "icon": "git-branch", "order": 0},
            cls.CLONING: {"label": "Cloning repository", "icon": "download", "order": 1},
            cls.TECHNOLOGY_DETECTION: {"label": "Detecting technologies", "icon": "search", "order": 2},
            cls.SCANNER_SELECTION: {"label": "Selecting scanners", "icon": "layers", "order": 3},
            cls.SCANNING: {"label": "Running security analysis", "icon": "shield", "order": 4},
            cls.NORMALIZATION: {"label": "Normalizing findings", "icon": "filter", "order": 5},
            cls.DEDUPLICATION: {"label": "Deduplicating results", "icon": "check-circle", "order": 6},
            cls.AI_GENERATION: {"label": "Generating AI suggestions", "icon": "brain", "order": 7},
            cls.REPORT_GENERATION: {"label": "Generating report", "icon": "file-text", "order": 8},
        }

    @classmethod
    def ordered(cls) -> list["ScanStage"]:
        """Stages in execution order."""
        return sorted(cls.metadata().keys(), key=lambda s: cls.metadata()[s]["order"])


class AIScanStatus(str, enum.Enum):
    """AI suggestion generation status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


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
    current_stage = Column(
        SQLEnum(ScanStage, values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )
    error_message = Column(Text, nullable=True)
    celery_task_id = Column(String(255), nullable=True)  # Celery task ID for tracking
    ai_status = Column(String(32), default=AIScanStatus.PENDING.value, server_default=AIScanStatus.PENDING.value, nullable=False)
    ai_error_message = Column(Text, nullable=True)
    ai_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Results
    overall_score = Column(Float, nullable=True)
    security_score = Column(Float, nullable=True)
    scalability_score = Column(Float, nullable=True)
    reliability_score = Column(Float, nullable=True)
    cost_score = Column(Float, nullable=True)
    observability_score = Column(Float, nullable=True)
    detected_stack = Column(JSON, nullable=True)  # Detected technology stack

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
    scanner_executions = relationship(
        "ScannerExecutionRecord", back_populates="scan",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, status={self.status})>"
