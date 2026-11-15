"""Regression tests for scan deletion, account deletion, and integration status."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text as sa_text

from app.core.security import create_access_token, get_password_hash
from app.models.github_installation import GitHubInstallation
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus
from app.models.user import User


@pytest.fixture(autouse=True)
def _jwt_blacklist_available():
    with patch(
        "app.services.token_blacklist.is_blacklisted",
        new_callable=AsyncMock,
        return_value=False,
    ):
        yield


async def _insert_user(
    test_db,
    *,
    username: str | None = None,
    password: str = "correct-horse",
    github_id: str | None = None,
    gitlab_id: str | None = None,
    oauth_token: str | None = None,
) -> UUID:
    user_id = uuid4()
    username = username or f"user-{user_id.hex[:10]}"
    hashed = get_password_hash(password) if password else ""
    await test_db.execute(
        sa_text(
            """
            INSERT INTO users (
                id, email_encrypted, email_hash, username, hashed_password,
                is_active, is_verified, role, subscription_plan, subscription_status,
                mfa_enabled, failed_login_attempts, github_id, gitlab_id, github_access_token
            )
            VALUES (
                :id, 'enc', :email_hash, :username, :hashed_password,
                true, true, 'USER', 'free', 'active',
                false, 0, :github_id, :gitlab_id, :github_access_token
            )
            """
        ),
        {
            "id": user_id,
            "email_hash": f"hash-{user_id}",
            "username": username,
            "hashed_password": hashed,
            "github_id": github_id,
            "gitlab_id": gitlab_id,
            "github_access_token": oauth_token,
        },
    )
    await test_db.commit()
    return user_id


def _auth_headers(user_id: UUID) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


async def _insert_scan(
    test_db,
    user_id: UUID,
    status: ScanStatus = ScanStatus.COMPLETED,
    *,
    celery_task_id: str | None = None,
) -> UUID:
    scan_id = uuid4()
    scan = Scan(
        id=scan_id,
        user_id=user_id,
        repository_url="https://github.com/test/sample",
        branch="main",
        status=status,
        progress=100 if status == ScanStatus.COMPLETED else 10,
        celery_task_id=celery_task_id,
    )
    test_db.add(scan)
    await test_db.commit()
    return scan_id


@pytest.mark.asyncio
async def test_owner_can_delete_scan(client, test_db):
    user_id = await _insert_user(test_db)
    scan_id = await _insert_scan(test_db, user_id)

    response = await client.delete(f"/api/v1/scans/{scan_id}", headers=_auth_headers(user_id))
    assert response.status_code == 200
    assert response.json()["success"] is True

    remaining = await test_db.execute(select(Scan).where(Scan.id == scan_id))
    assert remaining.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_other_user_cannot_delete_scan(client, test_db):
    owner_id = await _insert_user(test_db)
    other_id = await _insert_user(test_db)
    scan_id = await _insert_scan(test_db, owner_id)

    response = await client.delete(f"/api/v1/scans/{scan_id}", headers=_auth_headers(other_id))
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_unauthenticated_cannot_delete_scan(client, test_db):
    user_id = await _insert_user(test_db)
    scan_id = await _insert_scan(test_db, user_id)

    response = await client.delete(f"/api/v1/scans/{scan_id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_missing_scan_returns_404(client, test_db):
    user_id = await _insert_user(test_db)
    missing = uuid4()
    response = await client.delete(f"/api/v1/scans/{missing}", headers=_auth_headers(user_id))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_running_scan_cancels_then_removes(client, test_db):
    user_id = await _insert_user(test_db)
    scan_id = await _insert_scan(
        test_db,
        user_id,
        status=ScanStatus.PROCESSING,
        celery_task_id="task-delete-123",
    )

    with patch("app.api.v1.routes.scans.cancel_scan_task") as mock_cancel:
        mock_cancel.delay = MagicMock()
        response = await client.delete(f"/api/v1/scans/{scan_id}", headers=_auth_headers(user_id))

    assert response.status_code == 200
    mock_cancel.delay.assert_called_once_with(str(scan_id))
    remaining = await test_db.execute(select(Scan).where(Scan.id == scan_id))
    assert remaining.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_account_password_user(client, test_db):
    user_id = await _insert_user(test_db, password="delete-me-now")
    response = await client.request(
        "DELETE",
        "/api/v1/settings/account",
        headers=_auth_headers(user_id),
        json={"password": "delete-me-now"},
    )
    assert response.status_code == 200
    remaining = await test_db.execute(select(User).where(User.id == user_id))
    assert remaining.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_account_wrong_password(client, test_db):
    user_id = await _insert_user(test_db, password="good-password")
    response = await client.request(
        "DELETE",
        "/api/v1/settings/account",
        headers=_auth_headers(user_id),
        json={"password": "bad-password"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_account_oauth_requires_confirmation(client, test_db):
    user_id = await _insert_user(test_db, password="", github_id="12345", oauth_token="gho_test")
    with patch(
        "app.services.account_deletion.verify_github_identity_active",
        new_callable=AsyncMock,
    ) as verify_github:
        verify_github.return_value = None
        response = await client.request(
            "DELETE",
            "/api/v1/settings/account",
            headers=_auth_headers(user_id),
            json={"confirmation": "DELETE", "provider": "github"},
        )
    assert response.status_code == 200
    verify_github.assert_awaited_once()


@pytest.mark.asyncio
async def test_integration_status_splits_github_states(client, test_db):
    user_id = await _insert_user(test_db, password="pw", github_id=None)

    test_db.add(
        Repository(
            user_id=user_id,
            name="org/manual-repo",
            url="https://github.com/org/manual-repo",
        )
    )
    test_db.add(
        GitHubInstallation(
            user_id=user_id,
            installation_id=999001,
            repo_full_name="acme/manual-repo",
        )
    )
    await test_db.commit()

    response = await client.get("/api/v1/integrations/status", headers=_auth_headers(user_id))
    assert response.status_code == 200
    data = response.json()
    assert data["github_oauth"] is False
    assert data["github_app_installed"] is True
    assert data["github_repository_access"] is True
    assert data["github"] is True