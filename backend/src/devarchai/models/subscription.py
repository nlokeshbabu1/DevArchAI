"""Subscription model for billing."""

import uuid
import enum
from sqlalchemy import Column, String, Float, ForeignKey, Text, Enum as SQLEnum, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from devarchai.db.base import Base
from devarchai.models.mixins import TimestampMixin


class SubscriptionStatus(str, enum.Enum):
    """Subscription status."""

    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class PlanType(str, enum.Enum):
    """Subscription plan types."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Subscription(Base, TimestampMixin):
    """
    Subscription model for billing and plan management.

    Each organization has one active subscription.
    """

    __tablename__ = "subscriptions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Plan info
    plan = Column(SQLEnum(PlanType), default=PlanType.FREE, nullable=False)
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False)
    
    # Stripe info
    stripe_subscription_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_price_id = Column(String(255), nullable=True)
    
    # Billing cycle
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Trial
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    scans_this_period = Column(Integer, default=0, nullable=False)
    repositories_count = Column(Integer, default=0, nullable=False)
    team_members_count = Column(Integer, default=1, nullable=False)
    
    # Metadata
    metadata = Column(Text, nullable=True)  # JSON string
    
    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, plan={self.plan}, status={self.status})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "plan": self.plan.value,
            "status": self.status.value,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "scans_this_period": self.scans_this_period,
            "repositories_count": self.repositories_count,
            "team_members_count": self.team_members_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
