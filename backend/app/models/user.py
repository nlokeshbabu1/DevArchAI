"""User model."""

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserRole(str, enum.Enum):
    """User role enumeration."""

    USER = "user"
    ADMIN = "admin"
    ENTERPRISE = "enterprise"


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Email encryption: store encrypted email, with hash for lookups
    email_encrypted = Column(String(512), nullable=False)  # Encrypted email
    email_hash = Column(String(255), unique=True, index=True, nullable=False)  # SHA256 hash for lookups
    
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Profile
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # GitHub OAuth
    github_id = Column(String(100), unique=True, index=True, nullable=True)
    github_login = Column(String(100), index=True, nullable=True)  # GitHub username for webhook lookups
    github_access_token = Column(String(500), nullable=True)  # Store OAuth token for API access

    # GitLab OAuth
    gitlab_id = Column(String(100), unique=True, index=True, nullable=True)
    gitlab_username = Column(String(100), nullable=True)
    gitlab_access_token = Column(String(500), nullable=True)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)

    # Subscription plan
    subscription_plan = Column(String(50), default="free", nullable=False)  # free, plus, pro, enterprise
    subscription_status = Column(String(50), default="inactive", nullable=False)
    payment_provider = Column(String(50), nullable=True)

    # Billing fields (added for payment system)
    country = Column(String(2), default="US", nullable=True)  # ISO 3166-1 alpha-2
    selected_country = Column(String(2), nullable=True)  # User-selected country preference
    selected_gateway = Column(String(20), nullable=True)  # User-selected payment gateway override
    billing_email = Column(String(255), nullable=True)
    tax_id = Column(String(100), nullable=True)  # GST, VAT, etc.

    # Current organization
    current_org_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    # API key for enterprise users
    api_key = Column(String(255), unique=True, index=True, nullable=True)
    api_key_prefix = Column(String(8), nullable=True)

    # MFA fields
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)
    backup_codes = Column(String(1000), nullable=True)  # JSON array of hashed backup codes

    # Account lockout
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # SSO-ready fields
    sso_provider = Column(String(50), nullable=True)  # okta, azure_ad, google_workspace, saml
    sso_id = Column(String(255), nullable=True)  # External identity provider user ID

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    memberships = relationship(
        "app.models.organization.OrganizationMember",
        foreign_keys="app.models.organization.OrganizationMember.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    repositories = relationship("Repository", back_populates="user", cascade="all, delete-orphan")
    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", foreign_keys="Subscription.organization_id",
                                primaryjoin="User.current_org_id==Subscription.organization_id",
                                uselist=False, viewonly=True)
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email_hash={self.email_hash})>"
