"""Report model for analysis reports."""

import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Text, Boolean, JSON as SAJSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from devarchai.db.base import Base
from devarchai.models.mixins import TimestampMixin, OrganizationMixin


class Report(Base, TimestampMixin, OrganizationMixin):
    """
    Report model for storing analysis reports.

    Each report is generated after a scan completes and contains
    the full analysis results including scores and findings summary.
    """

    __tablename__ = "reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    scan_id = Column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Repository info (denormalized)
    repository_name = Column(String(255), nullable=False)
    repository_url = Column(String(500), nullable=False)
    commit_hash = Column(String(40), nullable=True)
    branch = Column(String(100), nullable=True)
    
    # Scores
    overall_score = Column(Float, nullable=False)
    category_scores = Column(SAJSON, nullable=True)  # {"security": 80, "scalability": 65, ...}
    
    # AI-generated content
    executive_summary = Column(Text, nullable=True)
    risk_analysis = Column(Text, nullable=True)
    prioritized_recommendations = Column(SAJSON, nullable=True)  # Array of strings
    
    # Findings summary
    total_findings = Column(String(255), nullable=False, default=0)
    critical_count = Column(String(255), nullable=False, default=0)
    high_count = Column(String(255), nullable=False, default=0)
    medium_count = Column(String(255), nullable=False, default=0)
    low_count = Column(String(255), nullable=False, default=0)
    info_count = Column(String(255), nullable=False, default=0)
    
    # Files analyzed
    files_analyzed = Column(SAJSON, nullable=True)  # Array of file paths
    
    # Storage
    storage_path = Column(String(500), nullable=True)  # S3 path if stored
    storage_provider = Column(String(50), default="local", nullable=True)  # local, s3
    
    # Sharing
    is_public = Column(Boolean, default=False, nullable=False)
    share_token = Column(String(255), unique=True, nullable=True, index=True)
    share_expires_at = Column(String(255), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="reports")
    scan = relationship("Scan", back_populates="report")

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, scan_id={self.scan_id})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "scan_id": str(self.scan_id),
            "repository_name": self.repository_name,
            "repository_url": self.repository_url,
            "commit_hash": self.commit_hash,
            "branch": self.branch,
            "overall_score": self.overall_score,
            "category_scores": self.category_scores,
            "executive_summary": self.executive_summary,
            "risk_analysis": self.risk_analysis,
            "prioritized_recommendations": self.prioritized_recommendations,
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "files_analyzed": self.files_analyzed,
            "is_public": self.is_public,
            "organization_id": str(self.organization_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
