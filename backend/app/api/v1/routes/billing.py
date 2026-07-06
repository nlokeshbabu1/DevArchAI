"""Billing and subscription endpoints — production payment integration."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.user import User
from app.services.organization_provisioning import ensure_user_organization_membership
from app.services.payment_clients import RazorpayClient, StripeClient
from app.services.payment_service import PaymentService
from app.services.webhook_handler import WebhookIdempotencyGuard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


# ─── Request/Response Models ───────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str
    billing: str = "monthly"  # monthly | yearly
    coupon: str | None = None
    gateway: str | None = None  # Optional user gateway override


class RazorpayVerifyRequest(BaseModel):
    payment_id: str | None = None
    order_id: str | None = None
    signature: str | None = None
    razorpay_payment_id: str | None = None
    razorpay_order_id: str | None = None
    razorpay_signature: str | None = None
    plan: str | None = None
    billing: str | None = None

    def resolved_payment_id(self) -> str:
        return (self.payment_id or self.razorpay_payment_id or "").strip()

    def resolved_order_id(self) -> str:
        return (self.order_id or self.razorpay_order_id or "").strip()

    def resolved_signature(self) -> str:
        return (self.signature or self.razorpay_signature or "").strip()


class SubscriptionResponse(BaseModel):
    id: str | None
    user_id: str
    plan: str
    status: str
    current_period_start: str
    current_period_end: str | None
    cancel_at_period_end: bool
    trial_end: str | None
    scans_this_period: int
    repositories_count: int
    team_members_count: int
    features: dict


PLAN_NAME_MAP = {
    "free": "free",
    "plus": "plus",
    "pro": "pro",
    "enterprise": "enterprise",
}


def _normalize_country_code(country: str | None) -> str | None:
    if not country:
        return None
    normalized = country.strip().upper()
    if len(normalized) != 2:
        return None
    return normalized


def _detect_user_country(current_user: User, request: Request) -> str:
    """Resolve user country using request headers first, then persisted fields."""
    for header_name in ("CF-IPCountry", "CloudFront-Viewer-Country", "X-Country-Code"):
        header_country = _normalize_country_code(request.headers.get(header_name))
        if header_country:
            return header_country

    selected_country = _normalize_country_code(getattr(current_user, "selected_country", None))
    if selected_country:
        return selected_country

    user_country = _normalize_country_code(getattr(current_user, "country", None))
    if user_country:
        return user_country

    return "US"


def _normalize_gateway(gateway: str | None) -> str | None:
    if not gateway:
        return None
    normalized = gateway.strip().lower()
    if normalized not in {"stripe", "razorpay"}:
        return None
    return normalized


def _resolve_billing_gateway(current_user: User, request: Request) -> str:
    """Resolve the payment gateway entirely on the backend."""
    payment_svc = PaymentService()
    country = _detect_user_country(current_user, request)
    if country == "IN":
        return "razorpay"
    return payment_svc.get_payment_gateway(current_user)


def _map_plan_name(plan_name: str) -> str:
    normalized = (plan_name or "").strip().lower()
    return PLAN_NAME_MAP.get(normalized, "free")


def _normalize_billing_interval(billing_interval: str | None) -> str:
    normalized = (billing_interval or "monthly").strip().lower()
    return normalized if normalized in {"monthly", "yearly"} else "monthly"


def _apply_user_subscription_state(user: User, plan_name: str, gateway: str, status_value: str) -> None:
    user.subscription_plan = _map_plan_name(plan_name)
    user.subscription_status = status_value.lower()
    user.payment_provider = gateway


def _map_plan_tier(plan_name: str):
    from app.models.subscription import PlanTier

    normalized = _map_plan_name(plan_name)
    if normalized == "enterprise":
        return PlanTier.ENTERPRISE
    if normalized in {"plus", "pro"}:
        return PlanTier.PRO
    return PlanTier.FREE


async def _ensure_user_membership(db: AsyncSession, user: User):
    return await ensure_user_organization_membership(db, user)


async def _get_plan_record(db: AsyncSession, plan_name: str, billing_interval: str):
    from app.models.payment import Plan

    normalized_plan = _map_plan_name(plan_name)
    normalized_interval = _normalize_billing_interval(billing_interval)
    result = await db.execute(
        select(Plan).where(
            Plan.name == normalized_plan,
            Plan.interval == normalized_interval,
            Plan.is_active == True,
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def _get_plan_name_by_id(db: AsyncSession, plan_id) -> str | None:
    from app.models.payment import Plan

    if not plan_id:
        return None

    result = await db.execute(
        select(Plan.name).where(Plan.id == plan_id).limit(1)
    )
    return result.scalar_one_or_none()


async def _resolve_public_plan_name(db: AsyncSession, user: User, subscription) -> str:
    user_plan = _map_plan_name(getattr(user, "subscription_plan", ""))
    if user_plan != "free":
        return user_plan

    plan_name = await _get_plan_name_by_id(db, getattr(subscription, "plan_id", None))
    if plan_name:
        return _map_plan_name(plan_name)

    return _map_plan_name(subscription.plan.value if hasattr(subscription.plan, "value") else str(subscription.plan))


async def _resolve_razorpay_order_context(
    db: AsyncSession,
    razorpay_client: RazorpayClient,
    current_user: User,
    verify_request: RazorpayVerifyRequest,
) -> dict[str, Any]:
    payment_id = verify_request.resolved_payment_id()
    order_id = verify_request.resolved_order_id()
    fallback_plan = (verify_request.plan or "").strip().lower()
    fallback_billing = _normalize_billing_interval(verify_request.billing)

    logger.info(
        "Fetching Razorpay order for verification",
        extra={
            "user_id": str(current_user.id),
            "order_id": order_id,
            "payment_id": payment_id,
        },
    )

    order = await razorpay_client.fetch_order(order_id)
    notes = order.get("notes") or {}
    order_user_id = (notes.get("user_id") or "").strip()
    if order_user_id and order_user_id != str(current_user.id):
        logger.warning(
            "Razorpay order user mismatch",
            extra={
                "current_user_id": str(current_user.id),
                "order_user_id": order_user_id,
                "order_id": order_id,
            },
        )
        raise HTTPException(status_code=403, detail="Payment does not belong to the current user")

    raw_plan_name = ((notes.get("plan") or fallback_plan) or "").strip().lower()
    if raw_plan_name not in PLAN_NAME_MAP:
        logger.warning(
            "Unable to resolve plan metadata from Razorpay order",
            extra={
                "user_id": str(current_user.id),
                "order_id": order_id,
                "raw_plan_name": raw_plan_name,
            },
        )
        raise HTTPException(status_code=400, detail="Unable to resolve subscription plan for payment")

    plan_name = _map_plan_name(raw_plan_name)
    billing_interval = _normalize_billing_interval(notes.get("interval") or notes.get("billing") or fallback_billing)
    plan_record = await _get_plan_record(db, plan_name, billing_interval)

    logger.info(
        "Resolved Razorpay order context",
        extra={
            "user_id": str(current_user.id),
            "order_id": order_id,
            "plan": plan_name,
            "billing_interval": billing_interval,
            "currency": (order.get("currency") or "INR").upper(),
        },
    )

    return {
        "order": order,
        "notes": notes,
        "plan_name": plan_name,
        "billing_interval": billing_interval,
        "plan_record": plan_record,
        "amount": int(order.get("amount") or 0),
        "currency": (order.get("currency") or "INR").upper(),
    }


# ─── Plans ─────────────────────────────────────────────────────────────

@router.get("/plans", response_model=dict)
async def list_plans(db: AsyncSession = Depends(get_db)):
    """List all available plans with pricing. No auth required."""
    from app.models.payment import Plan

    result = await db.execute(
        select(Plan)
        .where(Plan.is_active == True)
        .order_by(Plan.sort_order, Plan.interval)
    )
    plans = result.scalars().all()

    return {
        "plans": [
            {
                "id": str(p.id),
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "interval": p.interval.value if hasattr(p.interval, "value") else str(p.interval),
                "price_usd": p.price_usd,
                "price_inr": p.price_inr,
                "price_eur": p.price_eur,
                "price_gbp": p.price_gbp,
                "features": p.features,
                "trial_days": p.trial_days,
            }
            for p in plans
        ]
    }


# ─── Enterprise Contact Sales ──────────────────────────────────────────

@router.post("/enterprise", response_model=dict)
async def enterprise_contact_sales(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enterprise plan: No payment gateway. Contact sales flow.
    Creates a pending enterprise subscription for admin review.
    """
    from app.models.subscription import Subscription

    membership = await _ensure_user_membership(db, current_user)

    # Check for existing active subscription
    result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == membership.organization_id,
            Subscription.status.in_(["ACTIVE", "TRIAL"]),
        ).order_by(Subscription.created_at.desc()).limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Already have an active subscription ({existing.plan.value if hasattr(existing.plan, 'value') else existing.plan})"
        )

    # Create pending enterprise subscription for admin review
    sub = Subscription(
        organization_id=membership.organization_id,
        plan=PlanTier.ENTERPRISE,
        status="TRIAL",  # Trial status until admin approves
        billing_interval="monthly",
        cancel_at_period_end=False,
    )
    db.add(sub)
    await db.commit()

    # TODO: Send email to sales team with user/org details
    logger.info(f"Enterprise contact sales request from user {current_user.id}, org {membership.organization_id}")

    return {
        "message": "Sales team will contact you within 24 hours",
        "status": "pending_review",
        "subscription_id": str(sub.id),
    }


