"""Authentication schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    """User role enumeration."""

    USER = "user"
    ADMIN = "admin"
    ENTERPRISE = "enterprise"


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded token data."""

    user_id: Optional[str] = None
    email: Optional[str] = None
    exp: Optional[datetime] = None


class UserCreate(BaseModel):
    """User registration request."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    organization_name: Optional[str] = Field(None, max_length=255)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "securepassword123",
                "full_name": "John Doe",
                "organization_name": "Acme Inc",
            }
        }


class UserLogin(BaseModel):
    """User login request."""

    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
            }
        }


class UserResponse(BaseModel):
    """User response."""

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    last_login_at: Optional[datetime] = None
    has_api_key: bool = False
    plan: str = "free"  # Subscription plan: free, plus, pro, enterprise


class UserUpdate(BaseModel):
    """User update request."""

    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    current_password: Optional[str] = Field(None, max_length=100)
    new_password: Optional[str] = Field(None, min_length=8, max_length=100)


class APIKeyResponse(BaseModel):
    """API key response."""

    api_key: str
    api_key_prefix: str
    created_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_key": "dk_abcd_1234567890abcdef",
                "api_key_prefix": "dk_abcd",
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
    )
