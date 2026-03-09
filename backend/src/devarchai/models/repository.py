"""Repository model."""

import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from devarchai.db.base import Base
from devarchai.models.mixins import TimestampMixin, OrganizationMixin


class Repository(Base, TimestampMixin, OrganizationMixin):
    """
    Repository model for tracking source code repositories.

    Supports GitHub, GitLab, and Bitbucket repositories.
    """

    __tablename__ = "repositories"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Source control info
    provider = Column(String(50), default="github", nullable=False)  # github, gitlab, bitbucket
    provider_repo_id = Column(String(255), nullable=True)  # External ID from provider
    name = Column(String(255), nullable=False, index=True)
    full_name = Column(String(500), nullable=True)  # e.g., "org/repo"
    url = Column(String(500), nullable=False)
    clone_url = Column(String(500), nullable=True)
    
    # Branch info
    default_branch = Column(String(100), default="main", nullable=False)
    current_branch = Column(String(100), nullable=True)
    
    # Git info
    current_commit = Column(String(40), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_private = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String(50), default="idle", nullable=True)  # idle, syncing, error
    
    # Foreign keys
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    creator_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="repositories")
    project = relationship("Project", back_populates="repositories")
    creator = relationship("User", foreign_keys=[creator_id], back_populates="repositories")
    scans = relationship(
        "Scan",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, name={self.name})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "full_name": self.full_name,
            "url": self.url,
            "provider": self.provider,
            "default_branch": self.default_branch,
            "current_branch": self.current_branch,
            "current_commit": self.current_commit,
            "is_active": self.is_active,
            "is_private": self.is_private,
            "organization_id": str(self.organization_id),
            "project_id": str(self.project_id) if self.project_id else None,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "sync_status": self.sync_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
