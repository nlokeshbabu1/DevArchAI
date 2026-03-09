"""Organization model for multi-tenancy."""

import uuid
import enum
import sqlalchemy
from sqlalchemy import Column, String, Boolean, Enum as SQLEnum, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base import Base


class PlanType(str, enum.Enum):
    """Subscription plan types."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Organization(Base):
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
    scans_this_month = Column(Integer, nullable=False, default=0)
    last_reset_date = Column(DateTime(timezone=True), nullable=True)

    # Settings
    settings = Column(Text, nullable=True)  # JSON string
    features = Column(Text, nullable=True)  # JSON string

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    members = relationship(
        "app.models.organization.OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, slug={self.slug})>"

class MembershipRole(str, enum.Enum):
    """Organization membership roles."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class OrganizationMember(Base):
    """
    Organization member model (many-to-many relationship).

    Links users to organizations with specific roles.
    """

    __tablename__ = "organization_members"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    organization_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    role = Column(SQLEnum(MembershipRole), default=MembershipRole.MEMBER, nullable=False)
    invited_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invited_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("app.models.user.User", foreign_keys=[user_id], back_populates="memberships")
    inviter = relationship("app.models.user.User", foreign_keys=[invited_by], remote_side="app.models.user.User.id")

    __table_args__ = (
        # Unique constraint: one membership per user per organization
        sqlalchemy.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember(org={self.organization_id}, user={self.user_id}, role={self.role})>"
