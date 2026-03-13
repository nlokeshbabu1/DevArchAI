"""Rule runner for executing rule evaluations."""

from typing import Any, Optional

from app.core.logging import get_logger
from app.rule_engine.base import Category, RuleFinding, RuleRegistry, Severity

logger = get_logger(__name__)


class RuleRunner:
    """Executes rule evaluations against parsed resources."""

    def __init__(self, registry: Optional[RuleRegistry] = None):
        self.registry = registry or RuleRegistry()

    def evaluate(
        self,
        resources: list[dict[str, Any]],
        file_path: str,
        file_type: Optional[str] = None,
    ) -> list[RuleFinding]:
        """
        Evaluate all applicable rules against resources.

        Args:
            resources: Parsed resources to evaluate
            file_path: Path to the file being evaluated
            file_type: Type of file (terraform, kubernetes, dockerfile, cicd)

        Returns:
            List of rule findings
        """
        logger.debug(
            "Running rule evaluation",
            file_path=file_path,
            file_type=file_type,
            resource_count=len(resources),
        )

        findings = self.registry.evaluate_all(resources, file_path, file_type)

        logger.debug(
            "Rule evaluation complete",
            file_path=file_path,
            findings_count=len(findings),
        )

        return findings

    def evaluate_batch(
        self,
        parsed_files: list[dict[str, Any]],
    ) -> list[RuleFinding]:
        """
        Evaluate rules against multiple parsed files.

        Args:
            parsed_files: List of dicts with keys: file_path, file_type, resources

        Returns:
            Combined list of all findings
        """
        all_findings = []

        for parsed_file in parsed_files:
            file_path = parsed_file.get("file_path", "unknown")
            file_type = parsed_file.get("file_type")
            resources = parsed_file.get("resources", [])

            findings = self.evaluate(resources, file_path, file_type)
            all_findings.extend(findings)

        logger.info(
            "Batch rule evaluation complete",
            files_processed=len(parsed_files),
            total_findings=len(all_findings),
        )

        return all_findings

    def get_findings_summary(self, findings: list[RuleFinding]) -> dict[str, Any]:
        """Generate a summary of findings."""
        summary = {
            "total": len(findings),
            "by_severity": {},
            "by_category": {},
            "by_rule": {},
        }

        # Count by severity
        for severity in Severity:
            count = sum(1 for f in findings if f.severity == severity)
            summary["by_severity"][severity.value] = count

        # Count by category
        for category in Category:
            count = sum(1 for f in findings if f.category == category)
            summary["by_category"][category.value] = count

        # Count by rule
        rule_counts: dict[str, int] = {}
        for finding in findings:
            rule_counts[finding.rule_id] = rule_counts.get(finding.rule_id, 0) + 1
        summary["by_rule"] = rule_counts

        return summary

    def filter_findings(
        self,
        findings: list[RuleFinding],
        min_severity: Optional[Severity] = None,
        categories: Optional[list[Category]] = None,
        file_type: Optional[str] = None,
    ) -> list[RuleFinding]:
        """Filter findings by criteria."""
        filtered = findings

        if min_severity:
            severity_order = {
                Severity.INFO: 0,
                Severity.LOW: 1,
                Severity.MEDIUM: 2,
                Severity.HIGH: 3,
                Severity.CRITICAL: 4,
            }
            min_level = severity_order.get(min_severity, 0)
            filtered = [f for f in filtered if severity_order.get(f.severity, 0) >= min_level]

        if categories:
            filtered = [f for f in filtered if f.category in categories]

        if file_type and findings:
            # Filter by file path containing the file type
            filtered = [f for f in filtered if f.file_path and file_type in f.file_path.lower()]

        return filtered
