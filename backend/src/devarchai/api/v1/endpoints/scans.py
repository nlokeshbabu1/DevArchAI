"""Scan management endpoints."""

import uuid
from typing import Optional

from devarchai.api.deps import get_current_user, get_db
from devarchai.core.exceptions import AuthorizationException
from devarchai.models.organization import OrganizationMember
from devarchai.models.scan import Scan, ScanStatus
from devarchai.models.user import User
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/scans", tags=["Scans"])


@router.get("", response_model=list)
async def list_scans(
    org_id: str,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List scans for an organization."""
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

    query = select(Scan).where(Scan.organization_id == uuid.UUID(org_id))

    if status_filter:
        query = query.where(Scan.status == ScanStatus(status_filter))

    result = await db.execute(query)
    scans = result.scalars().all()
    return scans


@router.post("", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    scan_data: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scan."""
    # TODO: Implement scan creation with Celery
    return {
        "message": "Scan creation endpoint - to be implemented with Celery",
        "status": "queued",
    }


@router.get("/{scan_id}", response_model=dict)
async def get_scan(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get scan by ID."""
    # TODO: Implement
    return {"message": "Scan get endpoint - to be implemented"}


@router.post("/{scan_id}/cancel", response_model=dict)
async def cancel_scan(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running scan."""
    # TODO: Implement
    return {"message": "Scan cancel endpoint - to be implemented"}


@router.delete("/{scan_id}", response_model=dict)
async def delete_scan(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a scan."""
    # TODO: Implement
    return {"message": "Scan delete endpoint - to be implemented"}
