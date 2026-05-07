"""Report schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryScore(BaseModel):
    """Score for a specific category."""

    category: str
    score: float = Field(ge=0, le=100)
    findings_count: int
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


class ReportFormat(str, Enum):
    """Supported downloadable report formats."""

    PDF = "pdf"
    EXCEL = "excel"


class ReportResponse(BaseModel):
    """Complete analysis report response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    repository_name: str
    repository_url: str
    commit_hash: str | None

    # Scores
    overall_score: float = Field(ge=0, le=100)
    category_scores: dict[str, float] | None

    # AI-generated content
    executive_summary: str | None
    risk_analysis: str | None
    prioritized_recommendations: list[str] | None

    # Summary statistics
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int

    # Files analyzed
    files_analyzed: list[str] | None
    pdf_s3_key: str | None = None
    excel_s3_key: str | None = None

    # Timestamps
    created_at: datetime

    @field_validator("id", "scan_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, value):
        """Convert UUID objects to strings."""
        if isinstance(value, UUID):
            return str(value)
        return value


class ReportListResponse(BaseModel):
    """Report list response."""

    reports: list[ReportResponse]
    total: int
    page: int
    page_size: int


class ReportDownloadResponse(BaseModel):
    """Report download response."""

    report_id: str
    scan_id: str
    format: ReportFormat
    url: str
    filename: str
    expires_at: datetime
    expires_in_seconds: int = 300

    @field_validator("report_id", "scan_id", mode="before")
    @classmethod
    def convert_download_uuids_to_str(cls, value):
        """Convert UUID objects to strings."""
        if isinstance(value, UUID):
            return str(value)
        return value


class ReportSummary(BaseModel):
    """Report summary for dashboard."""

    id: str
    scan_id: str
    repository_name: str
    overall_score: float
    total_findings: int
    critical_count: int
    high_count: int
    created_at: datetime

    @field_validator("id", "scan_id", mode="before")
    @classmethod
    def convert_summary_uuids_to_str(cls, value):
        """Convert UUID objects to strings."""
        if isinstance(value, UUID):
            return str(value)
        return value
