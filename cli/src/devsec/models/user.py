"""User model returned by the backend auth endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UserInfo(BaseModel):
    """The authenticated user (``GET /api/v1/auth/me``)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    email: str
    username: str
    full_name: str | None = None
    avatar_url: str | None = None
    role: str = "user"
    is_active: bool = True
    is_verified: bool = False
    has_api_key: bool = False
    plan: str = "free"
    provider: str = "password"
