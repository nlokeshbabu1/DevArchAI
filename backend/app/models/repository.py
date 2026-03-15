"""Repository model."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Repository(Base):
    """Repository model for tracking analyzed GitHub repositories."""

    __tablename__ = "repositories"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Repository info
    name = Column(String(255), nullable=False)  # e.g., "org/repo"
    full_name = Column(String(500), nullable=True)
    url = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # GitHub metadata
    default_branch = Column(String(100), default="main", nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)
    github_id = Column(String(100), unique=True, nullable=True)

    # Analysis status
    is_active = Column(Boolean, default=True, nullable=False)
    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("app.models.user.User", back_populates="repositories")
    scans = relationship("Scan", back_populates="repository", cascade="all, delete-orphan", order_by="Scan.created_at.desc()")

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, name={self.name})>"
