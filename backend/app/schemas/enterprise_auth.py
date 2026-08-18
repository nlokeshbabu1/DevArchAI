"""Enterprise authentication schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    id: str
    device_name: str | None = None
    browser: str | None = None
    os: str | None = None
    ip_address: str | None = None
    location: str | None = None
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime | None = None
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"


class RevokeAllSessionsResponse(BaseModel):
    message: str
    revoked_count: int = 0
