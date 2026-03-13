"""Organization management endpoints."""

import uuid

from devarchai.api.deps import get_current_user, get_db
from devarchai.core.exceptions import AuthorizationException, OrganizationNotFoundException
from devarchai.models.organization import MembershipRole, Organization, OrganizationMember, PlanType
from devarchai.models.user import User
from devarchai.schemas.common import MessageResponse
from devarchai.schemas.organization import (
    MemberInvite,
    MemberResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/me", response_model=OrganizationResponse)
async def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's organization."""
    if not current_user.current_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization selected",
        )

    result = await db.execute(
        select(Organization).where(Organization.id == current_user.current_org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise OrganizationNotFoundException(current_user.current_org_id)

    return org


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all organizations the user is a member of."""
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
    )
    organizations = result.scalars().all()
    return organizations


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization."""
    # Generate unique slug
    slug = org_data.slug or org_data.name.lower().replace(" ", "-")[:100]
    counter = 1
    original_slug = slug

    while True:
        result = await db.execute(select(Organization).where(Organization.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{original_slug}-{counter}"
        counter += 1

    organization = Organization(
        name=org_data.name,
        slug=slug,
        description=org_data.description,
        plan=PlanType.FREE,
    )
    db.add(organization)
    await db.flush()

    # Create membership
    membership = OrganizationMember(
        organization_id=organization.id,
        user_id=current_user.id,
        role=MembershipRole.OWNER,
    )
    db.add(membership)

    # Update user's current org
    current_user.current_org_id = organization.id

    await db.commit()
    await db.refresh(organization)

    return organization


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get organization by ID."""
    # Verify membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise AuthorizationException()

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()

    if not org:
        raise OrganizationNotFoundException(org_id)

    return org


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: uuid.UUID,
    org_data: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update organization."""
    # Verify admin/owner access
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([MembershipRole.OWNER, MembershipRole.ADMIN]),
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise AuthorizationException()

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()

    if not org:
        raise OrganizationNotFoundException(org_id)

    # Update fields
    if org_data.name is not None:
        org.name = org_data.name
    if org_data.description is not None:
        org.description = org_data.description

    await db.commit()
    await db.refresh(org)

    return org


@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List organization members."""
    # Verify membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise AuthorizationException()

    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org_id)
        .join(User)
    )
    members = result.scalars().all()

    return [
        MemberResponse(
            id=m.id,
            user_id=m.user_id,
            email=m.user.email,
            username=m.user.username,
            full_name=m.user.full_name,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in members
    ]


@router.post("/{org_id}/members/invite", response_model=MessageResponse)
async def invite_member(
    org_id: uuid.UUID,
    invite_data: MemberInvite,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a member to the organization."""
    # Verify admin/owner access
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([MembershipRole.OWNER, MembershipRole.ADMIN]),
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise AuthorizationException()

    # TODO: Send invitation email
    # For now, just return success message

    return MessageResponse(message=f"Invitation sent to {invite_data.email}")


@router.delete("/{org_id}/members/{member_id}", response_model=MessageResponse)
async def remove_member(
    org_id: uuid.UUID,
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the organization."""
    # Verify admin/owner access
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([MembershipRole.OWNER, MembershipRole.ADMIN]),
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise AuthorizationException()

    # Delete membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.id == member_id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Cannot remove yourself
    if member.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from organization",
        )

    await db.delete(member)
    await db.commit()

    return MessageResponse(message="Member removed successfully")
