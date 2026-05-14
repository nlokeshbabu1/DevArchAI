"""Settings schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=100)


class ProfileResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    organization: Optional[str] = None
    role: str
    is_verified: bool
    plan: str = "free"
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


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
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    is_current: bool = False
    last_active_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    id: str
    name: Optional[str] = None
    prefix: str
    key_preview: str
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class CreateApiKeyResponse(BaseModel):
    id: str
    name: Optional[str] = None
    prefix: str
    full_key: str
    created_at: Optional[datetime] = None


class DeleteAccountRequest(BaseModel):
    password: str
