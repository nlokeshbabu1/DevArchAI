"""Billing and subscription endpoints."""

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, status, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import get_current_user, get_optional_user, create_access_token
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/billing", tags=["Billing"])


class CheckoutRequest(BaseModel):
    plan: str


class SubscriptionResponse(BaseModel):
    id: Optional[str]
    user_id: str
    plan: str
    status: str
    current_period_start: str
    current_period_end: Optional[str]
    cancel_at_period_end: bool
    trial_end: Optional[str]
    scans_this_period: int
    repositories_count: int
    team_members_count: int
    features: dict


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current subscription for user."""
    user_id = str(current_user.id) if current_user else "anonymous"
    
    # Return free plan for all users
    return {
        "id": None,
        "user_id": user_id,
        "plan": "free",
        "status": "active",
        "current_period_start": datetime.now(timezone.utc).isoformat(),
        "current_period_end": None,
        "cancel_at_period_end": False,
        "trial_end": None,
        "scans_this_period": 0,
        "repositories_count": 0,
        "team_members_count": 1,
        "features": {
            "max_repositories": 5,
            "max_scans_per_month": 10,
            "ai_suggestions": False,
            "api_access": False,
            "priority_support": False,
        }
    }


@router.post("/subscription", response_model=dict)
async def create_subscription(
    request: CheckoutRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update subscription."""
    # Mock implementation
    return {
        "message": "Subscription updated successfully",
        "plan": request.plan,
        "status": "active",
        "requires_login": current_user is None,
    }


@router.get("/invoices", response_model=dict)
async def list_invoices(
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """List invoices for user."""
    return {
        "invoices": [],
        "has_more": False,
    }


@router.get("/usage", response_model=dict)
async def get_usage(
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current usage for user."""
    user_id = str(current_user.id) if current_user else "anonymous"
    
    return {
        "user_id": user_id,
        "plan": "free",
        "usage": {
            "scans_this_period": 0,
            "repositories_count": 0,
            "team_members_count": 1,
        },
        "limits": {
            "max_scans_per_month": 10,
            "max_repositories": 5,
        },
    }


@router.post("/checkout", response_model=dict)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe checkout session (mock)."""
    user_id = str(current_user.id) if current_user else "anonymous"

    # Mock implementation - redirect to success page for development
    # In production, replace with actual Stripe checkout session creation
    frontend_url = settings.FRONTEND_URL.rstrip('/')
    return {
        "checkout_url": f"{frontend_url}/billing/success?session_id=mock_session_{request.plan}_{user_id}&plan={request.plan}",
        "session_id": f"mock_session_{request.plan}_{user_id}",
        "plan": request.plan,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "requires_login": current_user is None,
        "mock": True,
    }


@router.post("/cancel", response_model=dict)
async def cancel_subscription(
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel subscription."""
    return {
        "message": "Subscription cancelled",
        "cancel_at_period_end": True,
    }
