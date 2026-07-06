"""Scanner execution models — status enum, result dataclass, applicability info."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.rule_engine.base import RuleFinding


class ScannerStatus(str, enum.Enum):
    """Explicit execution status for each scanner adapter."""

    DISCOVERED = "DISCOVERED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_FINDINGS = "COMPLETED_WITH_FINDINGS"
    COMPLETED_NO_FINDINGS = "COMPLETED_NO_FINDINGS"
    SKIPPED_NOT_APPLICABLE = "SKIPPED_NOT_APPLICABLE"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"
    FAILED = "FAILED"


@dataclass
class ApplicabilityInfo:
    """Describes whether a scanner is applicable to the repository."""

    applicable: bool
    reason: str = ""


@dataclass
class ScannerExecutionResult:
    """Result of executing a single scanner adapter, including execution metadata."""

    scanner_name: str
    scanner_id: str
    status: ScannerStatus
    applicable: bool = True
    enabled: bool = True
    version: str | None = None
    execution_start: datetime | None = None
    execution_end: datetime | None = None
    duration_ms: int | None = None
    files_scanned: int | None = None
    rules_executed: int | None = None
    findings_count: int = 0
    skipped_reason: str | None = None
    error_message: str | None = None
    findings: list[RuleFinding] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        if self.duration_ms is not None:
            return round(self.duration_ms / 1000, 2)
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanner_name": self.scanner_name,
            "scanner_id": self.scanner_id,
            "status": self.status.value,
            "applicable": self.applicable,
            "enabled": self.enabled,
            "version": self.version,
            "execution_start": self.execution_start.isoformat() if self.execution_start else None,
            "execution_end": self.execution_end.isoformat() if self.execution_end else None,
            "duration_ms": self.duration_ms,
            "duration_seconds": self.duration_seconds,
            "files_scanned": self.files_scanned,
            "rules_executed": self.rules_executed,
            "findings_count": self.findings_count,
            "skipped_reason": self.skipped_reason,
            "error_message": self.error_message,
        }
