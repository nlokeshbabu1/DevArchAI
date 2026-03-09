"""User model with multi-tenancy support."""

import uuid
import enum
import sqlalchemy
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from devarchai.db.base import Base
from devarchai.models.mixins import TimestampMixin


class UserRole(str, enum.Enum):
    """User role enumeration."""

    USER = "user"
    ADMIN = "admin"
    ENTERPRISE = "enterprise"


class User(Base, TimestampMixin):
    """
    User model for authentication and authorization.

    Users can be members of multiple organizations with different roles.
    """

    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    
    # Current organization context
    current_org_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    
    # API key for enterprise users
    api_key = Column(String(255), unique=True, index=True, nullable=True)
    api_key_prefix = Column(String(16), nullable=True)
    
    # Last login tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    memberships = relationship(
        "devarchai.models.organization.OrganizationMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    organizations = relationship(
        "Organization",
        secondary="organization_members",
        viewonly=True,
    )
    repositories = relationship(
        "Repository",
        back_populates="creator",
        foreign_keys="Repository.creator_id",
    )
    scans = relationship(
        "Scan",
        back_populates="creator",
        foreign_keys="Scan.creator_id",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"

    def to_dict(self) -> dict:
        """Convert to dictionary (excludes sensitive fields)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "role": self.role.value,
            "current_org_id": str(self.current_org_id) if self.current_org_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


class MembershipRole(str, enum.Enum):
    """Organization membership roles."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class OrganizationMember(Base, TimestampMixin):
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
    
    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("devarchai.models.user.User", back_populates="memberships")
    inviter = relationship("devarchai.models.user.User", foreign_keys=[invited_by], remote_side="devarchai.models.user.User.id")

    __table_args__ = (
        # Unique constraint: one membership per user per organization
        sqlalchemy.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember(org={self.organization_id}, user={self.user_id}, role={self.role})>"
