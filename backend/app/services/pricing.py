"""
Pricing Plans Configuration

Defines features, limits, and pricing for each subscription tier.
"""

from typing import Any

from app.models.subscription import Currency, PlanTier

# =============================================================================
# PRICING CONFIGURATION
# =============================================================================

PRICING: dict[PlanTier, dict[str, Any]] = {
    PlanTier.FREE: {
        "name": "Free",
        "description": "Perfect for getting started",
        "monthly_price": {
            Currency.USD: 0,
            Currency.INR: 0,
            Currency.EUR: 0,
            Currency.GBP: 0,
            Currency.SGD: 0,
            Currency.AUD: 0,
        },
        "features": {
            # Scan limits
            "max_scans_per_month": 3,
            "max_repositories": 1,
            "max_reports_per_month": 0,

            # AI features
            "ai_suggestions": False,
            "ai_suggestions_blurred": True,
            "ai_code_fixes": False,

            # Export features
            "export_json": False,
            "export_pdf": False,
            "export_excel": False,
            "export_sarif": False,
            "download_patch": False,

            # GitHub integration
            "github_pr_automation": False,
            "github_app_integration": False,

            # Team features
            "team_members": 1,
            "team_collaboration": False,
            "organization_scanning": False,

            # CI/CD
            "cicd_integration": False,
            "cicd_automation": False,

            # Compliance
            "compliance_reporting": False,
            "custom_rules": False,

            # API access
            "api_access": False,
            "api_rate_limit": 0,

            # Support
            "priority_support": False,
            "dedicated_support": False,
            "sla_guarantee": False,
        },
        "ui_features": {
            "show_security_score": True,
            "show_issue_titles": True,
            "show_issue_descriptions": True,
            "show_severity_counts": True,
            "show_detected_technologies": True,
            "blur_ai_code": True,
            "show_upgrade_prompt": True,
        },
    },

    PlanTier.PLUS: {
        "name": "Plus",
        "description": "For individual developers",
        "monthly_price": {
            Currency.USD: 12,
            Currency.INR: 999,
            Currency.EUR: 11,
            Currency.GBP: 10,
            Currency.SGD: 16,
            Currency.AUD: 18,
        },
        "features": {
            # Scan limits
            "max_scans_per_month": 50,
            "max_repositories": 5,
            "max_reports_per_month": 10,

            # AI features
            "ai_suggestions": True,
            "ai_suggestions_blurred": False,
            "ai_code_fixes": True,

            # Export features
            "export_json": True,
            "export_pdf": True,
            "export_excel": False,
            "export_sarif": False,
            "download_patch": False,

            # GitHub integration
            "github_pr_automation": False,
            "github_app_integration": False,

            # Team features
            "team_members": 1,
            "team_collaboration": False,
            "organization_scanning": False,

            # CI/CD
            "cicd_integration": False,
            "cicd_automation": False,

            # Compliance
            "compliance_reporting": False,
            "custom_rules": False,

            # API access
            "api_access": False,
            "api_rate_limit": 0,

            # Support
            "priority_support": False,
            "dedicated_support": False,
            "sla_guarantee": False,
        },
        "ui_features": {
            "show_security_score": True,
            "show_issue_titles": True,
            "show_issue_descriptions": True,
            "show_severity_counts": True,
            "show_detected_technologies": True,
            "blur_ai_code": False,
            "show_upgrade_prompt": False,
        },
    },

    PlanTier.PRO: {
        "name": "Pro",
        "description": "For professional DevOps engineers",
        "monthly_price": {
            Currency.USD: 29,
            Currency.INR: 2499,
            Currency.EUR: 26,
            Currency.GBP: 24,
            Currency.SGD: 39,
            Currency.AUD: 45,
        },
        "features": {
            # Scan limits
            "max_scans_per_month": -1,  # Unlimited
            "max_repositories": -1,  # Unlimited
            "max_reports_per_month": -1,  # Unlimited

            # AI features
            "ai_suggestions": True,
            "ai_suggestions_blurred": False,
            "ai_code_fixes": True,

            # Export features
            "export_json": True,
            "export_pdf": True,
            "export_excel": True,
            "export_sarif": True,
            "download_patch": True,

            # GitHub integration
            "github_pr_automation": False,
            "github_app_integration": True,

            # Team features
            "team_members": 3,
            "team_collaboration": True,
            "organization_scanning": False,

            # CI/CD
            "cicd_integration": True,
            "cicd_automation": False,

            # Compliance
            "compliance_reporting": False,
            "custom_rules": False,

            # API access
            "api_access": True,
            "api_rate_limit": 1000,  # requests per hour

            # Support
            "priority_support": True,
            "dedicated_support": False,
            "sla_guarantee": False,
        },
        "ui_features": {
            "show_security_score": True,
            "show_issue_titles": True,
            "show_issue_descriptions": True,
            "show_severity_counts": True,
            "show_detected_technologies": True,
            "blur_ai_code": False,
            "show_upgrade_prompt": False,
            "show_architecture_viz": True,
            "show_scan_history": True,
        },
    },

    PlanTier.ENTERPRISE: {
        "name": "Enterprise",
        "description": "For companies and teams",
        "monthly_price": {
            Currency.USD: 99,
            Currency.INR: 7999,
            Currency.EUR: 89,
            Currency.GBP: 79,
            Currency.SGD: 129,
            Currency.AUD: 149,
        },
        "features": {
            # Scan limits
            "max_scans_per_month": -1,  # Unlimited
            "max_repositories": -1,  # Unlimited
            "max_reports_per_month": -1,  # Unlimited

            # AI features
            "ai_suggestions": True,
            "ai_suggestions_blurred": False,
            "ai_code_fixes": True,
            "ai_pr_automation": True,

            # Export features
            "export_json": True,
            "export_pdf": True,
            "export_excel": True,
            "export_sarif": True,
            "download_patch": True,

            # GitHub integration
            "github_pr_automation": True,
            "github_app_integration": True,

            # Team features
            "team_members": -1,  # Unlimited
            "team_collaboration": True,
            "organization_scanning": True,

            # CI/CD
            "cicd_integration": True,
            "cicd_automation": True,

            # Compliance
            "compliance_reporting": True,
            "custom_rules": True,

            # API access
            "api_access": True,
            "api_rate_limit": 5000,  # requests per hour

            # Support
            "priority_support": True,
            "dedicated_support": True,
            "sla_guarantee": True,
        },
        "ui_features": {
            "show_security_score": True,
            "show_issue_titles": True,
            "show_issue_descriptions": True,
            "show_severity_counts": True,
            "show_detected_technologies": True,
            "blur_ai_code": False,
            "show_upgrade_prompt": False,
            "show_architecture_viz": True,
            "show_scan_history": True,
            "show_team_dashboard": True,
            "show_compliance_reports": True,
        },
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_plan_features(plan: PlanTier) -> dict[str, Any]:
    """Get all features for a specific plan."""
    return PRICING[plan]["features"].copy()


def get_plan_ui_features(plan: PlanTier) -> dict[str, Any]:
    """Get UI features for a specific plan."""
    return PRICING[plan]["ui_features"].copy()


def get_plan_price(plan: PlanTier, currency: Currency) -> int:
    """Get monthly price for a plan in specified currency."""
    return PRICING[plan]["monthly_price"].get(currency, 0)


def get_feature_limit(plan: PlanTier, feature: str) -> Any:
    """Get specific feature limit for a plan."""
    return PRICING[plan]["features"].get(feature, False)


def can_use_feature(plan: PlanTier, feature: str) -> bool:
    """Check if a plan has access to a specific feature."""
    return bool(get_feature_limit(plan, feature))


def has_unlimited_access(plan: PlanTier, feature: str) -> bool:
    """Check if a plan has unlimited access to a feature."""
    limit = get_feature_limit(plan, feature)
    return limit == -1


def is_feature_blurred(plan: PlanTier) -> bool:
    """Check if AI suggestions should be blurred for this plan."""
    return PRICING[plan]["ui_features"].get("blur_ai_code", False)


def should_show_upgrade_prompt(plan: PlanTier) -> bool:
    """Check if upgrade prompts should be shown."""
    return PRICING[plan]["ui_features"].get("show_upgrade_prompt", False)


def get_currency_for_country(country_code: str) -> Currency:
    """Get currency for a country code."""
    return COUNTRY_CURRENCY_MAP.get(country_code.upper(), DEFAULT_CURRENCY)


def format_price(amount: int, currency: Currency) -> str:
    """Format price with currency symbol."""
    symbols = {
        Currency.USD: "$",
        Currency.INR: "₹",
        Currency.EUR: "€",
        Currency.GBP: "£",
        Currency.SGD: "S$",
        Currency.AUD: "A$",
    }
    symbol = symbols.get(currency, "$")
    return f"{symbol}{amount}"


def get_all_plans_with_pricing(currency: Currency = DEFAULT_CURRENCY) -> list[dict[str, Any]]:
    """Get all plans with their pricing in specified currency."""
    plans = []
    for tier in PlanTier:
        plan_data = PRICING[tier].copy()
        plan_data["tier"] = tier.value
        plan_data["price"] = format_price(
            get_plan_price(tier, currency),
            currency
        )
        plan_data["raw_price"] = get_plan_price(tier, currency)
        plan_data["currency"] = currency.value
        plans.append(plan_data)
    return plans
