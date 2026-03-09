"""Finding schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    """Analysis categories."""

    SECURITY = "security"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    COST = "cost"
    OBSERVABILITY = "observability"


class FindingResponse(BaseModel):
    """Individual finding response."""

    id: int
    scan_id: int
    rule_id: str
    rule_name: str
    severity: Severity
    category: Category
    description: str
    recommendation: str
    file_path: Optional[str]
    line_number: Optional[int]
    resource_name: Optional[str]
    ai_explanation: Optional[str]
    impact_analysis: Optional[str]
    confidence_score: float
    is_resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class FindingListResponse(BaseModel):
    """Finding list response."""

    findings: List[FindingResponse]
    total: int
    page: int
    page_size: int
    summary: dict  # Count by severity


class FindingUpdate(BaseModel):
    """Finding update request."""

    is_resolved: Optional[bool] = None
    resolution_note: Optional[str] = Field(None, max_length=1000)
