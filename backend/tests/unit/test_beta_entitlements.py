"""Tests for Beta access mode and centralized entitlements."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.models.subscription import PlanTier
from app.services.entitlements import (
    is_checkout_enabled,
    product_config_payload,
    resolve_user_entitlements,
)
from app.services.feature_gating import FeatureGatingService


@pytest.fixture
def free_user():
    return SimpleNamespace(id="user-1", subscription_plan="free", subscription_status="active")


@pytest.fixture
def pro_user():
    return SimpleNamespace(id="user-2", subscription_plan="pro", subscription_status="active")


class TestBetaAccessModeDisabled:
    def test_checkout_enabled_by_default(self):
        with patch("app.services.entitlements.settings") as mock_settings:
            mock_settings.BETA_ACCESS_MODE = False
            assert is_checkout_enabled() is True

    def test_free_user_ai_blurred(self, free_user):
        with patch("app.services.entitlements.settings") as mock_settings:
            mock_settings.BETA_ACCESS_MODE = False
            ent = resolve_user_entitlements(free_user)
            assert ent.beta_entitlements_active is False
            assert ent.features.get("ai_suggestions") is False
            assert FeatureGatingService.can_create_pr(free_user) is False
            assert FeatureGatingService.can_export_report(free_user) is False

    def test_free_user_preview_limit(self, free_user):
        with patch("app.services.entitlements.settings") as mock_settings:
            mock_settings.BETA_ACCESS_MODE = False
            show_all, preview = FeatureGatingService.get_ai_suggestion_limit(free_user)
            assert show_all is False
            assert preview == 2


class TestBetaAccessModeEnabled:
    @pytest.fixture(autouse=True)
    def _beta_settings(self):
        with patch("app.services.entitlements.settings") as mock_settings:
            mock_settings.BETA_ACCESS_MODE = True
            mock_settings.BETA_MAX_SCANS_PER_MONTH = 50
            mock_settings.BETA_MAX_REPOSITORIES = 10
            mock_settings.BETA_MAX_REPORTS_PER_MONTH = 50
            mock_settings.BETA_MAX_CONCURRENT_SCANS = 2
            mock_settings.BETA_MAX_AI_REQUESTS_PER_MONTH = 200
            mock_settings.BETA_MAX_AI_TOKENS_PER_MONTH = 500_000
            mock_settings.BETA_MAX_REMEDIATION_PER_MONTH = 50
            mock_settings.BETA_API_RATE_LIMIT_PER_HOUR = 1000
            yield mock_settings

    def test_checkout_disabled(self):
        assert is_checkout_enabled() is False

    def test_free_user_gets_beta_entitlements(self, free_user):
        ent = resolve_user_entitlements(free_user)
        assert ent.beta_entitlements_active is True
        assert ent.checkout_enabled is False
        assert ent.show_upgrade_prompts is False
        assert ent.features["ai_suggestions"] is True
        assert ent.features["max_scans_per_month"] == 50
        assert FeatureGatingService.can_create_pr(free_user) is True
        assert FeatureGatingService.can_export_report(free_user) is True
        show_all, preview = FeatureGatingService.get_ai_suggestion_limit(free_user)
        assert show_all is True
        assert preview == 0

    def test_anonymous_user_not_beta_entitled(self):
        ent = resolve_user_entitlements(None)
        assert ent.beta_entitlements_active is False

    def test_product_config_payload(self):
        payload = product_config_payload()
        assert payload["beta_access_mode"] is True
        assert payload["checkout_enabled"] is False
        assert payload["show_upgrade_prompts"] is False
        assert payload["beta_label"] == "Beta — Free Access"

    def test_paid_user_still_gets_beta_capabilities_during_beta(self, pro_user):
        ent = resolve_user_entitlements(pro_user)
        assert ent.billing_plan == "pro"
        assert ent.beta_entitlements_active is True
        assert ent.features["export_json"] is True


class TestCheckoutGuard:
    def test_raise_checkout_disabled(self):
        from app.services.usage_enforcement import raise_checkout_disabled

        with pytest.raises(HTTPException) as exc:
            raise_checkout_disabled()
        assert exc.value.status_code == 403
        assert exc.value.detail["error"] == "BETA_CHECKOUT_DISABLED"


class TestPricingIntegration:
    def test_can_use_feature_with_user_beta(self, free_user):
        from app.services.pricing import can_use_feature

        with patch("app.services.entitlements.settings") as mock_settings:
            mock_settings.BETA_ACCESS_MODE = True
            mock_settings.BETA_MAX_SCANS_PER_MONTH = 50
            mock_settings.BETA_MAX_REPOSITORIES = 10
            mock_settings.BETA_MAX_REPORTS_PER_MONTH = 50
            mock_settings.BETA_MAX_CONCURRENT_SCANS = 2
            mock_settings.BETA_MAX_AI_REQUESTS_PER_MONTH = 200
            mock_settings.BETA_MAX_AI_TOKENS_PER_MONTH = 500_000
            mock_settings.BETA_MAX_REMEDIATION_PER_MONTH = 50
            mock_settings.BETA_API_RATE_LIMIT_PER_HOUR = 1000
            assert can_use_feature(PlanTier.FREE, "export_json", user=free_user) is True
            assert can_use_feature(PlanTier.FREE, "export_json", user=None) is False
