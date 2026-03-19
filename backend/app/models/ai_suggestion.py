"""AI Suggestion model for actionable fixes."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class SuggestionStatus(str, enum.Enum):
    """Status of AI suggestion."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    IGNORED = "ignored"


class FixType(str, enum.Enum):
    """Type of fix."""

    TERRAFORM = "terraform"
    DOCKERFILE = "dockerfile"
    KUBERNETES = "kubernetes"
    CI_CD = "ci_cd"
    GENERAL = "general"


class AISuggestion(Base):
    """AI Suggestion model for storing actionable fixes."""

    __tablename__ = "ai_suggestions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    finding_id = Column(PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id = Column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic info
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Classification
    severity = Column(String(50), nullable=False, index=True)  # critical, high, medium, low, info
    confidence = Column(Float, default=0.9, nullable=False)  # 0.0 to 1.0
    category = Column(String(50), nullable=False, index=True)  # security, reliability, cost, etc.
    fix_type = Column(SQLEnum(FixType), nullable=False, default=FixType.GENERAL)
    
    # Location
    file_path = Column(String(500), nullable=False)
    line_number = Column(Integer, nullable=True)
    
    # Fix code
    fix_code = Column(Text, nullable=True)  # The actual code fix
    auto_fix_available = Column(Boolean, default=False, nullable=False)
    
    # Status tracking
    status = Column(SQLEnum(SuggestionStatus), default=SuggestionStatus.OPEN, nullable=False, index=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    pr_url = Column(String(500), nullable=True)  # GitHub PR URL if created
    pr_number = Column(Integer, nullable=True)

    # Additional data (renamed from 'metadata' to avoid SQLAlchemy reservation)
    additional_data = Column(Text, nullable=True)  # JSON string for additional data

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships - only to Finding (scan relationship removed as it's redundant)
    finding = relationship("Finding", back_populates="ai_suggestions")

    def __repr__(self) -> str:
        return f"<AISuggestion(id={self.id}, title={self.title}, status={self.status})>"
