"""Shared scan read-access checks (tenant isolation + anonymous session tokens)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anonymous_scan import AnonymousScan
from app.models.scan import Scan
from app.models.user import User


async def verify_anonymous_session(
    db: AsyncSession,
    scan_id: UUID | str,
    session_token: str | None,
) -> None:
    """Ensure the caller holds a valid anonymous session for this scan."""
    if not session_token or not session_token.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A valid session token is required for this scan",
        )
    token = session_token.strip()
    result = await db.execute(
        select(AnonymousScan).where(
            AnonymousScan.linked_scan_id == str(scan_id),
            AnonymousScan.session_token == token,
            AnonymousScan.expires_at > datetime.now(UTC),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anonymous scan session is invalid or expired",
        )


async def assert_scan_read_access(
    db: AsyncSession,
    scan: Scan,
    current_user: User | None,
    session_token: str | None,
) -> None:
    """
    Enforce read access for scan-scoped resources.

    - Owned scans: authenticated owner only.
    - Anonymous scans (``user_id IS NULL``): valid ``AnonymousScan`` session token.
    """
    if scan.user_id is not None:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication required",
            )
        if scan.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return

    await verify_anonymous_session(db, scan.id, session_token)
