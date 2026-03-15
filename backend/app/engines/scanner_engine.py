"""Scanner engine base classes and interfaces."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class ScannerSeverity(str, Enum):
    """Scanner finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ScannerFinding:
    """Unified finding from any scanner."""

    scanner_id: str
    rule_id: str
    rule_name: str
    severity: ScannerSeverity
    category: str
    description: str
    recommendation: str
    file_path: str
    line_number: Optional[int] = None
    resource_name: Optional[str] = None
    cve_id: Optional[str] = None
    cvss_score: Optional[float] = None
    raw_data: Optional[dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "scanner_id": self.scanner_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "category": self.category,
            "description": self.description,
            "recommendation": self.recommendation,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "resource_name": self.resource_name,
            "cve_id": self.cve_id,
            "cvss_score": self.cvss_score,
            "raw_data": self.raw_data,
        }


class BaseScanner(ABC):
    """Abstract base class for all scanners."""

    @property
    @abstractmethod
    def scanner_id(self) -> str:
        """Unique scanner identifier."""
        pass

    @property
    @abstractmethod
    def scanner_name(self) -> str:
        """Human-readable scanner name."""
        pass

    @property
    @abstractmethod
    def supported_file_types(self) -> list[str]:
        """File types this scanner can analyze."""
        pass

    @abstractmethod
    async def scan(self, repo_path: str, file_paths: list[str]) -> list[ScannerFinding]:
        """
        Run scanner against repository.

        Args:
            repo_path: Path to cloned repository
            file_paths: List of files to scan

        Returns:
            List of findings
        """
        pass

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if scanner is available and configured."""
        pass

    @abstractmethod
    def parse_output(self, raw_output: str) -> list[ScannerFinding]:
        """Parse scanner output into unified findings."""
        pass


class ScannerResult:
    """Result from scanner execution."""

    def __init__(
        self,
        scanner_id: str,
        findings: list[ScannerFinding],
        success: bool = True,
        error: Optional[str] = None,
        duration_seconds: float = 0.0,
    ):
        self.scanner_id = scanner_id
        self.findings = findings
        self.success = success
        self.error = error
        self.duration_seconds = duration_seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "scanner_id": self.scanner_id,
            "findings": [f.to_dict() for f in self.findings],
            "findings_count": len(self.findings),
            "success": self.success,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
        }
