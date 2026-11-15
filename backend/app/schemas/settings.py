"""Settings schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    username: str | None = Field(None, min_length=3, max_length=100)


class ProfileResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str | None = None
    avatar_url: str | None = None
    organization: str | None = None
    role: str
    is_verified: bool
    plan: str = "free"
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class NotificationPreferences(BaseModel):
    email_notifications: bool = True
    critical_findings_alerts: bool = True
    weekly_reports: bool = False
    product_updates: bool = False
    scan_completion_alerts: bool = True


class SessionResponse(BaseModel):
    id: str
    device_info: str | None = None
    ip_address: str | None = None
    is_current: bool = False
    last_active_at: datetime | None = None
    created_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str | None = None
    prefix: str
    key_preview: str
    is_active: bool = True
    last_used_at: datetime | None = None
    created_at: datetime | None = None


class CreateApiKeyResponse(BaseModel):
    id: str
    name: str | None = None
    prefix: str
    full_key: str
    created_at: datetime | None = None


class DeleteAccountRequest(BaseModel):
    password: str | None = None
    confirmation: str | None = None
    provider: str | None = None
