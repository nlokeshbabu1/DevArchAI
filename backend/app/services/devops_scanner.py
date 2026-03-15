"""
DevOps Production Readiness Scanner

Scans repositories for DevOps production readiness issues using file-type based rule filtering.
Only applies rules to relevant file types (e.g., Terraform rules only to .tf files).
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import structlog

from app.parsers.base import ParsedFile, ParserRegistry
from app.parsers.cicd import CICDParser
from app.parsers.dockerfile import DockerfileParser
from app.parsers.kubernetes import KubernetesParser
from app.parsers.terraform import TerraformParser
from app.rules.base import RuleFinding, RuleRegistry, Severity
from app.rules.file_type_filter import (
    categorize_files,
)

logger = structlog.get_logger(__name__)


@dataclass
class ScannerSummary:
    """Summary of scanner findings."""

    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    files_scanned: int = 0
    files_ignored: int = 0
    rules_executed: int = 0


@dataclass
class ScannerReport:
    """Complete scanner report."""

    repo_path: str
    findings: list[RuleFinding] = field(default_factory=list)
    summary: ScannerSummary = field(default_factory=ScannerSummary)
    files_by_type: dict[str, list[str]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def format_output(self) -> str:
        """Format report as human-readable output."""
        lines = []
        lines.append("=" * 70)
        lines.append("DevOps Production Readiness Scanner Report")
        lines.append("=" * 70)
        lines.append(f"\nRepository: {self.repo_path}")
        lines.append(f"Files Scanned: {self.summary.files_scanned}")
        lines.append(f"Files Ignored: {self.summary.files_ignored}")
        lines.append(f"Total Findings: {self.summary.total_findings}")
        lines.append("")

        # Severity breakdown
        if self.summary.total_findings > 0:
            lines.append("Findings by Severity:")
            if self.summary.critical_count > 0:
                lines.append(f"  🔴 Critical: {self.summary.critical_count}")
            if self.summary.high_count > 0:
                lines.append(f"  🟠 High: {self.summary.high_count}")
            if self.summary.medium_count > 0:
                lines.append(f"  🟡 Medium: {self.summary.medium_count}")
            if self.summary.low_count > 0:
                lines.append(f"  🟢 Low: {self.summary.low_count}")
            if self.summary.info_count > 0:
                lines.append(f"  ℹ️  Info: {self.summary.info_count}")
            lines.append("")

            # Group findings by severity
            findings_by_severity = defaultdict(list)
            for finding in self.findings:
                findings_by_severity[finding.severity.value].append(finding)

            # Output findings by severity
            severity_order = ["critical", "high", "medium", "low", "info"]
            severity_labels = {
                "critical": "Critical",
                "high": "High",
                "medium": "Medium",
                "low": "Low",
                "info": "Info",
            }

            for severity in severity_order:
                severity_findings = findings_by_severity.get(severity, [])
                if severity_findings:
                    lines.append(f"{severity_labels[severity]}:")
                    for finding in severity_findings:
                        file_display = self._get_relative_path(finding.file_path)
                        lines.append(f"  - {finding.rule_name} ({file_display})")
                    lines.append("")
        else:
            lines.append("✅ No issues found!")
            lines.append("")

        # Files by type
        if self.files_by_type:
            lines.append("Files Analyzed by Type:")
            for file_type, files in self.files_by_type.items():
                if files and file_type not in ["ignored", "other"]:
                    lines.append(f"  {file_type.capitalize()}: {len(files)} files")
            lines.append("")

        # Errors
        if self.errors:
            lines.append("Errors:")
            for error in self.errors:
                lines.append(f"  ❌ {error}")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def _get_relative_path(self, file_path: str) -> str:
        """Get relative path for display."""
        if not file_path:
            return "unknown"
        # Remove repo path prefix
        if self.repo_path in file_path:
            return file_path.replace(self.repo_path + "/", "")
        return file_path


class DevOpsScanner:
    """
    DevOps production readiness scanner with file-type based rule filtering.

    This scanner:
    1. Detects file types (Terraform, Docker, K8s, CI/CD)
    2. Ignores documentation files (.md, etc.)
    3. Applies rules only to relevant file types
    4. Deduplicates findings
    5. Produces clean, actionable output
    """

    def __init__(self):
        self.rule_registry = RuleRegistry()
        self.parser_registry = self._setup_parsers()
        self.findings_cache: dict[str, list[RuleFinding]] = {}

    def _setup_parsers(self) -> ParserRegistry:
        """Initialize file parsers."""
        registry = ParserRegistry()
        registry.register(TerraformParser())
        registry.register(KubernetesParser())
        registry.register(DockerfileParser())
        registry.register(CICDParser())
        return registry

    def scan_repository(self, repo_path: str) -> ScannerReport:
        """
        Scan a repository for DevOps production readiness issues.

        Args:
            repo_path: Path to the repository

        Returns:
            ScannerReport with findings
        """
        logger.info("Starting repository scan", repo_path=repo_path)

        report = ScannerReport(repo_path=repo_path)
        all_findings: list[RuleFinding] = []

        # Collect all files
        all_files = self._collect_files(repo_path)

        # Categorize files by type
        categorized = categorize_files(all_files)
        report.files_by_type = categorized

        # Update summary
        report.summary.files_scanned = sum(
            len(files) for files in categorized.values()
            if files and len(files) > 0
        )
        report.summary.files_ignored = len(categorized.get("ignored", []))

        # Scan each file type with relevant rules
        for file_type, files in categorized.items():
            if not files or file_type in ["ignored", "other"]:
                continue

            logger.info(f"Scanning {file_type} files", count=len(files))
            findings = self._scan_files_by_type(repo_path, files, file_type)
            all_findings.extend(findings)

        # Deduplicate findings
        deduplicated = self._deduplicate_findings(all_findings)
        report.findings = deduplicated

        # Update summary
        report.summary.total_findings = len(deduplicated)
        for finding in deduplicated:
            if finding.severity == Severity.CRITICAL:
                report.summary.critical_count += 1
            elif finding.severity == Severity.HIGH:
                report.summary.high_count += 1
            elif finding.severity == Severity.MEDIUM:
                report.summary.medium_count += 1
            elif finding.severity == Severity.LOW:
                report.summary.low_count += 1
            else:
                report.summary.info_count += 1

        logger.info(
            "Scan complete",
            total_findings=report.summary.total_findings,
            files_scanned=report.summary.files_scanned,
        )

        return report

    def _collect_files(self, repo_path: str) -> list[str]:
        """Collect all files from repository."""
        files = []
        repo = Path(repo_path)

        for file_path in repo.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip git directory
            if ".git" in str(file_path) and ".github" not in str(file_path):
                continue

            # Skip common non-essential directories
            skip_dirs = {"node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", "dist", "build"}
            if any(dir_name in str(file_path) for dir_name in skip_dirs):
                continue

            files.append(str(file_path))

        return files

    def _scan_files_by_type(
        self,
        repo_path: str,
        files: list[str],
        file_type: str,
    ) -> list[RuleFinding]:
        """
        Scan files of a specific type with relevant rules.

        Args:
            repo_path: Path to repository
            files: List of file paths
            file_type: Type of files (terraform, dockerfile, kubernetes, cicd)

        Returns:
            List of findings
        """
        findings = []

        for file_path in files:
            try:
                # Parse file
                parsed = self._parse_file(repo_path, file_path, file_type)
                if not parsed:
                    continue

                # Extract resources
                resources = self._extract_resources(parsed, file_type)

                # Run rules for this file type
                file_findings = self.rule_registry.evaluate_all(
                    resources=resources,
                    file_path=file_path,
                    file_type=file_type,
                )

                findings.extend(file_findings)

            except Exception as e:
                logger.warning(f"Failed to scan file {file_path}: {str(e)}")

        return findings

    def _parse_file(
        self,
        repo_path: str,
        file_path: str,
        file_type: str,
    ) -> Optional[ParsedFile]:
        """Parse a file using the appropriate parser."""
        try:
            full_path = Path(repo_path) / file_path
            content = full_path.read_text(encoding="utf-8")

            parsed = self.parser_registry.parse_file(full_path, content)
            return parsed

        except Exception as e:
            logger.warning(f"Failed to parse file {file_path}: {str(e)}")
            return None

    def _extract_resources(
        self,
        parsed_file: ParsedFile,
        file_type: str,
    ) -> list[dict[str, Any]]:
        """Extract resources from parsed file for rule evaluation."""
        if not parsed_file:
            return []

        resources = []
        parsed_data = parsed_file.parsed_data

        if isinstance(parsed_data, dict):
            if file_type == "terraform":
                # Extract Terraform resources
                for resource in parsed_data.get("resources", []):
                    resource["file_type"] = "terraform"
                    resource["file_path"] = parsed_file.file_path
                    resources.append(resource)

                # Add backend configs
                for backend in parsed_data.get("backends", []):
                    resources.append({
                        "file_type": "terraform",
                        "resource_type": "backend",
                        "properties": backend,
                        "file_path": parsed_file.file_path,
                    })

                # Add providers
                for provider in parsed_data.get("providers", []):
                    resources.append({
                        "file_type": "terraform",
                        "resource_type": "provider",
                        "properties": provider,
                        "file_path": parsed_file.file_path,
                    })

            elif file_type == "kubernetes":
                # Extract Kubernetes resources
                for deployment in parsed_data.get("deployments", []):
                    deployment["file_type"] = "kubernetes"
                    deployment["file_path"] = parsed_file.file_path
                    resources.append(deployment)

                for hpa in parsed_data.get("hpa", []):
                    hpa["file_type"] = "kubernetes"
                    hpa["file_path"] = parsed_file.file_path
                    resources.append(hpa)

            elif file_type == "dockerfile":
                # Dockerfile is a single resource
                parsed_data["file_type"] = "dockerfile"
                parsed_data["file_path"] = parsed_file.file_path
                resources.append(parsed_data)

            elif file_type == "cicd":
                # CI/CD is a single resource
                parsed_data["file_type"] = "cicd"
                parsed_data["file_path"] = parsed_file.file_path
                resources.append(parsed_data)

        return resources

    def _deduplicate_findings(self, findings: list[RuleFinding]) -> list[RuleFinding]:
        """
        Deduplicate findings by rule_id and file_path.

        Groups findings by rule and file, reporting once per unique combination.
        """
        seen = set()
        unique = []

        for finding in findings:
            # Create unique key
            key = (
                finding.rule_id,
                finding.file_path or "",
                finding.resource_name or "",
            )

            if key not in seen:
                seen.add(key)
                unique.append(finding)

        return unique


def scan_repository(repo_path: str) -> ScannerReport:
    """
    Convenience function to scan a repository.

    Args:
        repo_path: Path to repository

    Returns:
        ScannerReport with findings
    """
    scanner = DevOpsScanner()
    return scanner.scan_repository(repo_path)


def print_scan_report(report: ScannerReport) -> None:
    """Print scanner report to console."""
    print(report.format_output())
