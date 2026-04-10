"""Billing and subscription endpoints — production payment integration."""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.user import User
from app.services.payment_clients import RazorpayClient, StripeClient
from app.services.payment_router import PaymentRouter
from app.services.webhook_handler import WebhookIdempotencyGuard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


# ─── Request/Response Models ───────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str
    billing: str = "monthly"  # monthly | yearly
    coupon: Optional[str] = None


class RazorpayVerifyRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    plan: str
    billing: str = "monthly"


class SubscriptionResponse(BaseModel):
    id: Optional[str]
    user_id: str
    plan: str
    status: str
    current_period_start: str
    current_period_end: Optional[str]
    cancel_at_period_end: bool
    trial_end: Optional[str]
    scans_this_period: int
    repositories_count: int
    team_members_count: int
    features: dict


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
    from app.models.subscription import Subscription, PlanTier
    from app.models.organization import OrganizationMember

    # Get user's org
    org_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == current_user.id,
        ).limit(1)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="No organization found")

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

@router.post("/checkout", response_model=dict)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a checkout session with the appropriate payment provider.

    Routes to Razorpay for India, Stripe for all other countries.
    """
    router_svc = PaymentRouter()
    user_country = getattr(current_user, "country", None) or "US"

    try:
        result = await router_svc.create_checkout(
            db=db,
            user=current_user,
            plan_name=request.plan,
            billing_interval=request.billing,
            user_country=user_country,
            coupon_code=request.coupon,
        )
        return result
    except ValueError as e:
        logger.warning(f"Checkout validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
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
    from app.models.subscription import Subscription, PlanTier
    from app.models.organization import OrganizationMember
    from app.models.payment import Payment, PaymentProvider, PaymentStatus, PaymentType
    from datetime import timedelta

    rzp = RazorpayClient()
    valid = rzp.verify_payment_signature(
        razorpay_payment_id=request.razorpay_payment_id,
        razorpay_order_id=request.razorpay_order_id,
        razorpay_signature=request.razorpay_signature,
    )
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Get user's org
    org_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == current_user.id,
        ).limit(1)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="No organization found")

    # Determine plan tier
    plan_map = {
        "free": PlanTier.FREE,
        "plus": PlanTier.PRO,
        "pro": PlanTier.PRO,
        "enterprise": PlanTier.ENTERPRISE,
    }
    plan_tier = plan_map.get(request.plan.lower(), PlanTier.FREE)

    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30 if request.billing == "monthly" else 365)

    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        provider=PaymentProvider.RAZORPAY,
        type=PaymentType.INITIAL,
        status=PaymentStatus.COMPLETED,
        amount=0,  # Amount stored in Razorpay order
        currency="INR",
        provider_payment_id=request.razorpay_payment_id,
        provider_order_id=request.razorpay_order_id,
    )
    db.add(payment)
    await db.flush()

    # Create or update subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == membership.organization_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.plan = plan_tier
        sub.status = "ACTIVE"
        sub.billing_interval = request.billing
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
            status="ACTIVE",
            billing_interval=request.billing,
            current_period_start=now,
            current_period_end=period_end,
            cancel_at_period_end=False,
            last_payment_at=now,
            last_payment_id=payment.id,
        )
        db.add(sub)

    await db.commit()

    return {
        "success": True,
        "payment_id": request.razorpay_payment_id,
        "subscription_id": str(sub.id),
        "plan": request.plan,
        "current_period_end": period_end.isoformat(),
        "message": "Payment verified and subscription activated",
    }


# ─── Stripe Webhook ────────────────────────────────────────────────────

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Stripe webhooks.

    MUST respond within 3 seconds. Heavy processing is deferred to Celery.
    """
    from app.models.subscription import Subscription, PlanTier, SubscriptionStatus
    from app.models.payment import Payment, PaymentProvider, PaymentStatus, PaymentType
    from app.models.organization import OrganizationMember

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
                    org_result = await db.execute(
                        select(OrganizationMember).where(
                            OrganizationMember.user_id == user.id,
                        ).limit(1)
                    )
                    membership = org_result.scalar_one_or_none()
                    if membership:
                        sub_result = await db.execute(
                            select(Subscription).where(
                                Subscription.organization_id == membership.organization_id,
                            ).order_by(Subscription.created_at.desc()).limit(1)
                        )
                        sub = sub_result.scalar_one_or_none()
                        if sub:
                            sub.stripe_subscription_id = subscription_id
                            sub.status = SubscriptionStatus.ACTIVE.value
                            sub.last_payment_at = datetime.now(timezone.utc)

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
                    sub.status = SubscriptionStatus.ACTIVE.value
                    sub.dunning_attempts = 0
                    sub.last_payment_at = datetime.now(timezone.utc)

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
                    sub.status = SubscriptionStatus.PAST_DUE.value
                    sub.dunning_attempts += 1

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
                    sub.status = SubscriptionStatus.CANCELED.value
                    sub.cancelled_at = datetime.now(timezone.utc)

        # Record the event (inside same transaction)
        await guard.record_event(db, "stripe", event["id"], event_type, event)

    logger.info(f"Stripe webhook processed: {event_type}")
    return {"status": "success"}


