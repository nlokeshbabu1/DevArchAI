"""Scan service for orchestrating repository analysis with stack detection."""

import json
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_engine.explanation_engine import ExplanationEngine
from app.config import settings
from app.core.logging import get_logger
from app.models.finding import Category, Finding
from app.models.report import Report
from app.models.scan import Scan, ScanStatus
from app.parsers.base import ParserRegistry
from app.parsers.cicd import CICDParser
from app.parsers.dockerfile import DockerfileParser
from app.parsers.kubernetes import KubernetesParser
from app.parsers.terraform import TerraformParser
from app.rule_engine.base import RuleFinding, RuleRegistry
from app.scoring.engine import ScoringEngine
from app.services.ai_recommendation_service import enqueue_ai_analysis_for_scan
from app.services.findings_deduplicator import FindingsDeduplicator
from app.services.findings_enricher import FindingsEnricher
from app.services.report_service import ReportService
from app.services.technology_detector import TechnologyStack, detect_technology_stack
from app.utils.repository_scanner import RepositoryScanner

logger = get_logger(__name__)


class ScanService:
    """Service for orchestrating repository scans with stack-based execution."""

    def __init__(
        self,
        db: AsyncSession,
        include_ai_explanations: bool = True,
    ):
        self.db = db
        self.include_ai_explanations = include_ai_explanations
        self.rule_registry = RuleRegistry()
        self.scoring_engine = ScoringEngine()
        self.repo_scanner = RepositoryScanner()
        self.parser_registry = self._setup_parsers()
        self.explanation_engine = ExplanationEngine() if include_ai_explanations else None
        self.detected_stack: TechnologyStack | None = None
        self.deduplicator = FindingsDeduplicator()
        self.enricher = FindingsEnricher()
        self.report_service = ReportService()
        logger.info("ScanService initialized", ai_explanations=include_ai_explanations)

    def _setup_parsers(self) -> ParserRegistry:
        """Initialize and register all parsers."""
        registry = ParserRegistry()
        registry.register(TerraformParser())
        registry.register(KubernetesParser())
        registry.register(DockerfileParser())
        registry.register(CICDParser())
        logger.info("Parsers registered", parsers=["terraform", "kubernetes", "dockerfile", "cicd"])
        return registry

    async def analyze_repository_sync(
        self,
        repo_url: str,
        branch: str = "main",
        commit_hash: str | None = None,
    ) -> dict[str, Any]:
        """
        Synchronous repository analysis with stack detection.

        This endpoint:
        1. Clones the repository
        2. Detects the technology stack
        3. Runs only relevant scanners
        4. Generates AI explanations
        5. Calculates scores
        6. Returns detailed findings with stack info

        Args:
            repo_url: GitHub repository URL
            branch: Branch to analyze
            commit_hash: Specific commit (optional)

        Returns:
            Analysis results with findings and detected stack
        """
        logger.info("Starting synchronous repository analysis", repo_url=repo_url, branch=branch)
        start_time = time.time()
        repo_path = None
        findings = []

        try:
            # Clone repository
            logger.info("Cloning repository", repo_url=repo_url)
            repo_path, _ = self.repo_scanner.clone_repository(
                repo_url, branch, commit_hash, settings.GITHUB_TOKEN
            )
            logger.info("Repository cloned", path=repo_path)

            # Parse files
            logger.info("Loading and parsing files")
            parsed_files = self._load_and_parse_files(Path(repo_path))
            logger.info("Files parsed", count=len(parsed_files), files=[f.file_path for f in parsed_files])

            if not parsed_files:
                raise ValueError("No analyzable files found")

            # Detect technology stack FIRST
            logger.info("Detecting technology stack")
            file_paths = [str(f.file_path) for f in parsed_files]
            self.detected_stack = detect_technology_stack(file_paths)
            detected_techs = self.detected_stack.get_detected_technologies()
            logger.info("Technology stack detected", stack=",".join(detected_techs) if detected_techs else "none")

            # Extract resources
            logger.info("Extracting resources from detected technologies")
            resources = self._extract_resources(parsed_files)
            logger.info("Resources extracted", count=len(resources))

            # Run rules
            logger.info("Running rule engine for detected technologies", technologies=detected_techs)
            findings = self._run_rules(resources, parsed_files)
            logger.info("Rule engine complete", findings_count=len(findings), findings=[f.rule_id for f in findings])

            # AI explanations
            if self.include_ai_explanations and self.explanation_engine and findings:
                logger.info("Generating AI explanations", findings_count=len(findings))
                findings = await self.explanation_engine.explain_findings_batch(findings, max_findings=20)
                logger.info("AI explanations generated")

            # Calculate scores
            logger.info("Calculating scores")
            scores = self.scoring_engine.calculate_scores(findings)
            logger.info("Scores calculated", overall=scores.score, grade=scores.grade)

            analysis_duration = time.time() - start_time

            return {
                "repo_url": repo_url,
                "branch": branch,
                "files_analyzed": len(parsed_files),
                "resources_found": len(resources),
                "detected_stack": self.detected_stack.to_dict(),
                "findings": [self._finding_to_dict(f) for f in findings],
                "scores": {
                    "overall": scores.score,
                    "grade": scores.grade,
                    "category_scores": {cs.category.value: cs.score for cs in scores.category_scores},
                },
                "duration_seconds": analysis_duration,
                "success": True,
            }

        except Exception as e:
            logger.exception("Synchronous analysis failed", error=str(e))
            return {
                "repo_url": repo_url,
                "error": str(e),
                "success": False,
            }
        finally:
            if repo_path:
                self.repo_scanner.cleanup(repo_path)

    def _finding_to_dict(self, finding: RuleFinding) -> dict[str, Any]:
        """Convert RuleFinding to dictionary."""
        return {
            "rule_id": finding.rule_id,
            "rule_name": finding.rule_name,
            "severity": finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
            "category": finding.category.value if hasattr(finding.category, 'value') else str(finding.category),
            "description": finding.description,
            "recommendation": finding.recommendation,
            "file_path": finding.file_path,
            "line_number": finding.line_number,
            "ai_explanation": finding.ai_explanation,
            "impact_analysis": finding.impact_analysis,
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

    async def execute_scan(
        self,
        scan: Scan,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> Scan:
        """
        Execute a complete scan workflow.

        Args:
            scan: Scan model instance
            progress_callback: Optional callback for progress updates

        Returns:
            Updated scan with results
        """
        start_time = time.time()
        repo_path = None

        try:
            # Update status to processing
            scan.status = ScanStatus.PROCESSING
            scan.started_at = datetime.utcnow()
            await self.db.commit()

            self._update_progress(progress_callback, 10, "Cloning repository...")

            # Clone repository
            repo_path, repo_info = self.repo_scanner.clone_repository(
                scan.repository_url,
                scan.branch,
                scan.commit_hash,
                settings.GITHUB_TOKEN,
            )

            self._update_progress(progress_callback, 30, "Loading files...")

            # Load and parse files
            parsed_files = self._load_and_parse_files(Path(repo_path))

            if not parsed_files:
                raise ValueError("No analyzable files found in repository")

            logger.info(
                "Files loaded for analysis",
                file_count=len(parsed_files),
            )

            self._update_progress(progress_callback, 50, "Running rule engine...")

            # Extract resources and run rules
            resources = self._extract_resources(parsed_files)
            rule_findings = self._run_rules(resources, parsed_files)

            logger.info(
                "Rule evaluation complete",
                findings_count=len(rule_findings),
            )

            self._update_progress(progress_callback, 65, "Preparing remediation guidance...")

            # Keep the main scan path static and deterministic; AI suggestions are generated later.
            self._update_progress(progress_callback, 70, "Building static recommendations...")
            from app.services.findings_enricher import enrich_findings
            rule_findings = enrich_findings(rule_findings)
            logger.info(
                "Findings enriched",
                findings_count=len(rule_findings),
                with_fix_examples=sum(1 for f in rule_findings if f.fix_example),
            )

            self._update_progress(progress_callback, 80, "Calculating scores...")

            # Calculate scores
            scores = self.scoring_engine.calculate_scores(rule_findings)

            self._update_progress(progress_callback, 90, "Saving results...")

            # Save findings to database
            await self._save_findings(scan.id, rule_findings)

            # Create report
            await self._create_report(
                scan=scan,
                rule_findings=rule_findings,
                scores=scores,
                files_analyzed=[f.file_path for f in parsed_files],
            )

            # Update scan with results
            analysis_duration = time.time() - start_time

            scan.status = ScanStatus.COMPLETED
            scan.completed_at = datetime.utcnow()
            scan.analysis_duration_seconds = analysis_duration
            scan.overall_score = scores.score
            scan.security_score = next((cs.score for cs in scores.category_scores if cs.category == Category.SECURITY), None)
            scan.scalability_score = next((cs.score for cs in scores.category_scores if cs.category == Category.SCALABILITY), None)
            scan.reliability_score = next((cs.score for cs in scores.category_scores if cs.category == Category.RELIABILITY), None)
            scan.cost_score = next((cs.score for cs in scores.category_scores if cs.category == Category.COST), None)
            scan.observability_score = next((cs.score for cs in scores.category_scores if cs.category == Category.OBSERVABILITY), None)
            scan.ai_status = "pending" if self.include_ai_explanations and rule_findings else "completed"
            scan.ai_error_message = None
            if scan.ai_status == "completed":
                scan.ai_completed_at = datetime.utcnow()

            await self.db.commit()

            self._update_progress(progress_callback, 100, "Scan complete")

            if scan.ai_status == "pending":
                enqueue_ai_analysis_for_scan(scan.id)

            logger.info(
                "Scan completed successfully",
                scan_id=scan.id,
                duration=analysis_duration,
                overall_score=scores.score,
                findings_count=len(rule_findings),
            )

        except Exception as e:
            logger.exception("Scan failed", scan_id=scan.id, error=str(e))
            scan.status = ScanStatus.FAILED
            scan.ai_status = "failed"
            scan.error_message = str(e)
            await self.db.commit()

            self._update_progress(progress_callback, 0, f"Failed: {str(e)}")

        finally:
            # Cleanup
            if repo_path:
                self.repo_scanner.cleanup(repo_path)

        return scan

    def _load_and_parse_files(self, repo_path: Path) -> list:
        """Load and parse all files in repository."""

        parsed_files = []

        # Scan for files
        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip hidden dirs (except .github), node_modules, etc.
            if ".git" in str(file_path) and ".github" not in str(file_path):
                continue
            if "node_modules" in str(file_path):
                continue
            if "__pycache__" in str(file_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                parsed = self.parser_registry.parse_file(file_path, content)
                if parsed:
                    parsed_files.append(parsed)
            except Exception as e:
                logger.warning(
                    "Failed to parse file",
                    file=str(file_path),
                    error=str(e),
                )

        return parsed_files

    def _extract_resources(self, parsed_files: list) -> list[dict[str, Any]]:
        """Extract resources from parsed files."""
        all_resources = []

        for parsed_file in parsed_files:
            resources = parsed_file.parsed_data  # ParsedFile has parsed_data dict
            if isinstance(resources, dict):
                # Extract based on file type
                if parsed_file.file_type == "terraform":
                    for resource in resources.get("resources", []):
                        resource["file_path"] = str(parsed_file.file_path)
                        resource["file_type"] = "terraform"
                        all_resources.append(resource)

                    # Also add backend config - wrap in properties for rule engine
                    for backend in resources.get("backends", []):
                        all_resources.append({
                            "file_type": "terraform",
                            "resource_type": "backend",
                            "properties": backend,
                            "file_path": str(parsed_file.file_path),
                        })

                elif parsed_file.file_type == "kubernetes":
                    for deployment in resources.get("deployments", []):
                        deployment["file_path"] = str(parsed_file.file_path)
                        deployment["file_type"] = "kubernetes"
                        deployment["kind"] = "Deployment"
                        all_resources.append(deployment)

                    for hpa in resources.get("hpa", []):
                        hpa["file_path"] = str(parsed_file.file_path)
                        hpa["file_type"] = "kubernetes"
                        hpa["kind"] = "HorizontalPodAutoscaler"
                        all_resources.append(hpa)

                    for service in resources.get("services", []):
                        service["file_path"] = str(parsed_file.file_path)
                        service["file_type"] = "kubernetes"
                        service["kind"] = "Service"
                        all_resources.append(service)

                elif parsed_file.file_type == "dockerfile":
                    # Dockerfile is a single resource
                    resources["file_path"] = str(parsed_file.file_path)
                    resources["file_type"] = "dockerfile"
                    all_resources.append(resources)

                elif parsed_file.file_type == "cicd":
                    # CICD needs raw_content for Terraform command detection
                    all_resources.append({
                        "file_path": str(parsed_file.file_path),
                        "file_type": "cicd",
                        "raw_content": parsed_file.raw_content,  # Include raw YAML text
                        **resources  # Include parsed data
                    })

        return all_resources

    def _run_rules(
        self,
        resources: list[dict[str, Any]],
        parsed_files: list,
    ) -> list[RuleFinding]:
        """Run rule engine against resources with file-type based filtering."""
        all_findings = []

        # Detect if repository has Terraform files
        has_terraform = any(
            pf.file_type == "terraform"
            for pf in parsed_files
        )

        # Group resources by file
        resources_by_file: dict[str, list[dict]] = {}
        for resource in resources:
            file_path = resource.get("file_path", "unknown")
            if file_path not in resources_by_file:
                resources_by_file[file_path] = []
            resources_by_file[file_path].append(resource)

        # Run rules for each file with file-type filtering
        for parsed_file in parsed_files:
            file_path = str(parsed_file.file_path)
            file_type = parsed_file.file_type
            file_resources = resources_by_file.get(file_path, [])

            # Skip files that shouldn't be scanned (documentation, etc.)
            if file_type not in ["terraform", "dockerfile", "kubernetes", "cicd", "docker_compose", "helm"]:
                continue

            # Skip tfvars files - they only contain variable values, no resources/backends
            if file_type == "terraform_vars":
                continue

            # Evaluate rules with file-type filtering
            # Pass has_terraform flag for CI/CD rules that need it
            file_findings = self.rule_registry.evaluate_all(
                file_resources,
                file_path,
                file_type=file_type,
                has_terraform=has_terraform
            )
            all_findings.extend(file_findings)

        # Run module-level checks for Terraform backends
        module_findings = self._check_terraform_module_backends(parsed_files)
        all_findings.extend(module_findings)

        # Run repository-level rules (once per repo, not per file)
        repo_findings = self._run_repository_level_rules(parsed_files, resources)
        all_findings.extend(repo_findings)

        return all_findings

    def _run_repository_level_rules(
        self,
        parsed_files: list,
        all_resources: list[dict[str, Any]],
    ) -> list[RuleFinding]:
        """
        Run repository-level rules that scan the entire repository.

        These rules run once per repository, not per file.
        Examples:
        - Missing monitoring stack (K8S-OBS-001)
        - Missing NetworkPolicy across all namespaces
        - Missing HPA coverage across all deployments

        Args:
            parsed_files: List of all parsed files
            all_resources: List of all extracted resources

        Returns:
            List of repository-level findings
        """
        from app.rule_engine.repository_rules import repo_level_rules

        return repo_level_rules.evaluate_repository_level_rules(
            parsed_files,
            all_resources,
        )

    def _check_terraform_module_backends(self, parsed_files: list) -> list[RuleFinding]:
        """
        Check Terraform backend configuration at module level.

        A Terraform root module is any directory containing .tf files
        that is NOT inside a modules/ directory.

        Reports one finding per module that lacks backend configuration.

        Args:
            parsed_files: List of parsed file objects

        Returns:
            List of findings (one per module without backend)
        """
        from app.rule_engine.base import Category, RuleFinding, Severity

        findings = []

        # Collect Terraform files by module directory
        modules: dict[str, dict] = {}

        for parsed_file in parsed_files:
            if parsed_file.file_type not in ["terraform", "terraform_vars"]:
                continue

            file_path = Path(parsed_file.file_path)

            # Skip files inside modules/ directories
            if "modules" in file_path.parts:
                continue

            # Get module directory
            module_dir = str(file_path.parent) if str(file_path.parent) != "." else "."

            # Initialize module if not exists
            if module_dir not in modules:
                modules[module_dir] = {
                    "path": module_dir,
                    "tf_files": [],
                    "has_backend": False,
                    "backend_type": None,
                }

            modules[module_dir]["tf_files"].append(str(file_path))

            # Check for backend in this file
            if parsed_file.file_type == "terraform":
                parsed_data = parsed_file.parsed_data
                if isinstance(parsed_data, dict):
                    backends = parsed_data.get("backends", [])
                    if backends:
                        modules[module_dir]["has_backend"] = True
                        if isinstance(backends[0], dict):
                            modules[module_dir]["backend_type"] = backends[0].get("type")

        # Generate findings for modules without backend
        for module_path, module_info in modules.items():
            if not module_info["has_backend"]:
                # Use module directory path instead of first .tf file to avoid confusion
                # The issue is a module-level problem, not a file-specific problem
                finding_file_path = module_path.rstrip('/') + '/'  # Use module directory as the "file"

                findings.append(RuleFinding(
                    rule_id="TF-STATE-002",
                    rule_name="Remote Backend Required",
                    severity=Severity.HIGH,
                    category=Category.RELIABILITY,
                    description=f"Terraform root module '{module_path}' does not have a remote backend configured",
                    recommendation="Configure remote backend (S3, GCS, Azure Blob, Consul, Terraform Cloud) with state locking",
                    file_path=finding_file_path,
                    metadata={
                        "module_path": module_path,
                        "tf_files_count": len(module_info["tf_files"]),
                        "tf_files": module_info["tf_files"][:3],
                    },
                    risk="Terraform state stored locally cannot be shared across team members or CI/CD pipelines, leading to state drift, failed applies, and potential infrastructure corruption.",
                    impact="Multiple engineers running terraform apply simultaneously can corrupt state, causing infrastructure drift and deployment failures.",
                    fix_example='''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
                ))

        if findings:
            logger.info(
                "Module-level backend check complete",
                modules_checked=len(modules),
                modules_without_backend=len(findings),
            )

        return findings

    async def _save_findings(
        self,
        scan_id: int,
        findings: list[RuleFinding],
    ) -> None:
        """Save findings to database."""
        for finding in findings:
            db_finding = Finding(
                scan_id=scan_id,
                rule_id=finding.rule_id,
                rule_name=finding.rule_name,
                severity=finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
                category=finding.category.value if hasattr(finding.category, 'value') else str(finding.category),
                description=finding.description,
                recommendation=finding.recommendation,
                # AI Fix Generator fields
                summary=finding.summary,
                risk=finding.risk,
                impact=finding.impact,
                fix_code=finding.fix_code,
                fix_example=finding.fix_example,
                full_example=finding.full_example,
                best_practices=json.dumps(finding.best_practices) if finding.best_practices else None,
                confidence=finding.confidence,
                documentation_url=finding.documentation_url,
                file_path=finding.file_path,
                line_number=finding.line_number,
                resource_name=finding.resource_name,
                ai_explanation=finding.ai_explanation,
                impact_analysis=finding.impact_analysis,
                ai_generated=getattr(finding, 'ai_generated', False),  # Track AI usage
                confidence_score=finding.confidence or 1.0,
            )
            self.db.add(db_finding)

        await self.db.flush()

    async def _create_report(
        self,
        scan: Scan,
        rule_findings: list[RuleFinding],
        scores: Any,
        files_analyzed: list[str],
    ) -> Report | None:
        """Create analysis report."""
        # Generate AI summary if enabled
        executive_summary = None
        risk_analysis = None
        prioritized_recommendations = None

        if self.explanation_engine:
            scores_dict = {
                cs.category.value: cs.score for cs in scores.category_scores
            }

            summary_data = await self.explanation_engine.generate_report_summary(
                rule_findings, scores_dict
            )
            executive_summary = summary_data.get("executive_summary")
            risk_analysis = summary_data.get("risk_analysis")
            prioritized_recommendations = summary_data.get("prioritized_recommendations")

        try:
            async with self.db.begin_nested():
                report = await self.report_service.upsert_report_record_async(
                    db=self.db,
                    scan=scan,
                    findings=rule_findings,
                    scores=scores,
                    files_analyzed=files_analyzed,
                    executive_summary=executive_summary,
                    risk_analysis=risk_analysis,
                    prioritized_recommendations=prioritized_recommendations,
                )
                self.report_service.generate_and_store_artifacts(
                    scan=scan,
                    report=report,
                    findings=rule_findings,
                )
                await self.db.flush()
        except Exception as exc:
            logger.exception(
                "Report artifact generation failed",
                scan_id=scan.id,
                error=str(exc),
            )
            return None

        return report

    def _update_progress(
        self,
        callback: Callable[[int, str], None] | None,
        progress: int,
        message: str,
    ) -> None:
        """Update progress if callback provided."""
        if callback:
            callback(progress, message)