# ─── Checkout ──────────────────────────────────────────────────────────

@router.get("/gateway", response_model=dict)
async def get_billing_gateway(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Return the backend-selected payment gateway for the current user."""
    return {"gateway": _resolve_billing_gateway(current_user, request)}

@router.post("/checkout", response_model=dict)
async def create_checkout_session(
    http_request: Request,
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a checkout session with the appropriate payment provider.

    Routes to Razorpay for India, Stripe for all other countries.
    """
    payment_svc = PaymentService()
    user_country = _detect_user_country(current_user, http_request)
    selected_gateway = _resolve_billing_gateway(current_user, http_request)

    if request.gateway and _normalize_gateway(request.gateway) is None:
        raise HTTPException(status_code=400, detail="Invalid gateway. Use 'stripe' or 'razorpay'.")

    try:
        current_user.selected_country = user_country
        current_user.selected_gateway = selected_gateway
        await db.flush()

        result = await payment_svc.create_checkout(
            db=db,
            user=current_user,
            plan_name=request.plan,
            billing_interval=request.billing,
            user_country=user_country,
            coupon_code=request.coupon,
            selected_gateway=selected_gateway,
        )
        checkout_provider = result.get("gateway", selected_gateway)

        logger.info(
            "Billing gateway selected",
            extra={
                "user_id": str(current_user.id),
                "country": user_country,
                "selected_gateway": selected_gateway,
                "checkout_provider": checkout_provider,
                "plan": request.plan,
                "billing_interval": request.billing,
            },
        )
        await db.commit()
        return result
    except ValueError as e:
        await db.rollback()
        logger.warning(f"Checkout validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.exception(f"Checkout creation failed with exception: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")


# ─── Razorpay Payment Verification ─────────────────────────────────────

@router.post("/verify", response_model=dict)
async def verify_payment(
    request: RazorpayVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a Razorpay payment signature and activate subscription."""
    from datetime import timedelta

    from app.models.payment import Payment, PaymentProvider, PaymentStatus, PaymentType
    from app.models.subscription import Subscription

    payment_id = request.resolved_payment_id()
    order_id = request.resolved_order_id()
    signature = request.resolved_signature()

    if not payment_id or not order_id or not signature:
        raise HTTPException(status_code=400, detail="Missing Razorpay payment verification fields")

    logger.info(
        "Starting Razorpay payment verification",
        extra={
            "user_id": str(current_user.id),
            "payment_id": payment_id,
            "order_id": order_id,
        },
    )

    try:
        rzp = RazorpayClient()
        valid = rzp.verify_payment_signature(
            razorpay_payment_id=payment_id,
            razorpay_order_id=order_id,
            razorpay_signature=signature,
        )
        if not valid:
            logger.warning(
                "Razorpay payment signature verification failed",
                extra={
                    "user_id": str(current_user.id),
                    "payment_id": payment_id,
                    "order_id": order_id,
                },
            )
            raise HTTPException(status_code=400, detail="Invalid payment signature")

        membership = await _ensure_user_membership(db, current_user)
        if not membership:
            raise HTTPException(status_code=404, detail="No organization found")

        order_context = await _resolve_razorpay_order_context(db, rzp, current_user, request)
        plan_name = order_context["plan_name"]
        billing_interval = order_context["billing_interval"]
        plan_record = order_context["plan_record"]
        plan_tier = _map_plan_tier(plan_name)

        now = datetime.now(UTC)
        period_end = now + timedelta(days=30 if billing_interval == "monthly" else 365)

        result = await db.execute(
            select(Subscription)
            .where(Subscription.organization_id == membership.organization_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub = result.scalar_one_or_none()

        payment_result = await db.execute(
            select(Payment).where(
                Payment.provider == PaymentProvider.RAZORPAY,
                Payment.provider_payment_id == payment_id,
            ).limit(1)
        )
        payment = payment_result.scalar_one_or_none()

        if payment is None:
            payment_type = PaymentType.INITIAL if sub is None else PaymentType.UPGRADE
            payment = Payment(
                user_id=current_user.id,
                provider=PaymentProvider.RAZORPAY,
                type=payment_type,
                status=PaymentStatus.COMPLETED,
                amount=order_context["amount"],
                currency=order_context["currency"],
                provider_payment_id=payment_id,
                provider_order_id=order_id,
                provider_response={
                    "order": order_context["order"],
                    "notes": order_context["notes"],
                },
            )
            db.add(payment)
            await db.flush()
        else:
            payment.status = PaymentStatus.COMPLETED
            payment.amount = order_context["amount"]
            payment.currency = order_context["currency"]
            payment.provider_order_id = order_id
            payment.provider_response = {
                "order": order_context["order"],
                "notes": order_context["notes"],
            }

        if sub:
            sub.plan = plan_tier
            sub.plan_id = getattr(plan_record, "id", None)
            sub.status = "ACTIVE"
            sub.provider = "razorpay"
            sub.billing_interval = billing_interval
            sub.current_period_start = now
            sub.current_period_end = period_end
            sub.cancel_at_period_end = False
            sub.cancelled_at = None
            sub.last_payment_at = now
            sub.last_payment_id = payment.id
        else:
            sub = Subscription(
                organization_id=membership.organization_id,
                plan=plan_tier,
                plan_id=getattr(plan_record, "id", None),
                status="ACTIVE",
                provider="razorpay",
                billing_interval=billing_interval,
                current_period_start=now,
                current_period_end=period_end,
                cancel_at_period_end=False,
                last_payment_at=now,
                last_payment_id=payment.id,
            )
            db.add(sub)
            await db.flush()

        payment.subscription_id = sub.id
        _apply_user_subscription_state(current_user, plan_name, "razorpay", "active")
        await db.commit()

        logger.info(
            "Razorpay payment verified and subscription activated",
            extra={
                "user_id": str(current_user.id),
                "payment_id": payment_id,
                "order_id": order_id,
                "plan": plan_name,
                "billing_interval": billing_interval,
                "subscription_id": str(sub.id),
            },
        )

        return {
            "success": True,
            "payment_id": payment_id,
            "order_id": order_id,
            "subscription_id": str(sub.id),
            "plan": plan_name,
            "status": "active",
            "current_period_end": period_end.isoformat(),
            "message": "Payment verified and subscription activated",
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception(
            "Unexpected Razorpay verification failure",
            extra={
                "user_id": str(current_user.id),
                "payment_id": payment_id,
                "order_id": order_id,
                "error_type": type(exc).__name__,
            },
        )
        raise HTTPException(status_code=500, detail="Failed to verify payment")


# ─── Stripe Webhook ────────────────────────────────────────────────────

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Stripe webhooks.

    MUST respond within 3 seconds. Heavy processing is deferred to Celery.
    """
    from app.models.payment import Payment, PaymentProvider, PaymentStatus, PaymentType
    from app.models.subscription import Subscription, SubscriptionStatus

    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    stripe = StripeClient()
    event = stripe.verify_webhook(payload, sig_header)
    if event is None:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Idempotency guard
    guard = WebhookIdempotencyGuard()
    already = await guard.is_already_processed(db, "stripe", event.get("id", ""))
    if already:
        return {"status": "already_processed"}

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    # Process event type
    async with db.begin():
        if event_type == "checkout.session.completed":
            # Customer completed checkout — activate subscription
            customer_email = data.get("customer_email")
            subscription_id = data.get("subscription")
            metadata = data.get("metadata", {})

            # Find user by email
            from app.core.security import hash_email
            email_hash = hash_email(customer_email) if customer_email else None
            if email_hash:
                user_result = await db.execute(
                    select(User).where(User.email_hash == email_hash).limit(1)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    membership = await _ensure_user_membership(db, user)
                    if membership:
                        sub_result = await db.execute(
                            select(Subscription).where(
                                Subscription.organization_id == membership.organization_id,
                            ).order_by(Subscription.created_at.desc()).limit(1)
                        )
                        sub = sub_result.scalar_one_or_none()
                        if sub:
                            sub.stripe_subscription_id = subscription_id
                            sub.provider = "stripe"
                            sub.status = SubscriptionStatus.ACTIVE.value
                            sub.last_payment_at = datetime.now(UTC)
                            payment = Payment(
                                user_id=user.id,
                                subscription_id=sub.id,
                                provider=PaymentProvider.STRIPE,
                                type=PaymentType.INITIAL,
                                status=PaymentStatus.COMPLETED,
                                amount=data.get("amount_total", 0) or 0,
                                currency=(data.get("currency", "USD") or "USD").upper(),
                                provider_payment_id=data.get("payment_intent") or data.get("id"),
                                provider_order_id=data.get("id"),
                                provider_response=data,
                            )
                            db.add(payment)
                            _apply_user_subscription_state(
                                user,
                                metadata.get("plan", "pro"),
                                "stripe",
                                SubscriptionStatus.ACTIVE.value,
                            )

        elif event_type == "invoice.payment_succeeded":
            # Renewal payment succeeded
            subscription_stripe_id = data.get("subscription")
            if subscription_stripe_id:
                sub_result = await db.execute(
                    select(Subscription).where(
                        Subscription.stripe_subscription_id == subscription_stripe_id,
                    ).limit(1)
                )
                sub = sub_result.scalar_one_or_none()
                if sub:
                    user_result = await db.execute(
                        select(User).where(User.current_org_id == sub.organization_id).limit(1)
                    )
                    user = user_result.scalar_one_or_none()
                    sub.status = SubscriptionStatus.ACTIVE.value
                    sub.provider = "stripe"
                    sub.dunning_attempts = 0
                    sub.last_payment_at = datetime.now(UTC)
                    if user:
                        _apply_user_subscription_state(
                            user,
                            "pro" if getattr(sub.plan, "value", str(sub.plan)) != "ENTERPRISE" else "enterprise",
                            "stripe",
                            SubscriptionStatus.ACTIVE.value,
                        )

        elif event_type == "invoice.payment_failed":
            # Renewal payment failed
            subscription_stripe_id = data.get("subscription")
            if subscription_stripe_id:
                sub_result = await db.execute(
                    select(Subscription).where(
                        Subscription.stripe_subscription_id == subscription_stripe_id,
                    ).limit(1)
                )
                sub = sub_result.scalar_one_or_none()
                if sub:
                    user_result = await db.execute(
                        select(User).where(User.current_org_id == sub.organization_id).limit(1)
                    )
                    user = user_result.scalar_one_or_none()
                    sub.status = SubscriptionStatus.PAST_DUE.value
                    sub.dunning_attempts += 1
                    if user:
                        _apply_user_subscription_state(
                            user,
                            user.subscription_plan or "free",
                            "stripe",
                            SubscriptionStatus.PAST_DUE.value,
                        )

        elif event_type == "customer.subscription.deleted":
            # Subscription cancelled
            subscription_stripe_id = data.get("id")
            if subscription_stripe_id:
                sub_result = await db.execute(
                    select(Subscription).where(
                        Subscription.stripe_subscription_id == subscription_stripe_id,
                    ).limit(1)
                )
                sub = sub_result.scalar_one_or_none()
                if sub:
                    user_result = await db.execute(
                        select(User).where(User.current_org_id == sub.organization_id).limit(1)
                    )
                    user = user_result.scalar_one_or_none()
                    sub.status = SubscriptionStatus.CANCELED.value
                    sub.cancelled_at = datetime.now(UTC)
                    if user:
                        _apply_user_subscription_state(user, "free", "stripe", SubscriptionStatus.CANCELED.value)

        # Record the event (inside same transaction)
        await guard.record_event(db, "stripe", event["id"], event_type, event)

    logger.info(f"Stripe webhook processed: {event_type}")
    return {"status": "success"}


# ─── Razorpay Webhook ──────────────────────────────────────────────────

@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Razorpay webhooks with signature verification and idempotency."""
    from app.models.payment import Payment, PaymentProvider, PaymentStatus, PaymentType
    from app.models.subscription import Subscription, SubscriptionStatus

    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    rzp = RazorpayClient()
    event = rzp.verify_webhook(payload, signature)
    if event is None:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_id = event.get("id", "")
    event_type = event.get("event", "")
    payload_data = event.get("payload", {})

    # Idempotency guard
    guard = WebhookIdempotencyGuard()
    already = await guard.is_already_processed(db, "razorpay", event_id)
    if already:
        return {"status": "already_processed"}

    # Process event type
    async with db.begin():
        if event_type == "payment.captured":
            # Payment succeeded
            payment_data = payload_data.get("payment", {}).get("entity", {})
            payment_id = payment_data.get("id", "")
            order_id = payment_data.get("order_id", "")
            amount = payment_data.get("amount", 0)

            # Find subscription by order_id in notes
            notes = payment_data.get("notes", {})
            user_id = notes.get("user_id")
            if user_id:
                user_result = await db.execute(
                    select(User).where(User.id == user_id).limit(1)
                )
                user = user_result.scalar_one_or_none()
                membership = await _ensure_user_membership(db, user) if user else None
                if membership:
                    sub_result = await db.execute(
                        select(Subscription).where(
                            Subscription.organization_id == membership.organization_id,
                        ).order_by(Subscription.created_at.desc()).limit(1)
                    )
                    sub = sub_result.scalar_one_or_none()
                    if sub:
                        sub.status = SubscriptionStatus.ACTIVE.value
                        sub.last_payment_at = datetime.now(UTC)
                        sub.provider = "razorpay"
                        sub.razorpay_subscription_id = notes.get("subscription_id")
                        if user:
                            _apply_user_subscription_state(
                                user,
                                notes.get("plan", "pro"),
                                "razorpay",
                                SubscriptionStatus.ACTIVE.value,
                            )

                        # Create payment record
                        payment = Payment(
                            user_id=user_id,
                            subscription_id=sub.id,
                            provider=PaymentProvider.RAZORPAY,
                            type=PaymentType.INITIAL,
                            status=PaymentStatus.COMPLETED,
                            amount=amount,
                            currency=payment_data.get("currency", "INR"),
                            provider_payment_id=payment_id,
                            provider_order_id=order_id,
                        )
                        db.add(payment)

        elif event_type == "payment.failed":
            # Payment failed
            payment_data = payload_data.get("payment", {}).get("entity", {})
            notes = payment_data.get("notes", {})
            user_id = notes.get("user_id")
            if user_id:
                user_result = await db.execute(
                    select(User).where(User.id == user_id).limit(1)
                )
                user = user_result.scalar_one_or_none()
                membership = await _ensure_user_membership(db, user) if user else None
                if membership:
                    sub_result = await db.execute(
                        select(Subscription).where(
                            Subscription.organization_id == membership.organization_id,
                        ).order_by(Subscription.created_at.desc()).limit(1)
                    )
                    sub = sub_result.scalar_one_or_none()
                    if sub:
                        sub.status = SubscriptionStatus.PAST_DUE.value
                        sub.dunning_attempts += 1
                        if user:
                            _apply_user_subscription_state(
                                user,
                                user.subscription_plan or "free",
                                "razorpay",
                                SubscriptionStatus.PAST_DUE.value,
                            )

        elif event_type == "subscription.charged":
            # Subscription renewal charged
            sub_data = payload_data.get("subscription", {}).get("entity", {})
            razorpay_sub_id = sub_data.get("id", "")

            sub_result = await db.execute(
                select(Subscription).where(
                    Subscription.razorpay_subscription_id == razorpay_sub_id,
                ).limit(1)
            )
            sub = sub_result.scalar_one_or_none()
            if sub:
                sub.status = SubscriptionStatus.ACTIVE.value
                sub.dunning_attempts = 0
                sub.last_payment_at = datetime.now(UTC)

        # Record the event (inside same transaction)
        await guard.record_event(db, "razorpay", event_id, event_type, event)

    logger.info(f"Razorpay webhook processed: {event_type}")
    return {"status": "success"}


# ─── Subscription ──────────────────────────────────────────────────────

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current subscription for user."""
    if not current_user:
        return _free_plan_response("anonymous")

    from app.models.subscription import Subscription
    membership = await _ensure_user_membership(db, current_user)

    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.organization_id == membership.organization_id,
            Subscription.status.in_(["ACTIVE", "TRIAL"]),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()

    if not sub:
        return _free_plan_response(str(current_user.id))

    public_plan_name = await _resolve_public_plan_name(db, current_user, sub)

    return {
        "id": str(sub.id),
        "user_id": str(current_user.id),
        "plan": public_plan_name,
        "status": sub.status,
        "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else "",
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
        "scans_this_period": sub.scans_this_period,
        "repositories_count": sub.repositories_count,
        "team_members_count": getattr(sub, "team_members_count", 1),
        "features": _plan_features(public_plan_name),
    }


@router.post("/subscription", response_model=dict)
async def activate_subscription(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Activate or update subscription after successful checkout.
    
    SECURITY: This endpoint should only be called after payment verification.
    In production, subscription activation should happen via webhooks only.
    This endpoint is for mock/dev mode or manual activation.
    """
    from datetime import datetime, timedelta

    from app.models.subscription import Subscription

    membership = await _ensure_user_membership(db, current_user)

    # Check if payment providers are configured
    stripe_configured = bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY != "sk_test_xxx")
    razorpay_configured = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_ID != "rzp_test_xxx")

    # If payment providers are configured, require payment verification
    # Only allow direct activation in mock/dev mode
    if stripe_configured or razorpay_configured:
        logger.warning(
            f"Direct subscription activation blocked - payment providers configured. "
            f"User {current_user.id} attempted to activate '{request.plan}' without payment verification."
        )
        raise HTTPException(
            status_code=403,
            detail="Direct subscription activation is disabled when payment providers are configured. "
                   "Subscriptions are activated via payment webhooks only."
        )

    # Mock/dev mode: allow direct activation
    logger.info(f"Mock mode: Activating subscription for user {current_user.id}, plan {request.plan}")

    # Check for existing subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == membership.organization_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()

    now = datetime.now(UTC)
    billing_interval = _normalize_billing_interval(getattr(request, "billing", "monthly"))
    period_end = now + timedelta(days=30 if billing_interval == "monthly" else 365)
    plan_name = _map_plan_name(request.plan)
    plan_tier = _map_plan_tier(plan_name)
    plan_record = await _get_plan_record(db, plan_name, billing_interval)

    if sub:
        # Update existing subscription
        sub.plan = plan_tier
        sub.plan_id = getattr(plan_record, "id", None)
        sub.status = "ACTIVE"
        sub.billing_interval = billing_interval
        sub.current_period_start = now
        sub.current_period_end = period_end
        sub.cancel_at_period_end = False
        sub.cancelled_at = None
        sub.last_payment_at = now
    else:
        # Create new subscription
        sub = Subscription(
            organization_id=membership.organization_id,
            plan=plan_tier,
            plan_id=getattr(plan_record, "id", None),
            status="ACTIVE",
            billing_interval=billing_interval,
            current_period_start=now,
            current_period_end=period_end,
            cancel_at_period_end=False,
        )
        db.add(sub)

    _apply_user_subscription_state(current_user, plan_name, "mock", "active")
    await db.commit()

    return {
        "message": "Subscription activated successfully",
        "plan": plan_name,
        "status": "active",
        "current_period_end": period_end.isoformat(),
        "mode": "mock",
    }


@router.post("/cancel", response_model=dict)
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel subscription at end of current billing period."""
    from app.models.subscription import Subscription

    membership = await _ensure_user_membership(db, current_user)

    result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == membership.organization_id,
            Subscription.status == "ACTIVE",
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")

    sub.cancel_at_period_end = True
    sub.cancelled_at = datetime.now(UTC)
    await db.commit()

    return {
        "message": "Subscription will be cancelled at the end of the current billing period",
        "cancel_at_period_end": True,
    }


# ─── Invoices ──────────────────────────────────────────────────────────

@router.get("/invoices", response_model=dict)
async def list_invoices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List invoices for user."""
    from app.models.payment import Invoice
    result = await db.execute(
        select(Invoice)
        .where(Invoice.user_id == current_user.id)
        .order_by(Invoice.created_at.desc())
        .limit(50)
    )
    invoices = result.scalars().all()

    return {
        "invoices": [
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "status": inv.status,
                "total_amount": inv.total_amount,
                "currency": inv.currency,
                "period_start": inv.period_start.isoformat() if inv.period_start else None,
                "period_end": inv.period_end.isoformat() if inv.period_end else None,
                "pdf_url": inv.pdf_url,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in invoices
        ],
        "has_more": False,
    }


# ─── Usage ─────────────────────────────────────────────────────────────

@router.get("/usage", response_model=dict)
async def get_usage(
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current usage for user."""
    if not current_user:
        user_id = "anonymous"
    else:
        user_id = str(current_user.id)

    return {
        "user_id": user_id,
        "plan": "free",
        "usage": {
            "scans_this_period": 0,
            "repositories_count": 0,
            "team_members_count": 1,
        },
        "limits": {
            "max_scans_per_month": 10,
            "max_repositories": 5,
        },
    }


# ─── Helpers ───────────────────────────────────────────────────────────

def _free_plan_response(user_id: str) -> dict:
    return {
        "id": None,
        "user_id": user_id,
        "plan": "free",
        "status": "active",
        "current_period_start": datetime.now(UTC).isoformat(),
        "current_period_end": None,
        "cancel_at_period_end": False,
        "trial_end": None,
        "scans_this_period": 0,
        "repositories_count": 0,
        "team_members_count": 1,
        "features": {
            "max_repositories": 5,
            "max_scans_per_month": 10,
            "ai_suggestions": False,
            "api_access": False,
            "priority_support": False,
        },
    }


def _plan_features(plan) -> dict:
    """Extract features from a plan. Handles both enum and string plans."""
    plan_name = _map_plan_name(plan.value if hasattr(plan, "value") else str(plan))
    features = {
        "free": {
            "max_repositories": 5,
            "max_scans_per_month": 10,
            "ai_suggestions": False,
            "api_access": False,
            "priority_support": False,
        },
        "plus": {
            "max_repositories": 50,
            "max_scans_per_month": 100,
            "ai_suggestions": True,
            "api_access": False,
            "priority_support": False,
        },
        "pro": {
            "max_repositories": -1,
            "max_scans_per_month": -1,
            "ai_suggestions": True,
            "api_access": True,
            "priority_support": True,
        },
        "enterprise": {
            "max_repositories": -1,
            "max_scans_per_month": -1,
            "ai_suggestions": True,
            "api_access": True,
            "priority_support": True,
        },
    }
    return features.get(plan_name, features["free"])
