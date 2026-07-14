"""Finding schemas."""

from datetime import datetime
from enum import Enum

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
    summary: str | None = None
    risk: str | None = None
    impact: str | None = None
    fix_example: str | None = None
    fix_code: str | None = None
    full_example: str | None = None
    best_practices: list[str] | None = None
    file_path: str | None
    line_number: int | None
    resource_name: str | None
    ai_explanation: str | None
    impact_analysis: str | None
    ai_generated: bool | None = False
    documentation_url: str | None = None
    confidence: float | None = None
    confidence_score: float
    is_resolved: bool
    resolved_at: datetime | None
    created_at: datetime
    # Scanner metadata fields (backward-compatible)
    scanner_name: str | None = None
    scanner_rule_id: str | None = None
    package: str | None = None
    installed_version: str | None = None
    fixed_version: str | None = None
    cve: str | None = None
    cwe: str | None = None
    references: list[str] | None = None
    evidence: str | None = None

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

    is_resolved: bool | None = None
    resolution_note: str | None = Field(None, max_length=1000)


class EnrichedFinding(BaseModel):
    """Enriched finding with full remediation guidance."""

    rule_id: str
    title: str
    severity: Severity
    category: Category
    description: str
    summary: str | None = None
    risk: str
    impact: str
    file: str
    line: int | None = None
    resource: str | None = None
    recommendation: str
    fix_example: str | None = None
    fix_code: str | None = None
    full_example: str | None = None
    best_practices: str | None = None
    ai_explanation: str | None = None
    ai_generated: bool | None = False
    documentation_url: str | None = None
    confidence: float | None = None

    class Config:
        from_attributes = True
