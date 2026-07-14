"""Helpers for ensuring users have a usable personal organization."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import MembershipRole, Organization, OrganizationMember, PlanType
from app.models.user import User

logger = logging.getLogger(__name__)


def _slugify_org_name(name: str) -> str:
    """Create a URL-safe organization slug."""
    normalized = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return normalized[:100] or "workspace"


def _build_personal_org_name(user: User) -> str:
    """Build a readable default organization name for a user."""
    base_name = (
        (getattr(user, "full_name", None) or "").strip()
        or (getattr(user, "username", None) or "").strip()
        or "Personal"
    )
    if base_name.lower().endswith("workspace"):
        return base_name
    return f"{base_name}'s Workspace"


async def _generate_unique_org_slug(db: AsyncSession, base_slug: str) -> str:
    """Generate a unique organization slug."""
    slug = base_slug[:100] or "workspace"
    counter = 1

    while True:
        result = await db.execute(select(Organization.id).where(Organization.slug == slug).limit(1))
        if result.scalar_one_or_none() is None:
            return slug

        suffix = f"-{counter}"
        slug = f"{base_slug[: max(1, 100 - len(suffix))]}{suffix}"
        counter += 1


async def ensure_user_organization_membership(
    db: AsyncSession,
    user: User,
    organization_name: str | None = None,
) -> OrganizationMember:
    """Ensure the user has a current organization and membership."""
    now = datetime.now(UTC)

    if getattr(user, "current_org_id", None):
        membership_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == user.id,
                OrganizationMember.organization_id == user.current_org_id,
            ).limit(1)
        )
        membership = membership_result.scalar_one_or_none()
        if membership:
            return membership

        org_result = await db.execute(
            select(Organization).where(Organization.id == user.current_org_id).limit(1)
        )
        organization = org_result.scalar_one_or_none()
        if organization:
            membership = OrganizationMember(
                organization_id=organization.id,
                user_id=user.id,
                role=MembershipRole.OWNER,
                joined_at=now,
            )
            db.add(membership)
            await db.flush()
            logger.info(
                "Restored missing organization membership",
                extra={"user_id": str(user.id), "organization_id": str(organization.id)},
            )
            return membership

        user.current_org_id = None
        await db.flush()

    membership_result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.created_at.asc())
        .limit(1)
    )
    membership = membership_result.scalar_one_or_none()
    if membership:
        if user.current_org_id != membership.organization_id:
            user.current_org_id = membership.organization_id
            await db.flush()
        return membership

    resolved_name = (organization_name or "").strip() or _build_personal_org_name(user)
    slug = await _generate_unique_org_slug(db, _slugify_org_name(resolved_name))

    organization = Organization(
        name=resolved_name,
        slug=slug,
        plan=PlanType.FREE,
    )
    db.add(organization)
    await db.flush()

    membership = OrganizationMember(
        organization_id=organization.id,
        user_id=user.id,
        role=MembershipRole.OWNER,
        joined_at=now,
    )
    db.add(membership)

    user.current_org_id = organization.id
    await db.flush()

    logger.info(
        "Provisioned personal organization for user",
        extra={"user_id": str(user.id), "organization_id": str(organization.id), "slug": slug},
    )
    return membership