# ─── Razorpay Webhook ──────────────────────────────────────────────────

@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Razorpay webhooks with signature verification and idempotency."""
    from app.models.subscription import Subscription, SubscriptionStatus
    from app.models.payment import Payment, PaymentProvider, PaymentStatus, PaymentType

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
                org_result = await db.execute(
                    select(OrganizationMember).where(
                        OrganizationMember.user_id == user_id,
                    ).limit(1)
                )
                membership = org_result.scalar_one_or_none()
                if membership:
                    sub_result = await db.execute(
                        select(Subscription).where(
                            Subscription.organization_id == membership.organization_id,
                        ).order_by(Subscription.created_at.desc()).limit(1)
                    )
                    sub = sub_result.scalar_one_or_none()
                    if sub:
                        sub.status = SubscriptionStatus.ACTIVE.value
                        sub.last_payment_at = datetime.now(timezone.utc)
                        sub.provider = "razorpay"
                        sub.razorpay_subscription_id = notes.get("subscription_id")

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
                org_result = await db.execute(
                    select(OrganizationMember).where(
                        OrganizationMember.user_id == user_id,
                    ).limit(1)
                )
                membership = org_result.scalar_one_or_none()
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
                sub.last_payment_at = datetime.now(timezone.utc)

        # Record the event (inside same transaction)
        await guard.record_event(db, "razorpay", event_id, event_type, event)

    logger.info(f"Razorpay webhook processed: {event_type}")
    return {"status": "success"}


# ─── Subscription ──────────────────────────────────────────────────────

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current subscription for user."""
    if not current_user:
        return _free_plan_response("anonymous")

    # Check DB for active subscription (subscriptions are org-based)
    from app.models.subscription import Subscription
    from app.models.organization import OrganizationMember

    # Get user's org
    org_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == current_user.id,
        ).limit(1)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        return _free_plan_response(str(current_user.id))

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

    return {
        "id": str(sub.id),
        "user_id": str(current_user.id),
        "plan": sub.plan.value if hasattr(sub.plan, "value") else str(sub.plan),
        "status": sub.status,
        "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else "",
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
        "scans_this_period": sub.scans_this_period,
        "repositories_count": sub.repositories_count,
        "team_members_count": getattr(sub, "team_members_count", 1),
        "features": _plan_features(sub.plan),
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
    from app.models.subscription import Subscription, PlanTier
    from app.models.organization import OrganizationMember
    from app.models.payment import Plan
    from datetime import datetime, timezone, timedelta
    from app.config import settings

    # Get user's org
    org_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == current_user.id,
        ).limit(1)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="No organization found")

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

    # Determine plan tier (map frontend names to DB enum values)
    plan_map = {
        "free": PlanTier.FREE,
        "plus": PlanTier.PRO,      # DB doesn't have PLUS, use PRO
        "pro": PlanTier.PRO,
        "enterprise": PlanTier.ENTERPRISE,
    }
    plan_tier = plan_map.get(request.plan.lower(), PlanTier.FREE)

    now = datetime.now(timezone.utc)
    billing_interval = getattr(request, "billing", "monthly")
    period_end = now + timedelta(days=30 if billing_interval == "monthly" else 365)

    if sub:
        # Update existing subscription
        sub.plan = plan_tier
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
            status="ACTIVE",
            billing_interval=billing_interval,
            current_period_start=now,
            current_period_end=period_end,
            cancel_at_period_end=False,
        )
        db.add(sub)

    await db.commit()

    return {
        "message": "Subscription activated successfully",
        "plan": request.plan,
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
    from app.models.organization import OrganizationMember

    # Get user's org
    org_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == current_user.id,
        ).limit(1)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="No organization found")

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
    sub.cancelled_at = datetime.now(timezone.utc)
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
    current_user: Optional[User] = Depends(get_optional_user),
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
        "current_period_start": datetime.now(timezone.utc).isoformat(),
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
    plan_name = plan.value if hasattr(plan, "value") else str(plan)
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
