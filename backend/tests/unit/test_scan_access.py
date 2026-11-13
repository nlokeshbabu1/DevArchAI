"""Tests for scan read-access enforcement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.scan_access import assert_scan_read_access, verify_anonymous_session
from app.models.anonymous_scan import AnonymousScan
from app.models.scan import Scan, ScanStatus
from app.models.user import User


from sqlalchemy import text as sa_text


@pytest.mark.asyncio
async def test_owned_scan_denies_other_user(db_session):
    owner_id = uuid4()
    other_id = uuid4()
    scan_id = uuid4()
    await db_session.execute(
        sa_text(
            "INSERT INTO users (id, email_encrypted, email_hash, username, hashed_password, "
            "is_active, is_verified, role, subscription_plan, subscription_status, "
            "mfa_enabled, failed_login_attempts) "
            "VALUES (:id, '', :eh, :un, '', true, true, 'USER', 'free', 'active', false, 0)"
        ),
        {"id": owner_id, "eh": f"h-{owner_id}", "un": f"owner-{owner_id.hex[:8]}"},
    )
    scan = Scan(
        id=scan_id,
        user_id=owner_id,
        repository_url="https://github.com/a/b",
        branch="main",
        status=ScanStatus.PENDING,
    )
    other = User(
        id=other_id,
        email_encrypted="e",
        email_hash=f"h-{other_id}",
        username=f"u-{other_id}",
        hashed_password="x",
    )
    db_session.add(scan)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await assert_scan_read_access(db_session, scan, other, None)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_anonymous_scan_requires_session_token(db_session):
    scan_id = uuid4()
    scan = Scan(
        id=scan_id,
        user_id=None,
        repository_url="https://github.com/a/b",
        branch="main",
        status=ScanStatus.PENDING,
    )
    db_session.add(scan)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await assert_scan_read_access(db_session, scan, None, None)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_anonymous_scan_accepts_valid_session():
    from unittest.mock import AsyncMock, MagicMock

    scan_id = uuid4()
    token = "st_test_token_abc"
    scan = Scan(
        id=scan_id,
        user_id=None,
        repository_url="https://github.com/a/b",
        branch="main",
        status=ScanStatus.PENDING,
    )
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=lambda: MagicMock(session_token=token))
    )
    await assert_scan_read_access(db, scan, None, token)
