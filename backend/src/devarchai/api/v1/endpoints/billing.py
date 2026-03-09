"""Billing and subscription endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from devarchai.api.deps import get_db, get_current_user
from devarchai.models.user import User

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/subscription", response_model=dict)
async def get_subscription(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current subscription for organization."""
    # TODO: Implement Stripe integration
    return {
        "message": "Subscription get endpoint - to be implemented",
        "organization_id": org_id,
    }


@router.post("/subscription", response_model=dict)
async def create_subscription(
    org_id: str,
    plan: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update subscription."""
    # TODO: Implement Stripe integration
    return {
        "message": "Subscription create endpoint - to be implemented",
        "plan": plan,
    }


@router.get("/invoices", response_model=dict)
async def list_invoices(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List invoices for organization."""
    # TODO: Implement Stripe integration
    return {
        "message": "Invoices list endpoint - to be implemented",
    }


@router.get("/usage", response_model=dict)
async def get_usage(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current usage for organization."""
    # TODO: Implement
    return {
        "message": "Usage get endpoint - to be implemented",
    }


@router.post("/checkout", response_model=dict)
async def create_checkout_session(
    org_id: str,
    plan: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create Stripe checkout session."""
    # TODO: Implement Stripe integration
    return {
        "message": "Checkout session endpoint - to be implemented",
        "plan": plan,
    }
