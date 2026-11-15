"""Authorization tests for legacy /api/v1/scans and related guest flows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text as sa_text

from app.core.security import create_access_token
from app.models.anonymous_scan import AnonymousScan
from app.models.scan import Scan, ScanStatus


async def _insert_user(test_db, username: str | None = None):
    user_id = uuid4()
    username = username or f"legacy-{user_id.hex[:8]}"
    await test_db.execute(
        sa_text(
            """
            INSERT INTO users (
                id, email_encrypted, email_hash, username, hashed_password,
                is_active, is_verified, role, subscription_plan, subscription_status,
                mfa_enabled, failed_login_attempts
            )
            VALUES (
                :id, 'enc', :email_hash, :username, 'hash',
                true, true, 'USER', 'free', 'active',
                false, 0
            )
            """
        ),
        {"id": user_id, "email_hash": f"hash-{user_id}", "username": username},
    )
    await test_db.commit()
    return user_id


def _auth_headers(user_id) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


async def _guest_scan_with_session(test_db, token: str | None = None):
    scan_id = uuid4()
    session = token or AnonymousScan.generate_session_token()
    scan = Scan(
        id=scan_id,
        user_id=None,
        repository_url="https://github.com/test/guest-repo",
        branch="main",
        status=ScanStatus.COMPLETED,
    )
    anon = AnonymousScan(
        session_token=session,
        repository_url=scan.repository_url,
        branch="main",
        linked_scan_id=str(scan_id),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    test_db.add(scan)
    test_db.add(anon)
    await test_db.commit()
    return scan_id, session


@pytest.mark.asyncio
async def test_list_scans_requires_authentication(client):
    response = await client.get("/api/v1/scans")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_guest_scan_denied_without_session_token(client, test_db):
    scan_id, _ = await _guest_scan_with_session(test_db)
    response = await client.get(f"/api/v1/scans/{scan_id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_guest_cannot_read_other_guest_scan_even_with_wrong_token(client, test_db):
    token_a = f"anon_{uuid4().hex}"
    token_b = f"anon_{uuid4().hex}"
    scan_id, _ = await _guest_scan_with_session(test_db, token=token_a)
    other_scan_id, _ = await _guest_scan_with_session(test_db, token=token_b)
    headers = {"X-Session-Token": token_a}
    response = await client.get(f"/api/v1/scans/{other_scan_id}", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_guest_reads_own_scan_with_valid_session(client, test_db):
    scan_id, token = await _guest_scan_with_session(test_db)
    headers = {"X-Session-Token": token}
    response = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(scan_id)


@pytest.mark.asyncio
async def test_owner_reads_owned_scan(client, test_db):
    owner_id = await _insert_user(test_db)
    scan_id = uuid4()
    scan = Scan(
        id=scan_id,
        user_id=owner_id,
        repository_url="https://github.com/test/owned",
        branch="main",
        status=ScanStatus.COMPLETED,
    )
    test_db.add(scan)
    await test_db.commit()

    response = await client.get(f"/api/v1/scans/{scan_id}", headers=_auth_headers(owner_id))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_other_user_denied_owned_scan(client, test_db):
    owner_id = await _insert_user(test_db, username=f"owner-{uuid4().hex[:8]}")
    other_id = await _insert_user(test_db, username=f"other-{uuid4().hex[:8]}")
    scan_id = uuid4()
    test_db.add(
        Scan(
            id=scan_id,
            user_id=owner_id,
            repository_url="https://github.com/test/owned",
            branch="main",
            status=ScanStatus.COMPLETED,
        )
    )
    await test_db.commit()

    response = await client.get(f"/api/v1/scans/{scan_id}", headers=_auth_headers(other_id))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_public_status_requires_guest_session(client, test_db):
    scan_id, token = await _guest_scan_with_session(test_db)
    denied = await client.get(f"/api/v1/public/status/{scan_id}")
    assert denied.status_code == 403
    allowed = await client.get(
        f"/api/v1/public/status/{scan_id}",
        headers={"X-Session-Token": token},
    )
    assert allowed.status_code == 200
