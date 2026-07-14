"""
Feature gating middleware for AI remediation.

Determines what level of AI suggestions a user can see based on their subscription plan.
"""


from app.models.user import User


class FeatureGatingService:
    """Service for determining feature access based on subscription plan."""

    @staticmethod
    def get_ai_suggestion_limit(user: User | None) -> tuple[bool, int]:
        """
        Get AI suggestion access level.
        
        Returns:
            Tuple of (show_all, preview_count)
            - show_all: If True, show all AI suggestions without blur
            - preview_count: Number of suggestions to show before blurring
        """
        if user is None:
            # Not logged in - no AI suggestions visible
            return (False, 0)

        plan = getattr(user, 'subscription_plan', 'free') or 'free'

        if plan == 'free':
            # Free users see first 2 suggestions as preview
            return (False, 2)
        elif plan in ['plus', 'pro', 'enterprise']:
            # Paid users see all suggestions
            return (True, 0)
        else:
            # Default to free tier
            return (False, 2)

    @staticmethod
    def should_blur_suggestion(user: User | None, suggestion_index: int) -> bool:
        """
        Determine if a specific AI suggestion should be blurred.
        
        Args:
            user: The current user (None if not authenticated)
            suggestion_index: 0-based index of the suggestion
            
        Returns:
            True if the suggestion should be blurred
        """
        show_all, preview_count = FeatureGatingService.get_ai_suggestion_limit(user)

        if show_all:
            return False

        if suggestion_index < preview_count:
            return False

        return True

    @staticmethod
    def get_upgrade_plan_for_user(user: User | None) -> str:
        """
        Get the recommended upgrade plan for a user.
        
        Returns:
            Plan name to suggest for upgrade
        """
        if user is None:
            return 'free'  # Suggest login/signup

        plan = getattr(user, 'subscription_plan', 'free') or 'free'

        if plan == 'free':
            return 'plus'
        elif plan == 'plus':
            return 'pro'
        else:
            return 'enterprise'

    @staticmethod
    def can_copy_fix(user: User | None) -> bool:
        """Check if user can copy AI fix code."""
        if user is None:
            return False

        plan = getattr(user, 'subscription_plan', 'free') or 'free'
        return plan in ['plus', 'pro', 'enterprise']

    @staticmethod
    def can_create_pr(user: User | None) -> bool:
        """Check if user can create GitHub PR from AI fix."""
        if user is None:
            return False

        plan = getattr(user, 'subscription_plan', 'free') or 'free'
        return plan in ['pro', 'enterprise']

    @staticmethod
    def can_export_report(user: User | None) -> bool:
        """Check if user can export reports."""
        if user is None:
            return False

        plan = getattr(user, 'subscription_plan', 'free') or 'free'
        return plan in ['plus', 'pro', 'enterprise']
