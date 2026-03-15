"""Scanner orchestrator for running multiple scanners."""

import asyncio
import time
from pathlib import Path
from typing import Any, Optional

import structlog

from app.engines.scanner_engine import BaseScanner, ScannerFinding, ScannerResult
from app.services.scanners.checkov_runner import CheckovScanner
from app.services.scanners.trivy_runner import TrivyScanner

logger = structlog.get_logger(__name__)


class ScannerOrchestrator:
    """Orchestrates multiple security scanners."""

    def __init__(self, scanners: Optional[list[BaseScanner]] = None):
        self.scanners = scanners or self._create_default_scanners()
        self._scanner_status: dict[str, bool] = {}

    def _create_default_scanners(self) -> list[BaseScanner]:
        """Create default scanner instances."""
        return [
            TrivyScanner(),
            CheckovScanner(),
        ]

    async def initialize(self) -> dict[str, bool]:
        """Check availability of all scanners."""
        for scanner in self.scanners:
            available = await scanner.check_availability()
            self._scanner_status[scanner.scanner_id] = available
            logger.info(
                "Scanner availability check",
                scanner_id=scanner.scanner_id,
                available=available,
            )
        return self._scanner_status

    async def scan_repository(
        self,
        repo_path: str,
        file_paths: Optional[list[str]] = None,
        timeout_seconds: int = 300,
    ) -> list[ScannerResult]:
        """
        Run all available scanners against repository.

        Args:
            repo_path: Path to cloned repository
            file_paths: Optional list of files to scan
            timeout_seconds: Timeout per scanner

        Returns:
            List of scanner results
        """
        if not file_paths:
            file_paths = self._collect_scannable_files(repo_path)

        # Create scan tasks for available scanners
        tasks = []
        for scanner in self.scanners:
            if self._scanner_status.get(scanner.scanner_id, False):
                tasks.append(self._run_scanner(scanner, repo_path, file_paths, timeout_seconds))

        if not tasks:
            logger.warning("No scanners available")
            return []

        # Run scanners in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        scanner_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Scanner execution failed", error=str(result))
            elif isinstance(result, ScannerResult):
                scanner_results.append(result)

        return scanner_results

    async def _run_scanner(
        self,
        scanner: BaseScanner,
        repo_path: str,
        file_paths: list[str],
        timeout_seconds: int,
    ) -> ScannerResult:
        """Run a single scanner."""
        start_time = time.time()

        try:
            findings = await scanner.scan(repo_path, file_paths, timeout_seconds)
            duration = time.time() - start_time

            return ScannerResult(
                scanner_id=scanner.scanner_id,
                findings=findings,
                success=True,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.exception("Scanner failed", scanner_id=scanner.scanner_id, error=str(e))

            return ScannerResult(
                scanner_id=scanner.scanner_id,
                findings=[],
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    def _collect_scannable_files(self, repo_path: str) -> list[str]:
        """Collect all scannable files from repository."""
        scannable_extensions = {
            ".tf", ".tf.json", ".tfvars",
            ".yaml", ".yml",
            "Dockerfile", "Containerfile",
            "docker-compose.yml", "docker-compose.yaml",
            "package.json", "requirements.txt", "Pipfile",
        }

        scannable_filenames = {
            "Dockerfile", "Containerfile",
            "docker-compose.yml", "docker-compose.yaml",
        }

        files = []
        repo = Path(repo_path)

        for file_path in repo.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip git and node_modules
            if ".git" in str(file_path) and ".github" not in str(file_path):
                continue
            if "node_modules" in str(file_path):
                continue
            if "__pycache__" in str(file_path):
                continue

            # Check if file is scannable
            if file_path.name in scannable_filenames or file_path.suffix in scannable_extensions:
                files.append(str(file_path))

        return files

    def aggregate_findings(
        self,
        results: list[ScannerResult],
    ) -> dict[str, Any]:
        """
        Aggregate findings from all scanners.

        Args:
            results: List of scanner results

        Returns:
            Aggregated findings with deduplication
        """
        all_findings: list[ScannerFinding] = []
        scanner_stats = {}

        for result in results:
            scanner_stats[result.scanner_id] = {
                "findings_count": len(result.findings),
                "success": result.success,
                "duration_seconds": result.duration_seconds,
                "error": result.error,
            }
            all_findings.extend(result.findings)

        # Deduplicate findings
        unique_findings = self._deduplicate_findings(all_findings)

        # Group by severity
        by_severity = {}
        for finding in unique_findings:
            severity = finding.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(finding)

        # Group by category
        by_category = {}
        for finding in unique_findings:
            category = finding.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(finding)

        return {
            "total_findings": len(unique_findings),
            "scanner_stats": scanner_stats,
            "by_severity": {k: len(v) for k, v in by_severity.items()},
            "by_category": {k: len(v) for k, v in by_category.items()},
            "findings": unique_findings,
            "findings_by_severity": by_severity,
            "findings_by_category": by_category,
        }

    def _deduplicate_findings(self, findings: list[ScannerFinding]) -> list[ScannerFinding]:
        """Remove duplicate findings."""
        seen = set()
        unique = []

        for finding in findings:
            # Create unique key based on file, line, and rule
            key = (
                finding.file_path,
                finding.line_number,
                finding.rule_id,
                finding.description[:50] if finding.description else "",
            )

            if key not in seen:
                seen.add(key)
                unique.append(finding)

        return unique

    def get_available_scanners(self) -> list[str]:
        """Get list of available scanner IDs."""
        return [
            scanner_id
            for scanner_id, available in self._scanner_status.items()
            if available
        ]
