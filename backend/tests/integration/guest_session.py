"""Shared anonymous scan session helper for integration tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.anonymous_scan import AnonymousScan


async def guest_session_headers(test_db, scan_id: UUID, token: str | None = None) -> dict[str, str]:
    token = token or AnonymousScan.generate_session_token()
    test_db.add(
        AnonymousScan(
            session_token=token,
            repository_url="https://github.com/test/repo",
            branch="main",
            linked_scan_id=str(scan_id),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    await test_db.commit()
    return {"X-Session-Token": token}
