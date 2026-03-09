"""Report schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CategoryScore(BaseModel):
    """Score for a specific category."""

    category: str
    score: float = Field(ge=0, le=100)
    findings_count: int
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


class ReportResponse(BaseModel):
    """Complete analysis report response."""

    id: int
    scan_id: int
    repository_name: str
    repository_url: str
    commit_hash: Optional[str]

    # Scores
    overall_score: float = Field(ge=0, le=100)
    category_scores: Optional[Dict[str, float]]

    # AI-generated content
    executive_summary: Optional[str]
    risk_analysis: Optional[str]
    prioritized_recommendations: Optional[List[str]]

    # Summary statistics
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int

    # Files analyzed
    files_analyzed: Optional[List[str]]

    # Timestamps
    created_at: datetime

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Report list response."""

    reports: List[ReportResponse]
    total: int
    page: int
    page_size: int


class ReportDownloadResponse(BaseModel):
    """Report download response."""

    report_id: int
    filename: str
    content_type: str
    size_bytes: int


class ReportSummary(BaseModel):
    """Report summary for dashboard."""

    id: int
    scan_id: int
    repository_name: str
    overall_score: float
    total_findings: int
    critical_count: int
    high_count: int
    created_at: datetime
