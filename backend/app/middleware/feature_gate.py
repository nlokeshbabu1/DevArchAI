"""
Feature Gating Middleware

Controls access to features based on subscription plan.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.subscription import PlanTier, Subscription
from app.models.user import User
from app.services.entitlements import (
    effective_can_use_feature,
    effective_plan_tier_for_gating,
    resolve_user_entitlements,
)
from app.services.pricing import is_feature_blurred


async def get_user_subscription(
    current_user: User,
    db: AsyncSession = Depends(get_db),
) -> Subscription | None:
    """Get user's current subscription."""
    from sqlalchemy import select

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    return result.scalar_one_or_none()


async def get_user_plan(
    current_user: User,
    db: AsyncSession = Depends(get_db),
) -> PlanTier:
    """Get user's current plan tier."""
    subscription = await get_user_subscription(current_user, db)
    if subscription and subscription.status == "active":
        return subscription.plan
    return PlanTier.FREE


def require_plan(minimum_plan: PlanTier):
    """
    Decorator to require minimum subscription plan for an endpoint.
    
    Usage:
        @router.get("/premium-feature")
        @require_plan(PlanTier.PRO)
        async def premium_feature():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
            *args,
            **kwargs,
        ):
            user_plan = await get_user_plan(current_user, db)
            entitlements = resolve_user_entitlements(current_user, plan_tier=user_plan)
            user_plan = effective_plan_tier_for_gating(entitlements)

            # Define plan hierarchy
            plan_hierarchy = {
                PlanTier.FREE: 0,
                PlanTier.PRO: 2,
                PlanTier.ENTERPRISE: 3,
            }

            if plan_hierarchy.get(user_plan, 0) < plan_hierarchy.get(minimum_plan, 0):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "INSUFFICIENT_PLAN",
                        "message": f"This feature requires {minimum_plan.value.capitalize()} plan or higher",
                        "current_plan": user_plan.value,
                        "required_plan": minimum_plan.value,
                        "upgrade_url": "/billing",
                    },
                )

            return await func(current_user=current_user, db=db, *args, **kwargs)

        return wrapper
    return decorator


def require_feature(feature: str):
    """
    Decorator to require specific feature access.
    
    Usage:
        @router.get("/ai-suggestions")
        @require_feature("ai_suggestions")
        async def get_ai_suggestions():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
            *args,
            **kwargs,
        ):
            user_plan = await get_user_plan(current_user, db)
            entitlements = resolve_user_entitlements(current_user, plan_tier=user_plan)

            if not effective_can_use_feature(entitlements, feature):
                subscription = await get_user_subscription(current_user, db)
                plan_name = subscription.plan.value if subscription else "free"

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "FEATURE_NOT_AVAILABLE",
                        "message": "This feature is not available in your current plan",
                        "feature": feature,
                        "current_plan": plan_name,
                        "upgrade_url": None if not entitlements.checkout_enabled else "/billing",
                        "beta_access_mode": entitlements.beta_access_mode,
                    },
                )

            return await func(current_user=current_user, db=db, *args, **kwargs)

        return wrapper
    return decorator


def check_scan_limit(func: Callable) -> Callable:
    """
    Decorator to check scan limit before allowing scan.
    
    Usage:
        @router.post("/scan")
        @check_scan_limit
        async def create_scan():
            ...
    """
    @wraps(func)
    async def wrapper(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        *args,
        **kwargs,
    ):
        from app.services.usage_enforcement import enforce_scan_monthly_limit

        await enforce_scan_monthly_limit(current_user, db)
        return await func(current_user=current_user, db=db, *args, **kwargs)

    return wrapper


def check_repository_limit(func: Callable) -> Callable:
    """
    Decorator to check repository limit.
    
    Usage:
        @router.post("/repositories")
        @check_repository_limit
        async def add_repository():
            ...
    """
    @wraps(func)
    async def wrapper(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        *args,
        **kwargs,
    ):
        from app.services.usage_enforcement import enforce_repository_limit

        await enforce_repository_limit(current_user, db)
        return await func(current_user=current_user, db=db, *args, **kwargs)

    return wrapper


def should_blur_ai_suggestion(user_plan: PlanTier, user: User | None = None) -> bool:
    """Check if AI suggestion should be blurred for user's plan."""
    if user is not None:
        ent = resolve_user_entitlements(user, plan_tier=user_plan)
        return bool(ent.ui_features.get("blur_ai_code", False))
    return is_feature_blurred(user_plan)


def get_ai_suggestion_with_gating(
    ai_suggestion: str,
    user_plan: PlanTier,
) -> dict[str, Any]:
    """
    Get AI suggestion with appropriate gating based on plan.
    
    Returns:
        dict with 'content', 'is_blurred', 'upgrade_required' keys
    """
    if should_blur_ai_suggestion(user_plan):
        return {
            "content": None,
            "blurred_content": "█" * len(ai_suggestion) if ai_suggestion else None,
            "is_blurred": True,
            "upgrade_required": True,
            "upgrade_message": "Upgrade to Plus to unlock AI remediation",
            "upgrade_plan": "plus",
        }

    return {
        "content": ai_suggestion,
        "blurred_content": None,
        "is_blurred": False,
        "upgrade_required": False,
        "upgrade_message": None,
        "upgrade_plan": None,
    }


# Import get_current_user for use in decorators
from app.core.security import get_current_user
