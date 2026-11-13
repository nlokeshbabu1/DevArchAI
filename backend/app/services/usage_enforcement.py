"""Server-side usage limit enforcement using centralized entitlements."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func as sql_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.services.entitlements import resolve_user_entitlements


def _limit_value(raw: object) -> int | None:
    if raw is None:
        return None
    if raw == -1:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


async def enforce_scan_monthly_limit(user: User, db: AsyncSession) -> None:
    entitlements = resolve_user_entitlements(user)
    max_scans = _limit_value(entitlements.features.get("max_scans_per_month"))
    if max_scans is None:
        return

    first_of_month = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(sql_func.count(Scan.id)).where(
            Scan.user_id == user.id,
            Scan.created_at >= first_of_month,
        )
    )
    scan_count = result.scalar() or 0
    if scan_count >= max_scans:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "SCAN_LIMIT_EXCEEDED",
                "message": f"Monthly scan limit reached ({max_scans} scans)",
                "current_usage": scan_count,
                "limit": max_scans,
                "beta_access_mode": entitlements.beta_access_mode,
            },
        )


async def enforce_concurrent_scan_limit(user: User, db: AsyncSession) -> None:
    entitlements = resolve_user_entitlements(user)
    max_concurrent = _limit_value(entitlements.features.get("max_concurrent_scans"))
    if max_concurrent is None:
        return

    result = await db.execute(
        select(sql_func.count(Scan.id)).where(
            Scan.user_id == user.id,
            Scan.status.in_([ScanStatus.PENDING, ScanStatus.PROCESSING, ScanStatus.QUEUED]),
        )
    )
    active = result.scalar() or 0
    if active >= max_concurrent:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "CONCURRENT_SCAN_LIMIT_EXCEEDED",
                "message": f"Concurrent scan limit reached ({max_concurrent})",
                "current_usage": active,
                "limit": max_concurrent,
                "beta_access_mode": entitlements.beta_access_mode,
            },
        )


async def enforce_repository_limit(user: User, db: AsyncSession) -> None:
    entitlements = resolve_user_entitlements(user)
    max_repos = _limit_value(entitlements.features.get("max_repositories"))
    if max_repos is None:
        return

    result = await db.execute(
        select(sql_func.count(Repository.id)).where(
            Repository.user_id == user.id,
            Repository.is_active.is_(True),
        )
    )
    repo_count = result.scalar() or 0
    if repo_count >= max_repos:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "REPOSITORY_LIMIT_EXCEEDED",
                "message": f"Repository limit reached ({max_repos})",
                "current_usage": repo_count,
                "limit": max_repos,
                "beta_access_mode": entitlements.beta_access_mode,
            },
        )


def raise_checkout_disabled() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "BETA_CHECKOUT_DISABLED",
            "message": "Checkout is disabled during the Beta program. All registered users have free access.",
            "beta_access_mode": True,
        },
    )
