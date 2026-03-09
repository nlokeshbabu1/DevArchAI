"""Organization schemas."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


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
    slug: Optional[str] = None
    description: Optional[str] = None


class OrganizationUpdate(BaseModel):
    """Organization update request."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class OrganizationResponse(BaseModel):
    """Organization response."""

    id: str
    name: str
    slug: str
    description: Optional[str] = None
    plan: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    """Organization member response."""

    id: str
    user_id: str
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    joined_at: Optional[datetime] = None


class MemberInvite(BaseModel):
    """Member invitation request."""

    email: EmailStr
    role: MembershipRole = MembershipRole.MEMBER


class MemberUpdate(BaseModel):
    """Member update request."""

    role: MembershipRole
