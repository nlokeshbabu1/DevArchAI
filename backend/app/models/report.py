"""Report model."""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid

from app.db.base import Base


class Report(Base):
    """Report model for storing complete analysis reports."""

    __tablename__ = "reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    scan_id = Column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Report content
    repository_name = Column(String(255), nullable=False)
    repository_url = Column(String(500), nullable=False)
    commit_hash = Column(String(40), nullable=True)

    # Scores
    overall_score = Column(Float, nullable=False)
    category_scores = Column(JSON, nullable=True)  # {"security": 85.0, "scalability": 70.0, ...}

    # AI-generated content
    executive_summary = Column(Text, nullable=True)
    risk_analysis = Column(Text, nullable=True)
    prioritized_recommendations = Column(JSON, nullable=True)  # List of strings

    # Summary statistics
    total_findings = Column(Integer, default=0, nullable=False)
    critical_count = Column(Integer, default=0, nullable=False)
    high_count = Column(Integer, default=0, nullable=False)
    medium_count = Column(Integer, default=0, nullable=False)
    low_count = Column(Integer, default=0, nullable=False)
    info_count = Column(Integer, default=0, nullable=False)

    # Files analyzed
    files_analyzed = Column(JSON, nullable=True)  # List of file paths

    # Storage
    s3_key = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    scan = relationship("Scan", back_populates="report")

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, scan_id={self.scan_id})>"
