"""Logout with refresh cookie only (expired access token)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.refresh_session_service import (
    generate_opaque_refresh_token,
    resolve_user_from_refresh_cookie,
)


@pytest.mark.asyncio
async def test_resolve_user_from_refresh_cookie():
    user_id = uuid4()
    raw = generate_opaque_refresh_token()
    user = AsyncMock()
    user.id = user_id
    user.is_active = True
    session = AsyncMock()

    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=AsyncMock(first=lambda: (session, user)),
    )

    with patch(
        "app.services.refresh_session_service.hash_token",
        return_value="hash",
    ):
        resolved = await resolve_user_from_refresh_cookie(db, raw)
    assert resolved is user
