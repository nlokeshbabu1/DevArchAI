"""Unit tests for payment gateway routing behavior."""

from types import SimpleNamespace

import pytest

from app.api.v1.routes.billing import (
    RazorpayVerifyRequest,
    _detect_user_country,
    _normalize_gateway,
    _plan_features,
    _map_plan_name,
    _resolve_public_plan_name,
)
from app.models.subscription import PlanTier
from app.services.payment_router import PaymentRouter


class _Request:
    headers = {}


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDB:
    def __init__(self, value=None):
        self.value = value
        self.called = False

    async def execute(self, _statement):
        self.called = True
        return _ScalarResult(self.value)


def test_resolve_provider_routes_india_to_razorpay():
    router = PaymentRouter()
    assert router.resolve_provider("IN") == "razorpay"


def test_resolve_provider_routes_non_india_to_stripe():
    router = PaymentRouter()
    assert router.resolve_provider("US") == "stripe"
    assert router.resolve_provider("DE") == "stripe"


def test_detect_country_prefers_user_country_over_headers():
    user = SimpleNamespace(
        selected_country=None,
        country="IN",
    )
    request = _Request()

    assert _detect_user_country(user, request) == "IN"


def test_detect_country_falls_back_to_default_us_when_user_country_missing():
    user = SimpleNamespace(selected_country=None, country=None)
    request = _Request()

    assert _detect_user_country(user, request) == "US"


def test_detect_country_prefers_selected_country_over_user_country():
    user = SimpleNamespace(
        selected_country="DE",
        country="IN",
    )
    request = _Request()

    assert _detect_user_country(user, request) == "DE"


def test_detect_country_falls_back_to_default_us():
    user = SimpleNamespace(selected_country=None, country=None)
    request = _Request()

    assert _detect_user_country(user, request) == "US"


def test_get_payment_gateway_prefers_selected_country_india():
    user = SimpleNamespace(selected_country="IN", country="US")

    assert PaymentRouter().get_payment_gateway(user) == "razorpay"


def test_get_payment_gateway_falls_back_to_stripe():
    user = SimpleNamespace(selected_country=None, country=None)

    assert PaymentRouter().get_payment_gateway(user) == "stripe"


def test_normalize_gateway_supports_only_valid_values():
    assert _normalize_gateway("stripe") == "stripe"
    assert _normalize_gateway("RAZORPAY") == "razorpay"
    assert _normalize_gateway(" paypal ") is None


def test_map_plan_name_preserves_plus_tier():
    assert _map_plan_name("plus") == "plus"
    assert _map_plan_name("PLUS") == "plus"


def test_plan_features_handle_uppercase_subscription_enums():
    features = _plan_features(PlanTier.PRO)
    assert features["ai_suggestions"] is True
    assert features["api_access"] is True


def test_razorpay_verify_request_accepts_public_api_field_names():
    request = RazorpayVerifyRequest(
        payment_id="pay_123",
        order_id="order_123",
        signature="sig_123",
    )

    assert request.resolved_payment_id() == "pay_123"
    assert request.resolved_order_id() == "order_123"
    assert request.resolved_signature() == "sig_123"


def test_razorpay_verify_request_accepts_legacy_field_names():
    request = RazorpayVerifyRequest(
        razorpay_payment_id="pay_legacy",
        razorpay_order_id="order_legacy",
        razorpay_signature="sig_legacy",
    )

    assert request.resolved_payment_id() == "pay_legacy"
    assert request.resolved_order_id() == "order_legacy"
    assert request.resolved_signature() == "sig_legacy"


@pytest.mark.asyncio
async def test_resolve_public_plan_name_prefers_user_subscription_state():
    db = _FakeDB(value="pro")
    user = SimpleNamespace(subscription_plan="plus")
    subscription = SimpleNamespace(plan=PlanTier.PRO, plan_id=None)

    plan_name = await _resolve_public_plan_name(db, user, subscription)

    assert plan_name == "plus"
    assert db.called is False


@pytest.mark.asyncio
async def test_resolve_public_plan_name_falls_back_to_plan_record_name():
    db = _FakeDB(value="plus")
    user = SimpleNamespace(subscription_plan="free")
    subscription = SimpleNamespace(plan=PlanTier.PRO, plan_id="plan-123")

    plan_name = await _resolve_public_plan_name(db, user, subscription)

    assert plan_name == "plus"
    assert db.called is True
