"""Payment routing service — determines which provider to use based on user geography."""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.payment import Plan
from app.models.subscription import Currency
from app.services.payment_clients import RazorpayClient, StripeClient

logger = logging.getLogger(__name__)

# Country → currency mapping (extends existing COUNTRY_CURRENCY_MAP)
COUNTRY_CURRENCY = {
    "IN": Currency.INR,
    "US": Currency.USD,
    "CA": Currency.USD,
    "GB": Currency.GBP,
    "DE": Currency.EUR,
    "FR": Currency.EUR,
    "IT": Currency.EUR,
    "ES": Currency.EUR,
    "NL": Currency.EUR,
    "SG": Currency.SGD,
    "AU": Currency.AUD,
    "JP": Currency.USD,
}

# Countries that MUST use Razorpay
RAZORPAY_COUNTRIES = {"IN"}
SUPPORTED_GATEWAYS = {"stripe", "razorpay"}


class PaymentRouter:
    """Routes payment requests to the correct provider based on user geography."""

    def __init__(self):
        self.stripe = StripeClient()
        self.razorpay = RazorpayClient()

    def resolve_provider(self, user_country: str | None) -> str:
        """Determine payment provider for user based on country."""
        country = (user_country or "").upper()
        if country in RAZORPAY_COUNTRIES:
            return "razorpay"
        return "stripe"

    def get_payment_gateway(self, user) -> str:
        """Resolve payment gateway from user billing fields with safe fallback."""
        country = (getattr(user, "selected_country", None) or getattr(user, "country", None) or "US").upper()
        if country == "IN":
            return "razorpay"
        return "stripe"

    def resolve_currency(self, user_country: str | None) -> Currency:
        """Resolve currency from country code."""
        country = (user_country or "US").upper()
        return COUNTRY_CURRENCY.get(country, Currency.USD)

    def get_plan_price(self, plan: Plan, currency: Currency) -> int:
        """Get plan price in smallest currency unit (cents/paise)."""
        price_map = {
            Currency.USD: plan.price_usd,
            Currency.INR: plan.price_inr,
            Currency.EUR: plan.price_eur,
            Currency.GBP: plan.price_gbp,
        }
        return price_map.get(currency, plan.price_usd)

    def _build_razorpay_receipt(self, user, plan: Plan) -> str:
        """Build a Razorpay-safe receipt string with max length 40."""
        receipt = f"user_{user.id}_{plan.name}"[:40]
        if len(receipt) > 40:
            raise ValueError("Razorpay receipt exceeds 40 characters")
        return receipt

    async def create_checkout(
        self,
        db: AsyncSession,
        user,
        plan_name: str,
        billing_interval: str,
        user_country: str | None = None,
        coupon_code: str | None = None,
        selected_gateway: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a checkout session/order with the appropriate provider.

        Returns provider-specific checkout data for the frontend.
        """
        resolved_country = (user_country or getattr(user, "selected_country", None) or getattr(user, "country", None) or "US").upper()
        provider = (selected_gateway or self.get_payment_gateway(user)).lower()
        if provider not in SUPPORTED_GATEWAYS:
            raise ValueError("Invalid payment gateway selection")
        currency = self.resolve_currency(resolved_country)

        logger.info(
            "Resolved payment gateway",
            extra={
                "user_id": str(getattr(user, "id", "")),
                "country": resolved_country,
                "selected_gateway": provider,
            },
        )

        # Fetch plan from DB
        result = await db.execute(
            select(Plan).where(
                Plan.name == plan_name,
                Plan.interval == billing_interval,
                Plan.is_active == True,
            )
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise ValueError(f"Plan '{plan_name}' ({billing_interval}) not found")

        amount = self.get_plan_price(plan, currency)
        frontend_url = settings.FRONTEND_URL.rstrip("/")

        if provider == "razorpay":
            logger.info(
                "Creating checkout provider",
                extra={
                    "user_id": str(getattr(user, "id", "")),
                    "provider": "razorpay",
                    "country": resolved_country,
                },
            )
            return await self._create_razorpay_order(
                user=user,
                plan=plan,
                amount=amount,
                currency=Currency.INR.value,
                billing_interval=billing_interval,
                frontend_url=frontend_url,
                country=resolved_country,
            )

        logger.info(
            "Creating checkout provider",
            extra={
                "user_id": str(getattr(user, "id", "")),
                "provider": "stripe",
                "country": resolved_country,
            },
        )
        return await self._create_stripe_session(
            user=user,
            plan=plan,
            amount=amount,
            currency=currency.value,
            billing_interval=billing_interval,
            frontend_url=frontend_url,
            country=resolved_country,
        )

    async def _create_razorpay_order(
        self,
        user,
        plan: Plan,
        amount: int,
        currency: str,
        billing_interval: str,
        frontend_url: str,
        country: str | None = None,
    ) -> dict[str, Any]:
        """Create Razorpay order for one-time or subscription payment."""
        receipt = self._build_razorpay_receipt(user, plan)
        if len(receipt) > 40:
            raise ValueError("Razorpay receipt exceeds 40 characters")
        notes = {
            "user_id": str(user.id),
            "plan": plan.name,
            "interval": billing_interval,
        }
        result = await self.razorpay.create_order(
            amount=amount,
            currency=currency,
            receipt=receipt,
            notes=notes,
        )
        return {
            "gateway": "razorpay",
            **result,
            "plan": plan.name,
            "billing_interval": billing_interval,
            "trial_days": plan.trial_days,
            "country": (country or "US").upper(),
        }

    async def _create_stripe_session(
        self,
        user,
        plan: Plan,
        amount: int,
        currency: str,
        billing_interval: str,
        frontend_url: str,
        country: str | None = None,
    ) -> dict[str, Any]:
        """Create Stripe Checkout session."""
        price_id = (
            plan.stripe_price_id_yearly
            if billing_interval == "yearly"
            else plan.stripe_price_id_monthly
        )
        if not price_id:
            # Check if Stripe is configured at all
            stripe_configured = bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY != "sk_test_xxx")
            
            if stripe_configured:
                # Stripe keys are set but plan price IDs are missing - this is an error
                raise ValueError(
                    f"Stripe is configured but price ID not set for plan '{plan.name}' ({billing_interval}). "
                    f"Please add stripe_price_id_{billing_interval} in the plans table. "
                    f"Create products at: https://dashboard.stripe.com/products"
                )
            else:
                # Stripe not configured - use mock mode for development/testing
                logger.warning(
                    f"Stripe not configured, using mock checkout for plan '{plan.name}' ({billing_interval})"
                )
                session_id = f"dev_session_{plan.name}_{billing_interval}_{user.id}"
                return {
                    "session_url": f"{frontend_url}/billing/success?session_id={session_id}&plan={plan.name}&mock=true",
                    "session_id": session_id,
                    "gateway": "stripe",
                    "plan": plan.name,
                    "billing_interval": billing_interval,
                    "amount": amount,
                    "currency": currency,
                    "mock": True,
                    "country": (country or "US").upper(),
                }

        success_url = f"{frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_url}/billing/cancel"

        logger.info(
            f"Creating Stripe checkout session: "
            f"plan={plan.name}, interval={billing_interval}, price_id={price_id}"
        )

        result = await self.stripe.create_checkout_session(
            customer_email=user.email if hasattr(user, "email") else None,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            trial_days=plan.trial_days,
            metadata={
                "user_id": str(getattr(user, "id", "")),
                "plan": plan.name,
                "billing_interval": billing_interval,
                "gateway": "stripe",
                "country": (country or "US").upper(),
            },
        )
        return {
            "gateway": "stripe",
            **result,
            "plan": plan.name,
            "billing_interval": billing_interval,
            "amount": amount,
            "currency": currency,
            "country": (country or "US").upper(),
        }
