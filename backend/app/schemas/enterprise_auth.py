"""Enterprise authentication schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    id: str
    device_name: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    last_active_at: datetime
    expires_at: Optional[datetime] = None
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"


class RevokeAllSessionsResponse(BaseModel):
    message: str
    revoked_count: int = 0
