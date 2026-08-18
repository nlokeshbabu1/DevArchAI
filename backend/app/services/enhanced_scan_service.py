"""Enhanced scan service with external scanners and rule engine — DEPRECATED.

This service is NOT used by any production code path (never imported).
The production scan path uses:
  - SyncScanService (app.workers.tasks.scan_repository)
  - ScanService (app.services.scan_service)

DO NOT add new production code that uses this service.
"""

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog

from app.config import settings
from app.engines.ai_recommendation_engine import AIRecommendationEngine
from app.engines.rule_engine import YAMLRuleEngine
from app.engines.scanner_orchestrator import ScannerOrchestrator
from app.parsers.base import ParsedFile, ParserRegistry
from app.parsers.cicd import CICDParser
from app.parsers.dockerfile import DockerfileParser
from app.parsers.kubernetes import KubernetesParser
from app.parsers.terraform import TerraformParser
from app.rule_engine.base import Category, RuleFinding, Severity
from app.scoring.engine import ScoringEngine

logger = structlog.get_logger(__name__)


class EnhancedScanService:
    """
    Enhanced scan service integrating external scanners and rule engine.

    Flow:
    1. Run external scanners (Trivy, Checkov)
    2. Parse files and run internal rules
    3. Aggregate all findings
    4. Calculate scores
    5. Generate AI recommendations
    """

    def __init__(
        self,
        db_session: Any,
        include_ai_explanations: bool = True,
        rules_dir: str | None = None,
    ):
        self.db = db_session
        self.include_ai_explanations = include_ai_explanations
        self.rules_dir = rules_dir or str(Path(__file__).parent.parent / "rules" / "yaml")

        # Initialize engines
        self.scanner_orchestrator = ScannerOrchestrator()
        self.rule_engine = YAMLRuleEngine(rules_dir=self.rules_dir)
        self.scoring_engine = ScoringEngine()
        self.ai_engine = AIRecommendationEngine()
        self.parser_registry = self._setup_parsers()

    def _setup_parsers(self) -> ParserRegistry:
        """Initialize parsers."""
        registry = ParserRegistry()
        registry.register(TerraformParser())
        registry.register(KubernetesParser())
        registry.register(DockerfileParser())
        registry.register(CICDParser())
        return registry

    async def execute_enhanced_scan(
        self,
        repo_path: str,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> dict[str, Any]:
        """
        Execute enhanced scan with external scanners and rules.

        Args:
            repo_path: Path to cloned repository
            progress_callback: Optional callback for progress updates

        Returns:
            Scan results with findings, scores, and recommendations
        """
        start_time = time.time()
        results = {
            "findings": [],
            "scores": None,
            "ai_summary": None,
            "scanner_results": {},
            "rule_stats": {},
        }

        try:
            self._update_progress(progress_callback, 10, "Initializing scanners...")

            # Initialize external scanners
            scanner_status = await self.scanner_orchestrator.initialize()
            logger.info("Scanner initialization complete", status=scanner_status)

            self._update_progress(progress_callback, 20, "Collecting files...")

            # Collect files to scan
            file_paths = self._collect_files(repo_path)
            logger.info("Files collected for scanning", count=len(file_paths))

            self._update_progress(progress_callback, 30, "Running external scanners...")

            # Run external scanners
            scanner_results = await self.scanner_orchestrator.scan_repository(
                repo_path=repo_path,
                file_paths=file_paths,
                timeout_seconds=settings.ANALYSIS_TIMEOUT_SECONDS,
            )

            # Aggregate scanner findings
            aggregated = self.scanner_orchestrator.aggregate_findings(scanner_results)
            results["scanner_results"] = {
                "stats": aggregated["scanner_stats"],
                "by_severity": aggregated["by_severity"],
                "by_category": aggregated["by_category"],
            }

            # Convert scanner findings to internal format
            scanner_findings = self._convert_scanner_findings(aggregated["findings"])
            results["findings"].extend(scanner_findings)

            logger.info(
                "External scanners completed",
                total_findings=aggregated["total_findings"],
            )

            self._update_progress(progress_callback, 50, "Parsing files...")

            # Parse files
            parsed_files = self._parse_files(repo_path)
            logger.info("File parsing complete", parsed_count=len(parsed_files))

            self._update_progress(progress_callback, 60, "Running rule engine...")

            # Run internal rules
            rule_findings = self._run_internal_rules(parsed_files)
            results["findings"].extend(rule_findings)
            results["rule_stats"] = self.rule_engine.get_rule_count()

            logger.info(
                "Rule engine completed",
                findings_count=len(rule_findings),
            )

            self._update_progress(progress_callback, 75, "Calculating scores...")

            # Calculate scores
            all_findings = results["findings"]
            scores = self.scoring_engine.calculate_scores(all_findings)
            results["scores"] = scores

            self._update_progress(progress_callback, 85, "Generating AI recommendations...")

            # Generate AI recommendations
            if self.include_ai_explanations:
                findings_dict = [self._finding_to_dict(f) for f in all_findings[:50]]
                recommendations = await self.ai_engine.generate_recommendations(findings_dict)

                # Add AI explanations to findings
                for rec in recommendations:
                    for finding in all_findings:
                        if finding.rule_id == rec.rule_id:
                            finding.ai_explanation = rec.explanation
                            finding.recommendation = "; ".join(rec.remediation_steps) or finding.recommendation

                # Generate executive summary
                category_scores = {
                    cs.category.value: cs.score for cs in scores.category_scores
                }
                results["ai_summary"] = await self.ai_engine.generate_executive_summary(
                    scores.score,
                    findings_dict,
                    category_scores,
                )

            self._update_progress(progress_callback, 95, "Finalizing results...")

            # Calculate duration
            analysis_duration = time.time() - start_time
            results["analysis_duration_seconds"] = analysis_duration

            logger.info(
                "Enhanced scan completed",
                duration=analysis_duration,
                total_findings=len(all_findings),
                overall_score=scores.score,
            )

            self._update_progress(progress_callback, 100, "Scan complete")

        except Exception as e:
            logger.exception("Enhanced scan failed", error=str(e))
            raise

        return results

    def _collect_files(self, repo_path: str) -> list[str]:
        """Collect all files in repository."""
        files = []
        repo = Path(repo_path)

        for file_path in repo.rglob("*"):
            if not file_path.is_file():
                continue
            if ".git" in str(file_path) and ".github" not in str(file_path):
                continue
            if "node_modules" in str(file_path):
                continue
            if "__pycache__" in str(file_path):
                continue

            files.append(str(file_path))

        return files

    def _parse_files(self, repo_path: str) -> list[ParsedFile]:
        """Parse all analyzable files."""
        parsed_files = []
        repo = Path(repo_path)

        for file_path in repo.rglob("*"):
            if not file_path.is_file():
                continue
            if ".git" in str(file_path) and ".github" not in str(file_path):
                continue
            if "node_modules" in str(file_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                parsed = self.parser_registry.parse_file(file_path, content)
                if parsed:
                    parsed_files.append(parsed)
            except Exception as e:
                logger.warning("Failed to parse file", file=str(file_path), error=str(e))

        return parsed_files

    def _run_internal_rules(self, parsed_files: list[ParsedFile]) -> list[RuleFinding]:
        """Run internal rules against parsed files."""
        all_findings = []

        for parsed_file in parsed_files:
            resources = self._extract_resources(parsed_file)
            file_type = parsed_file.file_type

            findings = self.rule_engine.evaluate(
                resources=resources,
                file_path=str(parsed_file.file_path),
                file_type=file_type,
            )
            all_findings.extend(findings)

        return all_findings

    def _extract_resources(self, parsed_file: ParsedFile) -> list[dict[str, Any]]:
        """Extract resources from parsed file for rule evaluation."""
        resources = []
        data = parsed_file.parsed_data

        if parsed_file.file_type == "terraform":
            for resource in data.get("resources", []):
                resource["file_path"] = str(parsed_file.file_path)
                resource["file_type"] = "terraform"
                resources.append(resource)

        elif parsed_file.file_type == "kubernetes":
            for deployment in data.get("deployments", []):
                deployment["file_path"] = str(parsed_file.file_path)
                deployment["file_type"] = "kubernetes"
                deployment["kind"] = "Deployment"
                resources.append(deployment)

        elif parsed_file.file_type == "dockerfile":
            data["file_path"] = str(parsed_file.file_path)
            data["file_type"] = "dockerfile"
            resources.append(data)

        elif parsed_file.file_type == "cicd":
            data["file_path"] = str(parsed_file.file_path)
            data["file_type"] = "cicd"
            resources.append(data)

        return resources

    def _convert_scanner_findings(
        self,
        scanner_findings: list[Any],
    ) -> list[RuleFinding]:
        """Convert scanner findings to internal RuleFinding format."""
        findings = []

        for finding in scanner_findings:
            # Get severity from scanner finding
            severity_value = finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)

            findings.append(
                RuleFinding(
                    rule_id=finding.rule_id,
                    rule_name=finding.rule_name,
                    severity=Severity(severity_value),
                    category=Category("security"),  # Scanner findings are mostly security
                    description=finding.description,
                    recommendation=finding.recommendation,
                    file_path=finding.file_path,
                    line_number=finding.line_number,
                    confidence=finding.cvss_score / 10.0 if finding.cvss_score else 1.0,
                )
            )

        return findings

    def _finding_to_dict(self, finding: RuleFinding) -> dict[str, Any]:
        """Convert RuleFinding to dictionary."""
        return {
            "rule_id": finding.rule_id,
            "rule_name": finding.rule_name,
            "severity": finding.severity.value,
            "category": finding.category.value,
            "description": finding.description,
            "recommendation": finding.recommendation,
            "file_path": finding.file_path,
            "scanner_name": getattr(finding, 'scanner_name', None),
            "scanner_rule_id": getattr(finding, 'scanner_rule_id', None),
            "package": getattr(finding, 'package', None),
            "installed_version": getattr(finding, 'installed_version', None),
            "fixed_version": getattr(finding, 'fixed_version', None),
            "cve": getattr(finding, 'cve', None),
            "cwe": getattr(finding, 'cwe', None),
            "references": getattr(finding, 'references', None),
            "evidence": getattr(finding, 'evidence', None),
        }

    def _update_progress(
        self,
        callback: Callable[[int, str], None] | None,
        progress: int,
        message: str,
    ):
        """Update progress if callback provided."""
        if callback:
            callback(progress, message)
