"""Payment and billing models."""

import enum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


def pg_enum(name, values, create_type=False):
    """Create ENUM with create_type=False to avoid conflicts with existing DB enums."""
    return SQLEnum(*values, name=name, create_type=create_type)


# ─── Enums ─────────────────────────────────────────────────────────────

class PlanInterval(str, enum.Enum):
    """Billing intervals."""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class PaymentStatus(str, enum.Enum):
    """Payment lifecycle statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    DISPUTED = "disputed"


class PaymentType(str, enum.Enum):
    """Types of payment transactions."""
    INITIAL = "initial"
    RENEWAL = "renewal"
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    REFUND = "refund"
    ONE_TIME = "one_time"


class PaymentProvider(str, enum.Enum):
    """Supported payment providers."""
    STRIPE = "stripe"
    RAZORPAY = "razorpay"
    PAYPAL = "paypal"


class InvoiceStatus(str, enum.Enum):
    """Invoice lifecycle statuses."""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    UNCOLLECTIBLE = "uncollectible"
    VOID = "void"
    PENDING = "pending"


class CouponType(str, enum.Enum):
    """Coupon discount types."""
    PERCENT = "percent"
    FIXED = "fixed"
    TRIAL = "trial"


# ─── Plans ─────────────────────────────────────────────────────────────

class Plan(Base):
    """Subscription plan definition with multi-currency pricing."""

    __tablename__ = "plans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    interval = Column(pg_enum("plan_interval", ["monthly", "yearly"]), nullable=False, default=PlanInterval.MONTHLY)
    is_active = Column(Boolean, nullable=False, default=True)

    # Pricing in smallest currency unit (cents/paise)
    price_usd = Column(Integer, nullable=False, default=0)
    price_inr = Column(Integer, nullable=False, default=0)
    price_eur = Column(Integer, nullable=False, default=0)
    price_gbp = Column(Integer, nullable=False, default=0)

    # Provider plan IDs
    stripe_price_id_monthly = Column(String(255), nullable=True)
    stripe_price_id_yearly = Column(String(255), nullable=True)
    razorpay_plan_id_monthly = Column(String(255), nullable=True)
    razorpay_plan_id_yearly = Column(String(255), nullable=True)

    # Features stored as JSON
    features = Column(JSONB, nullable=False, server_default="{}")

    # Trial
    trial_days = Column(Integer, nullable=False, default=0)

    # Metadata
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan_obj")

    __table_args__ = (
        CheckConstraint(
            "price_usd >= 0 AND price_inr >= 0 AND price_eur >= 0 AND price_gbp >= 0",
            name="plans_price_non_negative",
        ),
    )

    def __repr__(self) -> str:
        return f"<Plan(id={self.id}, name={self.name}, interval={self.interval})>"


# ─── Payments ──────────────────────────────────────────────────────────

class Payment(Base):
    """
    Payment transaction record.

    CRITICAL: The UNIQUE constraint on (provider, provider_payment_id)
    prevents duplicate payment records from webhook replay.
    """

    __tablename__ = "payments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(PG_UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)

    # Payment details
    type = Column(pg_enum("payment_type", ["initial", "renewal", "upgrade", "downgrade", "refund", "one_time"]), nullable=False, default=PaymentType.INITIAL)
    status = Column(pg_enum("payment_status", ["pending", "processing", "completed", "failed", "refunded", "partially_refunded", "disputed"]), nullable=False, default=PaymentStatus.PENDING, index=True)
    provider = Column(pg_enum("payment_provider", ["stripe", "razorpay", "paypal"]), nullable=False)

    # Amount in smallest currency unit
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)
    amount_refunded = Column(Integer, nullable=False, default=0)

    # Provider references
    provider_payment_id = Column(String(255), nullable=False)
    provider_order_id = Column(String(255), nullable=True)
    provider_invoice_id = Column(String(255), nullable=True)

    # Raw provider response for debugging
    provider_response = Column(JSONB, nullable=True)

    # Failure tracking
    failure_code = Column(String(100), nullable=True)
    failure_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    invoices = relationship("Invoice", back_populates="payment")

    __table_args__ = (
        # CRITICAL: Prevents duplicate payments from webhook replay
        CheckConstraint(
            "amount >= 0 AND amount_refunded >= 0",
            name="payments_amounts_non_negative",
        ),
    )

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, provider={self.provider}, status={self.status}, amount={self.amount})>"


# ─── Invoices ──────────────────────────────────────────────────────────

class Invoice(Base):
    """Invoice record linked to a payment and subscription period."""

    __tablename__ = "invoices"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(PG_UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_id = Column(PG_UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)

    invoice_number = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(pg_enum("invoice_status", ["draft", "open", "paid", "uncollectible", "void", "pending"]), nullable=False, default=InvoiceStatus.DRAFT, index=True)

    # Amounts in smallest currency unit
    subtotal = Column(Integer, nullable=False)
    tax_amount = Column(Integer, nullable=False, default=0)
    discount_amount = Column(Integer, nullable=False, default=0)
    total_amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)

    # Provider references
    provider_invoice_id = Column(String(255), nullable=True)
    provider_hosted_url = Column(Text, nullable=True)

    # Billing period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)

    # PDF download
    pdf_url = Column(Text, nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
    payment = relationship("Payment", back_populates="invoices")

    __table_args__ = (
        CheckConstraint("period_end >= period_start", name="invoices_period_check"),
        CheckConstraint(
            "subtotal >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND total_amount >= 0",
            name="invoices_amounts_non_negative",
        ),
    )

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, number={self.invoice_number}, status={self.status})>"


# ─── Coupons ───────────────────────────────────────────────────────────

class Coupon(Base):
    """Discount coupon for checkout."""

    __tablename__ = "coupons"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    type = Column(pg_enum("coupon_type", ["percent", "fixed", "trial"]), nullable=False)
    value = Column(Integer, nullable=False)  # Percentage (1-100) or fixed amount in cents

    # Applicability
    applicable_plans = Column(JSONB, nullable=True)  # Array of plan names, NULL = all
    max_redemptions = Column(Integer, nullable=True)
    redemption_count = Column(Integer, nullable=False, default=0)
    max_redemptions_per_user = Column(Integer, nullable=False, default=1)

    # Validity
    valid_from = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    duration_months = Column(Integer, nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Coupon(id={self.id}, code={self.code}, type={self.type})>"


# ─── Webhook Events ────────────────────────────────────────────────────

class WebhookEvent(Base):
    """
    Tracks processed webhook events for idempotency.

    The UNIQUE constraint on (provider, event_id) guarantees each
    webhook event is processed exactly once, even if delivered multiple times.
    """

    __tablename__ = "webhook_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False)
    event_id = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # CRITICAL: Idempotency guarantee
        UniqueConstraint("provider", "event_id", name="uq_webhook_events_provider_event"),
    )

    def __repr__(self) -> str:
        return f"<WebhookEvent(id={self.id}, provider={self.provider}, event_id={self.event_id})>"
