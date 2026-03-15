"""Organization schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class MembershipRole(str, Enum):
    """Organization membership roles."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class PlanType(str, Enum):
    """Subscription plan types."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class OrganizationCreate(BaseModel):
    """Organization creation request."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = None
    description: str | None = None


class OrganizationUpdate(BaseModel):
    """Organization update request."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class OrganizationResponse(BaseModel):
    """Organization response."""

    id: str
    name: str
    slug: str
    description: str | None = None
    plan: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    """Organization member response."""

    id: str
    user_id: str
    email: str
    username: str
    full_name: str | None = None
    role: str
    joined_at: datetime | None = None


class MemberInvite(BaseModel):
    """Member invitation request."""

    email: EmailStr
    role: MembershipRole = MembershipRole.MEMBER


class MemberUpdate(BaseModel):
    """Member update request."""

    role: MembershipRole
