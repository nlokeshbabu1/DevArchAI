"""
Feature Gating Middleware

Controls access to features based on subscription plan.
"""

from functools import wraps
from typing import Any, Callable, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.subscription import PlanTier, Subscription
from app.models.user import User
from app.services.pricing import (
    can_use_feature,
    get_plan_features,
    has_unlimited_access,
    is_feature_blurred,
)


async def get_user_subscription(
    current_user: User,
    db: AsyncSession = Depends(get_db),
) -> Optional[Subscription]:
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
            
            # Define plan hierarchy
            plan_hierarchy = {
                PlanTier.FREE: 0,
                PlanTier.PLUS: 1,
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
            
            if not can_use_feature(user_plan, feature):
                subscription = await get_user_subscription(current_user, db)
                plan_name = subscription.plan.value if subscription else "free"
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "FEATURE_NOT_AVAILABLE",
                        "message": f"This feature is not available in your current plan",
                        "feature": feature,
                        "current_plan": plan_name,
                        "upgrade_url": "/billing",
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
        from sqlalchemy import select, func as sql_func
        
        user_plan = await get_user_plan(current_user, db)
        max_scans = get_plan_features(user_plan).get("max_scans_per_month", 0)
        
        # Unlimited scans
        if max_scans == -1:
            return await func(current_user=current_user, db=db, *args, **kwargs)
        
        # Count scans this month
        from app.models.scan import Scan
        from datetime import datetime, timedelta
        
        first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = await db.execute(
            select(sql_func.count(Scan.id)).where(
                Scan.user_id == current_user.id,
                Scan.created_at >= first_of_month,
            )
        )
        scan_count = result.scalar() or 0
        
        if scan_count >= max_scans:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "SCAN_LIMIT_EXCEEDED",
                    "message": f"You've reached your monthly scan limit ({max_scans} scans)",
                    "current_usage": scan_count,
                    "limit": max_scans,
                    "reset_date": (datetime.now() + timedelta(days=30)).isoformat(),
                    "upgrade_url": "/billing",
                },
            )
        
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
        from sqlalchemy import select, func as sql_func
        
        user_plan = await get_user_plan(current_user, db)
        max_repos = get_plan_features(user_plan).get("max_repositories", 0)
        
        # Unlimited repositories
        if max_repos == -1:
            return await func(current_user=current_user, db=db, *args, **kwargs)
        
        # Count repositories
        from app.models.repository import Repository
        
        result = await db.execute(
            select(sql_func.count(Repository.id)).where(
                Repository.user_id == current_user.id,
            )
        )
        repo_count = result.scalar() or 0
        
        if repo_count >= max_repos:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "REPOSITORY_LIMIT_EXCEEDED",
                    "message": f"You've reached your repository limit ({max_repos} repositories)",
                    "current_usage": repo_count,
                    "limit": max_repos,
                    "upgrade_url": "/billing",
                },
            )
        
        return await func(current_user=current_user, db=db, *args, **kwargs)
    
    return wrapper


def should_blur_ai_suggestion(user_plan: PlanTier) -> bool:
    """Check if AI suggestion should be blurred for user's plan."""
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
