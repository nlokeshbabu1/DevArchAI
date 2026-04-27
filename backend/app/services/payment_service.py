"""Unified payment service for gateway resolution and checkout creation."""

from app.services.payment_router import PaymentRouter


class PaymentService(PaymentRouter):
    """Production payment service.

    Inherits the existing payment router implementation to preserve Stripe
    behavior while exposing a stable service-layer abstraction for checkout
    orchestration.
    """

    pass
