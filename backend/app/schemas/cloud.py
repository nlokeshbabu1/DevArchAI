"""Cloud Integration schemas — multi-cloud support."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.validators import validate_external_https_url

# ── Wizard ─────────────────────────────────────────────────


class WizardInitRequest(BaseModel):
    """Request to initialize the AWS onboarding wizard."""

    account_id: str = Field(
        ...,
        min_length=12,
        max_length=12,
        pattern=r"^\d{12}$",
        description="12-digit AWS Account ID",
    )
    connection_name: str = Field(default="", max_length=100)


class WizardInitResponse(BaseModel):
    """Response from wizard initialization — contains CloudFormation URL."""

    wizard_id: str
    account_id: str
    connection_name: str
    external_id: str
    stack_name: str
    role_name: str
    cloudformation_url: str
    template_url: str
    status: str = "pending"


class WizardStatusResponse(BaseModel):
    """Current wizard session status."""

    wizard_id: str
    account_id: str
    connection_name: str
    status: str
    role_arn: str | None = None
    regions: list[str] = Field(default_factory=list)
    error_message: str | None = None
    verified_account_id: str | None = None
    verified_permissions: list[str] = Field(default_factory=list)


class WizardVerifyResponse(BaseModel):
    """Result of connection verification."""

    success: bool
    account_id: str | None = None
    role_arn: str | None = None
    permissions: dict[str, Any] = Field(default_factory=dict)
    regions: list[str] = Field(default_factory=list)
    error: str | None = None


class WizardCompleteRequest(BaseModel):
    """Request to finalize wizard and create connection."""

    wizard_id: str
    regions: list[str] = Field(default_factory=lambda: ["us-east-1"])


# ── Connection ──────────────────────────────────────────────


class CloudConnectRequest(BaseModel):
    provider: str = Field(..., pattern=r"^(aws|azure|gcp|oracle)$")
    account_id: str = Field(..., min_length=12, max_length=12)
    role_arn: str = Field(..., min_length=1)
    external_id: str = Field(..., min_length=1)
    regions: list[str] = Field(default_factory=lambda: ["us-east-1"])
    connection_name: str = Field(default="", max_length=100)


class CloudConnectionResponse(BaseModel):
    id: UUID
    provider: str
    account_id: str
    role_arn: str
    connection_name: str
    status: str
    regions: list[str]
    last_scanned_at: datetime | None = None
    scan_status: str = "idle"
    resource_count: int = 0
    finding_count: int = 0
    security_score: float | None = None
    estimated_monthly_cost: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CloudConnectResponse(BaseModel):
    connection: CloudConnectionResponse
    message: str
    scan_id: str | None = None


# ── Scan ────────────────────────────────────────────────────


class CloudScanSessionSchema(BaseModel):
    id: UUID
    connection_id: UUID
    status: str
    progress: float = 0
    current_stage: str = ""
    stages_completed: list[str] = Field(default_factory=list)
    stages_total: int = 0
    resources_scanned: int = 0
    findings_count: int = 0
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Resources ───────────────────────────────────────────────


class CloudResourceSummary(BaseModel):
    total: int = 0
    by_service: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    by_region: dict[str, int] = Field(default_factory=dict)
    total_monthly_cost: float = 0.0


# ── Findings ────────────────────────────────────────────────


class CloudFindingSummary(BaseModel):
    total: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    by_service: dict[str, int] = Field(default_factory=dict)


# ── Cost ────────────────────────────────────────────────────


class CloudCostSummary(BaseModel):
    total: int = 0
    total_monthly_savings: float = 0.0
    by_service: dict[str, float] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)


# ── Compliance ──────────────────────────────────────────────


class CloudComplianceResultSchema(BaseModel):
    id: UUID
    framework: str
    total_controls: int
    passed: int
    failed: int
    warnings: int
    not_applicable: int
    score: float
    last_checked: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    provider: str = "aws"
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── AI Recommendations ──────────────────────────────────────


class AIRecommendationResponse(BaseModel):
    """Single AI recommendation returned by the API."""

    recommendation_id: str
    connection_id: str
    scan_id: str | None = None
    provider: str = "aws"
    service: str
    resource_id: str = ""
    resource_name: str = ""
    category: str
    severity: str
    title: str
    summary: str
    technical_explanation: str = ""
    business_impact: str = ""
    estimated_monthly_savings: float = 0.0
    estimated_risk_reduction: float = 0.0
    aws_cli_fix: str | None = None
    terraform_fix: str | None = None
    cloudformation_fix: str | None = None
    console_steps: list[str] = Field(default_factory=list)
    official_documentation_url: str | None = None
    recommendation_source: str = "ai_generated"
    status: str = "open"
    created_at: str | None = None


class CloudAIRecommendationSummary(BaseModel):
    total: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    total_monthly_savings: float = 0.0
    avg_risk_reduction: float = 0.0
    critical_count: int = 0


# ── Overview ────────────────────────────────────────────────


class CloudOverview(BaseModel):
    connection: CloudConnectionResponse
    resource_summary: CloudResourceSummary
    finding_summary: CloudFindingSummary
    cost_summary: CloudCostSummary
    compliance_results: list[CloudComplianceResultSchema] = Field(default_factory=list)
    ai_recommendation_summary: CloudAIRecommendationSummary = Field(default_factory=CloudAIRecommendationSummary)
    security_score: float = 0.0
    estimated_monthly_cost: float = 0.0


# ── Jira Integration ────────────────────────────────────────


class CreateJiraTicketRequest(BaseModel):
    jira_url: str = Field(..., description="Jira instance URL (e.g. https://your-domain.atlassian.net)")
    email: str = Field(..., description="Jira account email")
    api_token: str = Field(..., description="Jira API token")
    project_key: str = Field(..., description="Jira project key (e.g. SEC)")
    summary: str = Field(..., max_length=200)
    description: str = Field(..., max_length=10000)
    issue_type: str = Field(default="Task")

    @field_validator("jira_url")
    @classmethod
    def validate_jira_url(cls, value: str) -> str:
        return validate_external_https_url(value, field_name="jira_url")


class JiraTicketResponse(BaseModel):
    success: bool
    ticket_url: str | None = None
    ticket_key: str | None = None
    error: str | None = None


# ── Scan Comparison ─────────────────────────────────────────


class ScanComparisonDelta(BaseModel):
    added: int = 0
    removed: int = 0
    changed: int = 0


class ScanComparisonSection(BaseModel):
    resources: ScanComparisonDelta = Field(default_factory=ScanComparisonDelta)
    findings: ScanComparisonDelta = Field(default_factory=ScanComparisonDelta)
    cost_recommendations: ScanComparisonDelta = Field(default_factory=ScanComparisonDelta)
    compliance: ScanComparisonDelta = Field(default_factory=ScanComparisonDelta)
    ai_recommendations: ScanComparisonDelta = Field(default_factory=ScanComparisonDelta)


class ScanComparisonResponse(BaseModel):
    connection_id: str
    old_scan_id: str | None
    new_scan_id: str | None
    old_scan: CloudScanSessionSchema | None = None
    new_scan: CloudScanSessionSchema | None = None
    deltas: ScanComparisonSection = Field(default_factory=ScanComparisonSection)


# ── WebSocket events ────────────────────────────────────────


class CloudScanEvent(BaseModel):
    event_type: str
    stage: str = ""
    progress: float = 0
    message: str = ""
    resource_count: int = 0
    finding_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
