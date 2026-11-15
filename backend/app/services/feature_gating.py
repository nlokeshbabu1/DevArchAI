"""
Feature gating middleware for AI remediation.

Determines what level of AI suggestions a user can see based on entitlements
(subscription plan or Beta access mode).
"""

from app.models.user import User
from app.services.entitlements import effective_can_use_feature, resolve_user_entitlements


class FeatureGatingService:
    """Service for determining feature access based on effective entitlements."""

    @staticmethod
    def _entitlements(user: User | None):
        return resolve_user_entitlements(user)

    @staticmethod
    def get_ai_suggestion_limit(user: User | None) -> tuple[bool, int]:
        """
        Get AI suggestion access level.

        Returns:
            Tuple of (show_all, preview_count)
        """
        if user is None:
            return (False, 0)

        ent = FeatureGatingService._entitlements(user)
        if effective_can_use_feature(ent, "ai_suggestions") and not ent.features.get(
            "ai_suggestions_blurred", False
        ):
            return (True, 0)

        if ent.features.get("ai_suggestions_blurred", False):
            return (False, 2)

        return (False, 0)

    @staticmethod
    def should_blur_suggestion(user: User | None, suggestion_index: int) -> bool:
        if user is None:
            return True

        show_all, preview_count = FeatureGatingService.get_ai_suggestion_limit(user)
        if show_all:
            return False
        if suggestion_index < preview_count:
            return False
        return True

    @staticmethod
    def get_upgrade_plan_for_user(user: User | None) -> str:
        ent = FeatureGatingService._entitlements(user)
        if ent.show_upgrade_prompts:
            if ent.billing_plan == "free":
                return "plus"
            if ent.billing_plan == "plus":
                return "pro"
            return "enterprise"
        return ent.billing_plan or "free"

    @staticmethod
    def can_copy_fix(user: User | None) -> bool:
        if user is None:
            return False
        ent = FeatureGatingService._entitlements(user)
        return effective_can_use_feature(ent, "ai_code_fixes") or effective_can_use_feature(
            ent, "download_patch"
        )

    @staticmethod
    def can_create_pr(user: User | None) -> bool:
        if user is None:
            return False
        ent = FeatureGatingService._entitlements(user)
        return effective_can_use_feature(ent, "github_pr_automation") or effective_can_use_feature(
            ent, "ai_pr_automation"
        )

    @staticmethod
    def can_export_report(user: User | None) -> bool:
        if user is None:
            return False
        ent = FeatureGatingService._entitlements(user)
        return any(
            effective_can_use_feature(ent, key)
            for key in ("export_json", "export_pdf", "export_excel", "export_sarif")
        )
