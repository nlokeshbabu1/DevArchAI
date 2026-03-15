"""Billing and subscription endpoints with mock implementation."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from devarchai.api.deps import get_current_user, get_db
from devarchai.models.organization import Organization, PlanType
from devarchai.models.user import User, OrganizationMember
from devarchai.models.subscription import Subscription, SubscriptionStatus
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/subscription", response_model=dict)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current subscription for organization."""
    # Get organization ID from user
    org_id = current_user.current_org_id
    
    if not org_id:
        # Return default free plan if no organization
        return {
            "id": None,
            "organization_id": None,
            "plan": "free",
            "status": "active",
            "current_period_start": None,
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
    
    # Verify membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )
    
    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == uuid.UUID(org_id))
    )
    organization = result.scalar_one_or_none()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    
    # Get subscription
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == uuid.UUID(org_id))
    )
    subscription = result.scalar_one_or_none()
    
    # Return subscription info
    if subscription:
        return {
            "id": str(subscription.id),
            "organization_id": str(organization.id),
            "plan": subscription.plan.value,
            "status": subscription.status.value,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
            "scans_this_period": subscription.scans_this_period,
            "repositories_count": subscription.repositories_count,
            "team_members_count": subscription.team_members_count,
        }
    else:
        # Return default free plan
        return {
            "id": None,
            "organization_id": str(organization.id),
            "plan": "free",
            "status": "active",
            "current_period_start": organization.created_at.isoformat() if organization.created_at else None,
            "current_period_end": None,
            "cancel_at_period_end": False,
            "trial_end": None,
            "scans_this_period": getattr(organization, 'scans_this_month', 0),
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
    plan: str,
    org_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update subscription."""
    # Get organization ID from user if not provided
    if not org_id:
        org_id = current_user.current_org_id
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID required",
        )
    
    # Verify admin/owner access
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_(["owner", "admin"]),
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner access required",
        )
    
    # Validate plan
    try:
        plan_type = PlanType(plan.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan. Must be one of: free, pro, enterprise",
        )
    
    # Get or create subscription
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == uuid.UUID(org_id))
    )
    subscription = result.scalar_one_or_none()
    
    if subscription:
        # Update existing subscription
        subscription.plan = plan_type
        subscription.status = SubscriptionStatus.ACTIVE
    else:
        # Create new subscription
        subscription = Subscription(
            organization_id=uuid.UUID(org_id),
            plan=plan_type,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=None,  # Would be set by Stripe in production
        )
        db.add(subscription)
    
    # Update organization plan
    result = await db.execute(
        select(Organization).where(Organization.id == uuid.UUID(org_id))
    )
    organization = result.scalar_one_or_none()
    
    if organization:
        organization.plan = plan_type
    
    await db.commit()
    
    return {
        "message": "Subscription updated successfully",
        "plan": plan_type.value,
        "status": "active",
    }


@router.get("/invoices", response_model=dict)
async def list_invoices(
    org_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List invoices for organization."""
    # Get organization ID from user if not provided
    if not org_id:
        org_id = current_user.current_org_id
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID required",
        )
    
    # Verify membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )
    
    # Return mock invoices (in production, fetch from Stripe)
    return {
        "invoices": [
            {
                "id": "inv_001",
                "amount": 2900,
                "currency": "usd",
                "status": "paid",
                "created_at": "2024-01-01T00:00:00Z",
                "pdf_url": "/api/v1/billing/invoices/inv_001/pdf",
            }
        ],
        "has_more": False,
    }


@router.get("/usage", response_model=dict)
async def get_usage(
    org_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current usage for organization."""
    # Get organization ID from user if not provided
    if not org_id:
        org_id = current_user.current_org_id
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID required",
        )
    
    # Verify membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )
    
    # Get subscription
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == uuid.UUID(org_id))
    )
    subscription = result.scalar_one_or_none()
    
    # Get plan limits
    plan = subscription.plan.value if subscription else "free"
    limits = {
        "free": {"max_repositories": 5, "max_scans_per_month": 10},
        "pro": {"max_repositories": -1, "max_scans_per_month": -1},
        "enterprise": {"max_repositories": -1, "max_scans_per_month": -1},
    }
    
    plan_limits = limits.get(plan, limits["free"])
    
    return {
        "organization_id": org_id,
        "plan": plan,
        "current_period": {
            "start": subscription.current_period_start.isoformat() if subscription and subscription.current_period_start else None,
            "end": subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None,
        },
        "usage": {
            "scans_this_period": subscription.scans_this_period if subscription else 0,
            "repositories_count": subscription.repositories_count if subscription else 0,
            "team_members_count": subscription.team_members_count if subscription else 1,
        },
        "limits": {
            "max_scans_per_month": plan_limits["max_scans_per_month"],
            "max_repositories": plan_limits["max_repositories"],
        },
    }


@router.post("/checkout", response_model=dict)
async def create_checkout_session(
    plan: str,
    org_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe checkout session (mock implementation)."""
    # Get organization ID from user if not provided
    if not org_id:
        org_id = current_user.current_org_id
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID required",
        )
    
    # Verify admin/owner access
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_(["owner", "admin"]),
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner access required",
        )
    
    # In production, create Stripe checkout session here
    # For now, return mock session
    return {
        "checkout_url": f"https://checkout.stripe.com/mock/{plan}",
        "session_id": "mock_session_123",
        "plan": plan,
        "expires_at": "2024-12-31T23:59:59Z",
    }


@router.post("/cancel", response_model=dict)
async def cancel_subscription(
    org_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel subscription at end of billing period."""
    # Get organization ID from user if not provided
    if not org_id:
        org_id = current_user.current_org_id
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID required",
        )
    
    # Verify admin/owner access
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_(["owner", "admin"]),
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner access required",
        )
    
    # Get subscription
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == uuid.UUID(org_id))
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found",
        )
    
    # Mark for cancellation
    subscription.cancel_at_period_end = True
    subscription.canceled_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {
        "message": "Subscription will be cancelled at end of billing period",
        "cancel_at_period_end": True,
        "access_until": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
    }
