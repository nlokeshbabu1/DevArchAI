"""Reports management endpoints."""

import uuid

from devarchai.api.deps import get_current_user, get_db
from devarchai.core.exceptions import AuthorizationException
from devarchai.models.user import OrganizationMember
from devarchai.models.report import Report
from devarchai.models.user import User
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=list)
async def list_reports(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List reports for an organization."""
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

    result = await db.execute(
        select(Report).where(Report.organization_id == uuid.UUID(org_id))
    )
    reports = result.scalars().all()
    return reports


@router.get("/{report_id}", response_model=dict)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get report by ID."""
    # TODO: Implement
    return {"message": "Report get endpoint - to be implemented"}


@router.get("/{report_id}/download", response_model=dict)
async def download_report(
    report_id: uuid.UUID,
    format: str = "json",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download report in specified format."""
    # TODO: Implement
    return {"message": f"Report download endpoint - to be implemented ({format})"}


@router.post("/{report_id}/share", response_model=dict)
async def share_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate shareable link for report."""
    # TODO: Implement
    return {"message": "Report share endpoint - to be implemented"}
