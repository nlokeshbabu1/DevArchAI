"""Project model for grouping repositories."""

import uuid

from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from devarchai.db.base import Base
from devarchai.models.mixins import OrganizationMixin, TimestampMixin


class Project(Base, TimestampMixin, OrganizationMixin):
    """
    Project model for grouping related repositories.

    Projects help organize repositories within an organization.
    """

    __tablename__ = "projects"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Basic info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    repositories = relationship(
        "Repository",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "organization_id": str(self.organization_id),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
