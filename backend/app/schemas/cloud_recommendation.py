"""Cloud AI Recommendation schemas — Pydantic models for API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CloudAIRecommendationResponse(BaseModel):
    """Full AI recommendation response."""

    id: UUID
    connection_id: UUID
    scan_session_id: UUID | None = None
    finding_id: str | None = None
    rule_id: str | None = None
    service: str
    resource_id: str | None = None
    region: str

    executive_summary: str
    root_cause: str
    business_impact: str = ""
    security_impact: str = ""
    cost_impact: str = ""

    official_best_practice: str = ""
    documentation_references: list[dict[str, Any]] = Field(default_factory=list)
    documentation_retrieved_at: datetime | None = None

    terraform_fix: str | None = None
    aws_cli_fix: str | None = None
    console_steps: list[str] = Field(default_factory=list)

    compliance_mapping: dict[str, Any] = Field(default_factory=dict)

    confidence_score: float = 0.0
    estimated_risk_reduction: float = 0.0
    estimated_monthly_savings: float = 0.0
    severity: str = "medium"

    knowledge_sources_used: list[str] = Field(default_factory=list)
    llm_provider: str | None = None

    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class CloudAIRecommendationSummary(BaseModel):
    """Aggregated recommendation summary for dashboard."""

    total: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_service: dict[str, int] = Field(default_factory=dict)
    total_estimated_monthly_savings: float = 0.0
    avg_confidence_score: float = 0.0
    total_estimated_risk_reduction: float = 0.0
    recommendations: list[CloudAIRecommendationResponse] = Field(default_factory=list)


class CloudAIRecommendationListResponse(BaseModel):
    """Paginated list of recommendations."""

    recommendations: list[CloudAIRecommendationResponse]
    total: int
    page: int = 1
    page_size: int = 20
