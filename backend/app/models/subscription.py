"""
Subscription and Pricing Models

Defines pricing tiers, features, and subscription management.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
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
    """Subscription plan tiers."""

    FREE = "free"
    PLUS = "plus"
    PRO = "pro"
    ENTERPRISE = "enterprise"


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
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Plan details
    plan = Column(SQLEnum(PlanTier), default=PlanTier.FREE, nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, cancelled, past_due
    
    # Billing
    currency = Column(SQLEnum(Currency), default=DEFAULT_CURRENCY, nullable=False)
    amount = Column(Float, nullable=True)  # Amount in local currency
    
    # Stripe integration
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_price_id = Column(String(255), nullable=True)
    
    # Trial
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    
    # Billing periods
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    
    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Usage tracking
    scans_this_period = Column(Integer, default=0, nullable=False)
    repositories_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="subscription")

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan={self.plan})>"


# Add subscription relationship to User model
# This will be patched into app/models/user.py
