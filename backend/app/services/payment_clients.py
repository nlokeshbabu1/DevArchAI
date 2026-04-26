"""Payment provider clients."""

import hashlib
import hmac
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class StripeClient:
    """Stripe payment provider client."""

    def __init__(self):
        self._client = None

    def _get_stripe(self):
        """Lazy import and configure stripe."""
        if self._client is None:
            import stripe as stripe_lib
            stripe_lib.api_key = settings.STRIPE_SECRET_KEY
            self._client = stripe_lib
        return self._client

    async def create_checkout_session(
        self,
        customer_email: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        coupon_id: str | None = None,
        trial_days: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a Stripe Checkout session."""
        stripe = self._get_stripe()
        session_params: dict[str, Any] = {
            "mode": "subscription",
            "customer_email": customer_email,
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"source": "devarchai", **(metadata or {})},
        }
        if coupon_id:
            session_params["discounts"] = [{"coupon": coupon_id}]
        if trial_days > 0:
            session_params["subscription_data"] = {"trial_period_days": trial_days}

        session = stripe.checkout.Session.create(**session_params)
        return {
            "session_url": session.url,
            "session_id": session.id,
            "gateway": "stripe",
        }

    async def create_customer(self, email: str, name: str | None = None) -> str:
        """Create a Stripe customer."""
        stripe = self._get_stripe()
        customer = stripe.Customer.create(email=email, name=name)
        return customer.id

    def verify_webhook(self, payload: bytes, sig_header: str) -> dict[str, Any] | None:
        """Verify and parse a Stripe webhook event."""
        stripe = self._get_stripe()
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET or settings.STRIPE_WEBHOOK_SECRET_TEST
        if not webhook_secret:
            logger.error("Stripe webhook secret not configured")
            return None
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            return event.to_dict()
        except ValueError:
            logger.error("Invalid Stripe webhook payload")
            return None
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid Stripe webhook signature")
            return None


class RazorpayClient:
    """Razorpay payment provider client."""

    def __init__(self):
        self._client = None

    def _get_razorpay(self):
        """Lazy import and configure razorpay."""
        if self._client is None:
            import razorpay as razorpay_lib
            self._client = razorpay_lib.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        return self._client

    async def create_order(
        self,
        amount: int,
        currency: str,
        receipt: str,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a Razorpay order."""
        rzp = self._get_razorpay()
        order = rzp.order.create({
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "notes": notes or {},
        })
        return {
            "order_id": order["id"],
            "key": settings.RAZORPAY_KEY_ID,
            "amount": order["amount"],
            "currency": order["currency"],
            "gateway": "razorpay",
        }

    async def fetch_order(self, order_id: str) -> dict[str, Any]:
        """Fetch an existing Razorpay order."""
        rzp = self._get_razorpay()
        return rzp.order.fetch(order_id)

    async def create_customer(self, email: str, name: str | None = None) -> str:
        """Create a Razorpay customer."""
        rzp = self._get_razorpay()
        customer = rzp.customer.create({
            "name": name or "",
            "email": email,
            "fail_existing": "0",
        })
        return customer["id"]

    async def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        total_count: int = 1,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a Razorpay subscription."""
        rzp = self._get_razorpay()
        sub = rzp.subscription.create({
            "plan_id": plan_id,
            "customer_id": customer_id,
            "total_count": total_count,
            "notes": notes or {},
        })
        return sub

    def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any] | None:
        """Verify and parse a Razorpay webhook event."""
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        if not webhook_secret:
            logger.error("Razorpay webhook secret not configured")
            return None
        expected = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            logger.error("Invalid Razorpay webhook signature")
            return None
        import json
        return json.loads(payload)

    def verify_payment_signature(
        self,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        razorpay_signature: str,
    ) -> bool:
        """Verify Razorpay payment signature after checkout using HMAC SHA256."""
        secret = settings.RAZORPAY_KEY_SECRET
        if not secret:
            logger.error("Razorpay key secret not configured")
            return False

        payload = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, razorpay_signature):
            logger.error("Razorpay signature verification failed")
            return False
        return True
