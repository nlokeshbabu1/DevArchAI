"""Repository management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from devarchai.api.deps import get_db, get_current_user
from devarchai.models.user import User
from devarchai.models.repository import Repository
from devarchai.models.organization import OrganizationMember, MembershipRole
from devarchai.core.exceptions import AuthorizationException

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.get("", response_model=List)
async def list_repositories(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List repositories for an organization."""
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
        select(Repository).where(Repository.organization_id == uuid.UUID(org_id))
    )
    repositories = result.scalars().all()
    return repositories


@router.post("", response_model=dict)
async def create_repository(
    repo_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new repository."""
    # TODO: Implement repository creation
    return {"message": "Repository creation endpoint - to be implemented"}


@router.get("/{repo_id}", response_model=dict)
async def get_repository(
    repo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get repository by ID."""
    # TODO: Implement
    return {"message": "Repository get endpoint - to be implemented"}


@router.put("/{repo_id}", response_model=dict)
async def update_repository(
    repo_id: uuid.UUID,
    repo_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update repository."""
    # TODO: Implement
    return {"message": "Repository update endpoint - to be implemented"}


@router.delete("/{repo_id}", response_model=dict)
async def delete_repository(
    repo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete repository."""
    # TODO: Implement
    return {"message": "Repository delete endpoint - to be implemented"}


@router.post("/{repo_id}/sync", response_model=dict)
async def sync_repository(
    repo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync repository from source control."""
    # TODO: Implement
    return {"message": "Repository sync endpoint - to be implemented"}
