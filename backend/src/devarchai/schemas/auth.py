"""Authentication schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    """User registration request."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    organization_name: str | None = None


class UserLogin(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    username: str
    full_name: str | None = None
    avatar_url: str | None = None
    is_active: bool
    is_verified: bool
    role: str
    current_org_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update request."""

    full_name: str | None = None
    avatar_url: str | None = None
    current_password: str | None = None
    new_password: str | None = None


class APIKeyResponse(BaseModel):
    """API key response."""

    api_key: str
    api_key_prefix: str
    created_at: datetime
