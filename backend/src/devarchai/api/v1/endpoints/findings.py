"""Findings management endpoints."""

import uuid
from typing import Optional

from devarchai.api.deps import get_current_user, get_db
from devarchai.core.exceptions import AuthorizationException
from devarchai.models.finding import Finding
from devarchai.models.organization import OrganizationMember
from devarchai.models.user import User
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/findings", tags=["Findings"])


@router.get("", response_model=list)
async def list_findings(
    org_id: str,
    scan_id: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List findings for an organization."""
    # Verify membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise AuthorizationException()

    query = select(Finding).where(Finding.organization_id == uuid.UUID(org_id))

    if scan_id:
        query = query.where(Finding.scan_id == uuid.UUID(scan_id))
    if severity:
        query = query.where(Finding.severity == severity)
    if category:
        query = query.where(Finding.category == category)
    if status:
        query = query.where(Finding.status == status)

    result = await db.execute(query)
    findings = result.scalars().all()
    return findings


@router.get("/{finding_id}", response_model=dict)
async def get_finding(
    finding_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get finding by ID."""
    # TODO: Implement
    return {"message": "Finding get endpoint - to be implemented"}


@router.put("/{finding_id}", response_model=dict)
async def update_finding(
    finding_id: uuid.UUID,
    finding_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update finding (e.g., change status)."""
    # TODO: Implement
    return {"message": "Finding update endpoint - to be implemented"}
