"""Scan models mapped from the unified scan API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScanStartRequest(BaseModel):
    """Payload for POST /api/v1/scan/start."""

    repository_url: str
    repository_id: str | None = None
    branch: str | None = None
    include_ai_explanations: bool = True


class ScanStartResponse(BaseModel):
    """Response from POST /api/v1/scan/start."""

    model_config = ConfigDict(extra="ignore")

    scan_id: str
    session_token: str | None = None
    status: str
    message: str | None = None
    repository_id: str | None = None
    repository_url: str | None = None
    branch: str | None = None


class ScanStatusResponse(BaseModel):
    """Response from GET /api/v1/scan/status/{scan_id}."""

    model_config = ConfigDict(extra="ignore")

    scan_id: str
    status: str
    progress: int = 0
    current_step: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    detected_stack: list[Any] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    created_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None

    @property
    def is_terminal(self) -> bool:
        return self.status.lower() in {"completed", "failed", "cancelled"}


class TechnologyResult(BaseModel):
    """Technology entry from GET /api/v1/scan/state/{scan_id}."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str | None = None
    status: str = "detected"
    findings: int = 0
    icon: str | None = None


class ScanStateResponse(BaseModel):
    """Authoritative scan snapshot from GET /api/v1/scan/state/{scan_id}."""

    model_config = ConfigDict(extra="ignore")

    scan_id: str
    status: str
    stage: str | None = None
    progress: int | None = None
    message: str | None = None
    current_operation: str | None = None
    is_terminal: bool = False
    error_message: str | None = None
    repository_url: str | None = None
    branch: str | None = None
    detected_stack: list[str] = Field(default_factory=list)
    technologies: list[TechnologyResult] = Field(default_factory=list)
    technology_results: list[TechnologyResult] = Field(default_factory=list)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    findings_count: int = 0
    technologies_count: int = 0
    ai_status: str | None = None
    overall_score: float | None = None
    started_at: str | None = None
    completed_at: str | None = None
    ai_completed_at: str | None = None

    @property
    def technology_items(self) -> list[TechnologyResult]:
        """Deduplicated technology list (prefer ``technology_results``)."""
        source = self.technology_results or self.technologies
        seen: set[str] = set()
        items: list[TechnologyResult] = []
        for tech in source:
            if tech.id in seen:
                continue
            seen.add(tech.id)
            items.append(tech)
        return items

    @property
    def scan_complete(self) -> bool:
        return self.status.lower() == "completed" or self.stage == "scan_completed"

    @property
    def ai_terminal(self) -> bool:
        if not self.ai_status:
            return True
        return self.ai_status.lower() in {"completed", "failed", "skipped"}

class FindingAISource(BaseModel):
    """A single attributable documentation source behind a recommendation."""

    model_config = ConfigDict(extra="ignore")

    kind: str | None = None
    title: str | None = None
    url: str | None = None
    publisher: str | None = None
    retrieval_method: str | None = None
    relationship: str | None = None
    status: str | None = None
    supplied_to_llm: bool = False
    retrieved_at: str | None = None
    version: str | None = None


class ScanFinding(BaseModel):
    """A single finding from scan results."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    rule_id: str | None = None
    rule_name: str | None = None
    severity: str
    category: str | None = None
    description: str | None = None
    recommendation: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    scanner_name: str | None = None
    documentation_url: str | None = None
    ai_source: str | None = None
    source_display: str | None = None
    documentation_status: str | None = None
    documentation_status_display: str | None = None
    sources: list[FindingAISource] = Field(default_factory=list)


class ScanResultsResponse(BaseModel):
    """Response from GET /api/v1/scan/results/{scan_id}."""

    model_config = ConfigDict(extra="ignore")

    scan_id: str
    id: str | None = None
    repository_url: str | None = None
    repository_name: str | None = None
    branch: str | None = None
    status: str
    overall_score: float | None = None
    security_score: float | None = None
    findings_count: int = 0
    severity_counts: dict[str, int] = Field(default_factory=dict)
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    findings: list[ScanFinding] = Field(default_factory=list)
    detected_technologies: list[str] = Field(default_factory=list)
    error_message: str | None = None

    def count_at_or_above(self, threshold: str) -> int:
        """Count findings at or above a severity threshold."""
        order = ["info", "low", "medium", "high", "critical"]
        threshold = threshold.lower()
        if threshold not in order:
            return 0
        min_idx = order.index(threshold)
        allowed = {order[i].upper() for i in range(min_idx, len(order))}
        allowed |= {order[i] for i in range(min_idx, len(order))}
        total = 0
        for key, count in self.severity_counts.items():
            if key.upper() in allowed or key.lower() in allowed:
                total += count
        return total
