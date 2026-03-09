"""Finding model for analysis results."""

import uuid
import enum
from sqlalchemy import Column, String, Float, ForeignKey, Text, Enum as SQLEnum, Integer, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from devarchai.db.base import Base
from devarchai.models.mixins import TimestampMixin, OrganizationMixin


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


class FindingStatus(str, enum.Enum):
    """Finding status for tracking remediation."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"


class Finding(Base, TimestampMixin, OrganizationMixin):
    """
    Finding model for storing analysis results.

    Each finding represents a specific issue or recommendation
    identified during repository analysis.
    """

    __tablename__ = "findings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    scan_id = Column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Rule info
    rule_id = Column(String(100), nullable=False, index=True)
    rule_name = Column(String(255), nullable=False)
    
    # Classification
    severity = Column(SQLEnum(Severity), nullable=False, index=True)
    category = Column(SQLEnum(Category), nullable=False, index=True)
    
    # Description
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)
    
    # Location
    file_path = Column(String(500), nullable=True, index=True)
    line_number = Column(Integer, nullable=True)
    resource_name = Column(String(255), nullable=True)
    resource_type = Column(String(100), nullable=True)
    
    # AI analysis
    ai_explanation = Column(Text, nullable=True)
    impact_analysis = Column(Text, nullable=True)
    
    # Confidence
    confidence_score = Column(Float, default=1.0, nullable=False)
    
    # Status tracking
    status = Column(SQLEnum(FindingStatus), default=FindingStatus.OPEN, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="findings")
    scan = relationship("Scan", back_populates="findings")
    resolver = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, rule_id={self.rule_id}, severity={self.severity})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "category": self.category.value,
            "description": self.description,
            "recommendation": self.recommendation,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "resource_name": self.resource_name,
            "resource_type": self.resource_type,
            "ai_explanation": self.ai_explanation,
            "impact_analysis": self.impact_analysis,
            "confidence_score": self.confidence_score,
            "status": self.status.value,
            "scan_id": str(self.scan_id),
            "organization_id": str(self.organization_id),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
