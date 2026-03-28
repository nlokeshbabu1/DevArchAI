"""Finding schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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
    summary: Optional[str] = None
    risk: Optional[str] = None
    impact: Optional[str] = None
    fix_example: Optional[str] = None
    fix_code: Optional[str] = None
    full_example: Optional[str] = None
    best_practices: Optional[list[str]] = None
    file_path: Optional[str]
    line_number: Optional[int]
    resource_name: Optional[str]
    ai_explanation: Optional[str]
    impact_analysis: Optional[str]
    ai_generated: Optional[bool] = False
    documentation_url: Optional[str] = None
    confidence: Optional[float] = None
    confidence_score: float
    is_resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class FindingListResponse(BaseModel):
    """Finding list response."""

    findings: list[FindingResponse]
    total: int
    page: int
    page_size: int
    summary: dict  # Count by severity


class FindingUpdate(BaseModel):
    """Finding update request."""

    is_resolved: Optional[bool] = None
    resolution_note: Optional[str] = Field(None, max_length=1000)


class EnrichedFinding(BaseModel):
    """Enriched finding with full remediation guidance."""

    rule_id: str
    title: str
    severity: Severity
    category: Category
    description: str
    summary: Optional[str] = None
    risk: str
    impact: str
    file: str
    line: Optional[int] = None
    resource: Optional[str] = None
    recommendation: str
    fix_example: Optional[str] = None
    fix_code: Optional[str] = None
    full_example: Optional[str] = None
    best_practices: Optional[str] = None
    ai_explanation: Optional[str] = None
    ai_generated: Optional[bool] = False
    documentation_url: Optional[str] = None
    confidence: Optional[float] = None

    class Config:
        from_attributes = True
