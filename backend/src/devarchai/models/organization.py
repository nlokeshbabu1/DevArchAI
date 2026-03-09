"""Organization model for multi-tenancy."""

from sqlalchemy import Column, String, Boolean, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
import enum

from devarchai.db.base import Base
from devarchai.models.mixins import TimestampMixin


class PlanType(str, enum.Enum):
    """Subscription plan types."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Organization(Base, TimestampMixin):
    """
    Organization model for multi-tenancy.

    All resources (repositories, scans, findings, reports)
    belong to an organization for data isolation.
    """

    __tablename__ = "organizations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Basic info
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Subscription & billing
    plan = Column(SQLEnum(PlanType), default=PlanType.FREE, nullable=False)
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    # Usage tracking
    scans_this_month = Column(String(255), nullable=False, default=0)
    last_reset_date = Column(String(255), nullable=True)

    # Settings
    settings = Column(String(255), nullable=True)  # JSON string
    features = Column(String(255), nullable=True)  # JSON string

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    members = relationship(
        "devarchai.models.organization.OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    projects = relationship(
        "Project",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    repositories = relationship(
        "Repository",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    scans = relationship(
        "Scan",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    findings = relationship(
        "Finding",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    reports = relationship(
        "Report",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    subscriptions = relationship(
        "Subscription",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, slug={self.slug})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "plan": self.plan.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
