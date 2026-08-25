"""Scan models mapped from the unified scan API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScanStartRequest(BaseModel):
    """Payload for POST /api/v1/scan/start."""

    repository_url: str
    repository_id: str | None = None
    branch: str = "main"
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
