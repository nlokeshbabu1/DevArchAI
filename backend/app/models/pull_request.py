"""Pull Request model for tracking automated GitHub PRs."""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class PRStatus(str, enum.Enum):
    """Pull Request status enumeration."""

    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"
    DRAFT = "draft"


class PullRequest(Base):
    """Pull Request model for tracking automated GitHub PRs."""

    __tablename__ = "pull_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    scan_id = Column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # GitHub PR information
    github_pr_number = Column(Integer, nullable=False)
    github_pr_url = Column(String(500), nullable=False, unique=True)
    branch_name = Column(String(255), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Status and metadata
    status = Column(SQLEnum(PRStatus), default=PRStatus.OPEN, nullable=False)
    findings_fixed = Column(JSON, nullable=True)  # Array of finding IDs that were fixed
    score_before = Column(Float, nullable=True)
    score_after = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    merged_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    scan = relationship("Scan", backref="pull_requests")
    user = relationship("User", backref="pull_requests")

    def __repr__(self) -> str:
        return f"<PullRequest(id={self.id}, pr_number={self.github_pr_number}, status={self.status})>"
