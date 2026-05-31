"""AWS integration API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AWSConnectRequest(BaseModel):
    access_key_id: str = Field(..., min_length=16, max_length=128)
    secret_access_key: str = Field(..., min_length=20, max_length=256)
    default_region: str = Field(default="us-east-1", min_length=3, max_length=32)
    account_alias: str | None = Field(default=None, max_length=255)
    connection_type: str = Field(default="access_key", pattern="^(access_key|assume_role)$")
    role_arn: str | None = None
    external_id: str | None = None


class AWSAccountResponse(BaseModel):
    id: UUID
    account_id: str
    account_alias: str | None
    connection_type: str
    default_region: str
    is_active: bool
    scan_status: str
    scan_progress: int
    last_error: str | None
    last_scanned_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class AWSConnectResponse(BaseModel):
    account: AWSAccountResponse
    message: str


class AWSInventoryItem(BaseModel):
    id: UUID
    account_id: UUID
    resource_type: str
    resource_id: str
    name: str | None
    region: str | None
    metadata_json: dict[str, Any]
    collected_at: datetime

    class Config:
        from_attributes = True


class AWSFindingItem(BaseModel):
    id: UUID
    account_id: UUID
    category: str
    severity: str
    title: str
    description: str
    resource_type: str | None
    resource_id: str | None
    region: str | None
    recommendation: str | None
    metadata_json: dict[str, Any]
    detected_at: datetime

    class Config:
        from_attributes = True


class AWSCostRecommendationItem(BaseModel):
    id: UUID
    account_id: UUID
    recommendation_type: str
    title: str
    description: str
    resource_type: str | None
    resource_id: str | None
    region: str | None
    estimated_monthly_savings: float
    metadata_json: dict[str, Any]
    detected_at: datetime

    class Config:
        from_attributes = True


class AWSListResponse(BaseModel):
    items: list[Any]
    total: int
