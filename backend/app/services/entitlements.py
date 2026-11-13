"""
Centralized entitlement resolution for subscription and Beta access mode.

All feature gating should consult ``resolve_user_entitlements`` (or helpers below)
rather than reading ``user.subscription_plan`` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.models.subscription import PlanTier
from app.models.user import User
from app.services.pricing import get_plan_features, get_plan_ui_features


@dataclass(frozen=True)
class UserEntitlements:
    """Effective capabilities for a user (or anonymous) session."""

    beta_access_mode: bool
    beta_entitlements_active: bool
    billing_plan: str
    plan_tier: PlanTier
    features: dict[str, Any]
    ui_features: dict[str, Any]
    checkout_enabled: bool
    show_upgrade_prompts: bool
    limits: dict[str, Any]


def is_beta_access_mode_enabled() -> bool:
    return bool(settings.BETA_ACCESS_MODE)


def is_checkout_enabled() -> bool:
    return not is_beta_access_mode_enabled()


def plan_tier_from_billing_label(plan_name: str | None) -> PlanTier:
    normalized = (plan_name or "free").strip().lower()
    if normalized == "enterprise":
        return PlanTier.ENTERPRISE
    if normalized in {"plus", "pro"}:
        return PlanTier.PRO
    return PlanTier.FREE


def _beta_feature_overrides() -> dict[str, Any]:
    """Beta capabilities: Pro-like product access with configurable numeric limits."""
    base = get_plan_features(PlanTier.PRO).copy()
    base.update(
        {
            "max_scans_per_month": settings.BETA_MAX_SCANS_PER_MONTH,
            "max_repositories": settings.BETA_MAX_REPOSITORIES,
            "max_reports_per_month": settings.BETA_MAX_REPORTS_PER_MONTH,
            "max_concurrent_scans": settings.BETA_MAX_CONCURRENT_SCANS,
            "max_ai_requests_per_month": settings.BETA_MAX_AI_REQUESTS_PER_MONTH,
            "max_ai_tokens_per_month": settings.BETA_MAX_AI_TOKENS_PER_MONTH,
            "max_remediation_per_month": settings.BETA_MAX_REMEDIATION_PER_MONTH,
            "ai_suggestions": True,
            "ai_suggestions_blurred": False,
            "ai_code_fixes": True,
            "export_json": True,
            "export_pdf": True,
            "export_excel": True,
            "export_sarif": True,
            "download_patch": True,
            "github_pr_automation": True,
            "github_app_integration": True,
            "cicd_integration": True,
            "api_access": True,
            "api_rate_limit": settings.BETA_API_RATE_LIMIT_PER_HOUR,
        }
    )
    return base


def _beta_ui_features() -> dict[str, Any]:
    ui = get_plan_ui_features(PlanTier.PRO).copy()
    ui["blur_ai_code"] = False
    ui["show_upgrade_prompt"] = False
    return ui


def _limits_from_features(features: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "max_scans_per_month",
        "max_repositories",
        "max_reports_per_month",
        "max_concurrent_scans",
        "max_ai_requests_per_month",
        "max_ai_tokens_per_month",
        "max_remediation_per_month",
    )
    return {k: features.get(k) for k in keys if k in features}


def resolve_user_entitlements(
    user: User | None,
    *,
    plan_tier: PlanTier | None = None,
) -> UserEntitlements:
    """
    Resolve effective entitlements.

    When Beta access mode is on, authenticated users receive Beta entitlements
    regardless of stored subscription_plan (webhooks may still update billing state).
    """
    beta_mode = is_beta_access_mode_enabled()
    billing_plan = (getattr(user, "subscription_plan", None) or "free") if user else "free"
    tier = plan_tier or plan_tier_from_billing_label(billing_plan)
    beta_active = beta_mode and user is not None

    if beta_active:
        features = _beta_feature_overrides()
        ui = _beta_ui_features()
    else:
        features = get_plan_features(tier)
        ui = get_plan_ui_features(tier)

    return UserEntitlements(
        beta_access_mode=beta_mode,
        beta_entitlements_active=beta_active,
        billing_plan=billing_plan,
        plan_tier=tier,
        features=features,
        ui_features=ui,
        checkout_enabled=is_checkout_enabled(),
        show_upgrade_prompts=bool(ui.get("show_upgrade_prompt", False)),
        limits=_limits_from_features(features),
    )


def effective_can_use_feature(entitlements: UserEntitlements, feature: str) -> bool:
    value = entitlements.features.get(feature, False)
    if value == -1:
        return True
    return bool(value)


def effective_plan_tier_for_gating(entitlements: UserEntitlements) -> PlanTier:
    """Plan tier used for minimum-plan hierarchy checks."""
    if entitlements.beta_entitlements_active:
        return PlanTier.PRO
    return entitlements.plan_tier


def product_config_payload() -> dict[str, Any]:
    """Public product configuration (no secrets)."""
    beta = is_beta_access_mode_enabled()
    return {
        "beta_access_mode": beta,
        "checkout_enabled": is_checkout_enabled(),
        "show_upgrade_prompts": not beta,
        "beta_label": "Beta — Free Access" if beta else None,
        "limits": _limits_from_features(_beta_feature_overrides()) if beta else None,
    }


def subscription_features_payload(user: User | None, *, plan_name: str | None = None) -> dict[str, Any]:
    """Feature map for billing/subscription API responses."""
    tier = plan_tier_from_billing_label(plan_name or (getattr(user, "subscription_plan", None) if user else "free"))
    ent = resolve_user_entitlements(user, plan_tier=tier)
    payload = dict(ent.features)
    payload["beta_access_mode"] = ent.beta_access_mode
    payload["beta_entitlements_active"] = ent.beta_entitlements_active
    payload["checkout_enabled"] = ent.checkout_enabled
    payload["show_upgrade_prompts"] = ent.show_upgrade_prompts
    return payload
