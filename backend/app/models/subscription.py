"""
Subscription and Pricing Models

Defines pricing tiers, features, and subscription management.
"""

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class PlanTier(str, enum.Enum):
    """Subscription plan tiers — must match DB enum 'plantype'."""

    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status matching DB enum."""
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class Currency(str, enum.Enum):
    """Supported currencies."""

    USD = "USD"
    INR = "INR"
    EUR = "EUR"
    GBP = "GBP"
    SGD = "SGD"
    AUD = "AUD"


# Country to currency mapping
COUNTRY_CURRENCY_MAP = {
    "US": Currency.USD,
    "USDT": Currency.USD,
    "IN": Currency.INR,
    "DE": Currency.EUR,
    "FR": Currency.EUR,
    "IT": Currency.EUR,
    "ES": Currency.EUR,
    "NL": Currency.EUR,
    "GB": Currency.GBP,
    "SG": Currency.SGD,
    "AU": Currency.AUD,
    "CA": Currency.USD,
    "JP": Currency.USD,
    "CN": Currency.USD,
    "BR": Currency.USD,
    "MX": Currency.USD,
}

# Default currency
DEFAULT_CURRENCY = Currency.USD


class Subscription(Base):
    """User subscription model."""

    __tablename__ = "subscriptions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Plan details
    plan = Column(SQLEnum(PlanTier, name="plantype", create_type=False), default=PlanTier.FREE, nullable=False)
    status = Column(SQLEnum(SubscriptionStatus, name="subscriptionstatus", create_type=False), default=SubscriptionStatus.ACTIVE, nullable=False)

    # Billing
    # (amount stored in payments table, not here)

    # Stripe integration
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_price_id = Column(String(255), nullable=True)

    # Razorpay integration
    razorpay_customer_id = Column(String(255), nullable=True)
    razorpay_subscription_id = Column(String(255), nullable=True)

    # Payment provider used
    provider = Column(String(50), nullable=True)  # 'stripe', 'razorpay', 'paypal'
    billing_interval = Column(String(20), nullable=True)  # 'monthly', 'yearly'
    plan_id = Column(PG_UUID(as_uuid=True), ForeignKey("plans.id"), nullable=True)

    # Trial
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)

    # Billing periods
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)

    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    cancelled_at = Column("canceled_at", DateTime(timezone=True), nullable=True)

    # Usage tracking
    scans_this_period = Column(Integer, default=0, nullable=False)
    repositories_count = Column(Integer, default=0, nullable=False)
    team_members_count = Column(Integer, default=1, nullable=False)
    subscription_metadata = Column(Text, nullable=True)

    # Dunning & grace period
    dunning_attempts = Column(Integer, default=0, nullable=False)
    last_payment_at = Column(DateTime(timezone=True), nullable=True)
    last_payment_id = Column(PG_UUID(as_uuid=True), nullable=True)
    grace_period_ends = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")
    plan_obj = relationship("Plan", back_populates="subscriptions",
                            primaryjoin="Subscription.plan_id==Plan.id",
                            foreign_keys="Subscription.plan_id")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, org_id={self.organization_id}, plan={self.plan})>"


# Add subscription relationship to User model
# This will be patched into app/models/user.py
