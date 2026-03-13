"""Finding model."""

import enum
import uuid

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


class Severity(str, enum.Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, enum.Enum):
    """Analysis categories."""

    SECURITY = "security"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    COST = "cost"
    OBSERVABILITY = "observability"


class Finding(Base):
    """Finding model for storing detected issues."""

    __tablename__ = "findings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    scan_id = Column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)

    # Rule info
    rule_id = Column(String(50), nullable=False, index=True)
    rule_name = Column(String(255), nullable=False)

    # Classification
    severity = Column(SQLEnum(Severity), nullable=False, index=True)
    category = Column(SQLEnum(Category), nullable=False, index=True)

    # Details
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    risk = Column(Text, nullable=True)
    impact = Column(Text, nullable=True)
    fix_example = Column(Text, nullable=True)

    # Location
    file_path = Column(String(500), nullable=True)
    line_number = Column(Integer, nullable=True)
    resource_name = Column(String(255), nullable=True)

    # AI enhancements
    ai_explanation = Column(Text, nullable=True)
    impact_analysis = Column(Text, nullable=True)

    # Metadata
    confidence_score = Column(Float, default=1.0, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    scan = relationship("Scan", back_populates="findings")

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, rule_id={self.rule_id}, severity={self.severity})>"
