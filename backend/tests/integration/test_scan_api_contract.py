"""Scan API contract, auth, entitlement, and isolation integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy import select, text as sa_text

from app.core.security import create_access_token
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus


@pytest.fixture(autouse=True)
def _fast_branch_resolution():
    with patch(
        "app.api.v1.routes.unified_scan.resolve_repository_branch",
        return_value="main",
    ):
        yield


@pytest.fixture(autouse=True)
def _jwt_blacklist_available():
    with patch(
        "app.services.token_blacklist.is_blacklisted",
        new_callable=AsyncMock,
        return_value=False,
    ):
        yield


async def _insert_user(test_db, username: str | None = None) -> UUID:
    user_id = uuid4()
    username = username or f"scan-api-{user_id.hex[:10]}"
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
        {
            "id": user_id,
            "email_hash": f"hash-{user_id}",
            "username": username,
        },
    )
    await test_db.commit()
    return user_id


def _auth_headers(user_id: UUID) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


SCAN_START_URL = "/api/v1/scan/start"
VALID_PAYLOAD = {"repository_url": "https://github.com/test/sample-repo"}


@pytest.mark.asyncio
class TestScanStartValidation:
    async def test_missing_repository_url_returns_422(self, client):
        response = await client.post(SCAN_START_URL, json={})
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body or body.get("error", {}).get("code") == "VALIDATION_ERROR"

    async def test_valid_guest_scan_without_branch(self, client):
        with patch("app.api.v1.routes.unified_scan.SyncScanService"):
            response = await client.post(SCAN_START_URL, json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["branch"] == "main"
        assert UUID(data["scan_id"])

    async def test_invalid_repository_id_format(self, client, test_db):
        user_id = await _insert_user(test_db)
        response = await client.post(
            SCAN_START_URL,
            json={**VALID_PAYLOAD, "repository_id": "not-a-uuid"},
            headers=_auth_headers(user_id),
        )
        assert response.status_code == 400
        body = response.json()
        detail_text = str(body.get("detail") or body.get("error", {}).get("message", ""))
        assert "repository_id" in detail_text.lower()


@pytest.mark.asyncio
class TestScanStartAuthorization:
    async def test_repository_id_requires_authentication(self, client):
        response = await client.post(
            SCAN_START_URL,
            json={**VALID_PAYLOAD, "repository_id": str(uuid4())},
        )
        assert response.status_code == 403

    async def test_repository_not_found_for_user(self, client, test_db):
        user_id = await _insert_user(test_db)
        response = await client.post(
            SCAN_START_URL,
            json={**VALID_PAYLOAD, "repository_id": str(uuid4())},
            headers=_auth_headers(user_id),
        )
        assert response.status_code == 404

    async def test_cross_tenant_repository_denied(self, client, test_db):
        owner_id = await _insert_user(test_db, username=f"owner-{uuid4().hex[:8]}")
        other_id = await _insert_user(test_db, username=f"other-{uuid4().hex[:8]}")
        repo = Repository(
            user_id=owner_id,
            name="infra",
            url="https://github.com/acme/infra",
            default_branch="main",
            is_active=True,
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)

        response = await client.post(
            SCAN_START_URL,
            json={
                "repository_url": repo.url,
                "repository_id": str(repo.id),
            },
            headers=_auth_headers(other_id),
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestScanStatusAuthorization:
    async def test_status_404_for_invalid_scan_id(self, client):
        response = await client.get(f"/api/v1/scan/status/{uuid4()}")
        assert response.status_code == 404

    async def test_status_denies_other_authenticated_user(self, client, test_db):
        owner_id = await _insert_user(test_db, username=f"own-{uuid4().hex[:8]}")
        other_id = await _insert_user(test_db, username=f"oth-{uuid4().hex[:8]}")
        scan_id = uuid4()
        scan = Scan(
            id=scan_id,
            user_id=owner_id,
            repository_url=VALID_PAYLOAD["repository_url"],
            branch="main",
            status=ScanStatus.PROCESSING,
            progress=10,
        )
        test_db.add(scan)
        await test_db.commit()

        response = await client.get(
            f"/api/v1/scan/status/{scan_id}",
            headers=_auth_headers(other_id),
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestScanEntitlements:
    async def test_monthly_scan_limit_returns_429(self, client, test_db):
        user_id = await _insert_user(test_db)

        async def _limit(_user, _db):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "SCAN_LIMIT_EXCEEDED",
                    "message": "Monthly scan limit reached (50 scans)",
                    "beta_access_mode": True,
                },
            )

        with patch("app.api.v1.routes.unified_scan.SyncScanService"), patch(
            "app.api.v1.routes.unified_scan.enforce_scan_monthly_limit",
            side_effect=_limit,
        ):
            response = await client.post(
                SCAN_START_URL,
                json=VALID_PAYLOAD,
                headers=_auth_headers(user_id),
            )

        assert response.status_code == 429
        body = response.json()
        message = body.get("error", {}).get("message", body)
        if isinstance(message, dict):
            assert message.get("error") == "SCAN_LIMIT_EXCEEDED"
            assert message.get("beta_access_mode") is True
        else:
            assert "SCAN_LIMIT" in str(message)


@pytest.mark.asyncio
class TestDuplicateScanHandling:
    async def test_returns_existing_in_progress_scan(self, client, test_db):
        user_id = await _insert_user(test_db, username=f"dup-{uuid4().hex[:8]}")
        repo = Repository(
            user_id=user_id,
            name="sample",
            url=VALID_PAYLOAD["repository_url"],
            default_branch="main",
            is_active=True,
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)

        existing = Scan(
            id=uuid4(),
            user_id=user_id,
            repository_id=repo.id,
            repository_url=repo.url,
            branch="main",
            status=ScanStatus.PENDING,
            progress=0,
        )
        test_db.add(existing)
        await test_db.commit()

        with patch("app.api.v1.routes.unified_scan.SyncScanService"):
            response = await client.post(
                SCAN_START_URL,
                json={
                    "repository_url": repo.url,
                    "repository_id": str(repo.id),
                },
                headers=_auth_headers(user_id),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["scan_id"] == str(existing.id)
        assert "already in progress" in data.get("message", "").lower()

        count = await test_db.execute(
            select(Scan).where(
                Scan.user_id == user_id,
                Scan.repository_id == repo.id,
                Scan.status.in_([ScanStatus.PENDING, ScanStatus.PROCESSING, ScanStatus.QUEUED]),
            )
        )
        rows = count.scalars().all()
        assert len(rows) == 1
