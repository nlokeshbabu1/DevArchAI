"""Scan service for orchestrating repository analysis with stack detection."""

import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.scan import Scan, ScanStatus
from app.models.finding import Finding, Severity, Category
from app.models.report import Report
from app.rule_engine.base import RuleFinding, RuleRegistry
from app.ai_engine.explanation_engine import ExplanationEngine
from app.scoring.engine import ScoringEngine
from app.utils.repository_scanner import RepositoryScanner
from app.parsers.base import ParserRegistry
from app.parsers.terraform import TerraformParser
from app.parsers.kubernetes import KubernetesParser
from app.parsers.dockerfile import DockerfileParser
from app.parsers.cicd import CICDParser
from app.services.technology_detector import detect_technology_stack, TechnologyStack
from app.core.logging import get_logger
from app.config import settings

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
        self.detected_stack: Optional[TechnologyStack] = None
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
        commit_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
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
            logger.info("Technology stack detected", stack=detected_techs)

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

    def _finding_to_dict(self, finding: RuleFinding) -> Dict[str, Any]:
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
        }

    async def execute_scan(
        self,
        scan: Scan,
        progress_callback: Optional[Callable[[int, str], None]] = None,
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

            self._update_progress(progress_callback, 65, "Generating AI explanations...")

            # Add AI explanations
            if self.include_ai_explanations and self.explanation_engine:
                rule_findings = await self.explanation_engine.explain_findings_batch(
                    rule_findings,
                    max_findings=20,
                )

            self._update_progress(progress_callback, 80, "Calculating scores...")

            # Calculate scores
            scores = self.scoring_engine.calculate_scores(rule_findings)

            self._update_progress(progress_callback, 90, "Saving results...")

            # Save findings to database
            await self._save_findings(scan.id, rule_findings)

            # Create report
            report = await self._create_report(
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

            await self.db.commit()

            self._update_progress(progress_callback, 100, "Scan complete")

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
            scan.error_message = str(e)
            await self.db.commit()

            self._update_progress(progress_callback, 0, f"Failed: {str(e)}")

        finally:
            # Cleanup
            if repo_path:
                self.repo_scanner.cleanup(repo_path)

        return scan
    
    def _load_and_parse_files(self, repo_path: Path) -> List:
        """Load and parse all files in repository."""
        from app.parsers.base import ParsedFile
        
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
    
    def _extract_resources(self, parsed_files: List) -> List[Dict[str, Any]]:
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
                    resources["file_path"] = str(parsed_file.file_path)
                    resources["file_type"] = "cicd"
                    all_resources.append(resources)

        return all_resources

    def _run_rules(
        self,
        resources: List[Dict[str, Any]],
        parsed_files: List,
    ) -> List[RuleFinding]:
        """Run rule engine against resources."""
        all_findings = []

        # Group resources by file
        resources_by_file: Dict[str, List[Dict]] = {}
        for resource in resources:
            file_path = resource.get("file_path", "unknown")
            if file_path not in resources_by_file:
                resources_by_file[file_path] = []
            resources_by_file[file_path].append(resource)

        # Run rules for each file
        for parsed_file in parsed_files:
            file_path = str(parsed_file.file_path)
            file_type = parsed_file.file_type
            file_resources = resources_by_file.get(file_path, [])

            # Evaluate all rules
            file_findings = self.rule_registry.evaluate_all(file_resources, file_path)
            all_findings.extend(file_findings)

        return all_findings

    async def _save_findings(
        self,
        scan_id: int,
        findings: List[RuleFinding],
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
                file_path=finding.file_path,
                line_number=finding.line_number,
                resource_name=finding.resource_name,
                ai_explanation=finding.ai_explanation,
                impact_analysis=finding.impact_analysis,
                confidence_score=finding.confidence,
            )
            self.db.add(db_finding)

        await self.db.flush()

    async def _create_report(
        self,
        scan: Scan,
        rule_findings: List[RuleFinding],
        scores: Any,
        files_analyzed: List[str],
    ) -> Report:
        """Create analysis report."""
        # Count findings by severity
        severity_counts = {
            "critical": sum(1 for f in rule_findings if f.severity == Severity.CRITICAL or (hasattr(f.severity, 'value') and f.severity.value == "critical")),
            "high": sum(1 for f in rule_findings if f.severity == Severity.HIGH or (hasattr(f.severity, 'value') and f.severity.value == "high")),
            "medium": sum(1 for f in rule_findings if f.severity == Severity.MEDIUM or (hasattr(f.severity, 'value') and f.severity.value == "medium")),
            "low": sum(1 for f in rule_findings if f.severity == Severity.LOW or (hasattr(f.severity, 'value') and f.severity.value == "low")),
            "info": sum(1 for f in rule_findings if f.severity == Severity.INFO or (hasattr(f.severity, 'value') and f.severity.value == "info")),
        }

        # Generate AI summary if enabled
        executive_summary = None
        risk_analysis = None
        prioritized_recommendations = None

        if self.explanation_engine:
            scores_dict = {
                "security": scores.score,
                "scalability": scores.scalability_score,
                "reliability": scores.reliability_score,
                "cost": scores.cost_score,
                "observability": scores.observability_score,
            }

            summary_data = await self.explanation_engine.generate_report_summary(
                rule_findings, scores_dict
            )
            executive_summary = summary_data.get("executive_summary")
            risk_analysis = summary_data.get("risk_analysis")
            prioritized_recommendations = summary_data.get("prioritized_recommendations")

        # Create report
        report = Report(
            scan_id=scan.id,
            repository_name=scan.repository_url.split("/")[-1],
            repository_url=scan.repository_url,
            commit_hash=scan.commit_hash,
            overall_score=scores.score,
            category_scores={
                "security": next((cs.score for cs in scores.category_scores if cs.category == Category.SECURITY), 0),
                "scalability": next((cs.score for cs in scores.category_scores if cs.category == Category.SCALABILITY), 0),
                "reliability": next((cs.score for cs in scores.category_scores if cs.category == Category.RELIABILITY), 0),
                "cost": next((cs.score for cs in scores.category_scores if cs.category == Category.COST), 0),
                "observability": next((cs.score for cs in scores.category_scores if cs.category == Category.OBSERVABILITY), 0),
            },
            executive_summary=executive_summary,
            risk_analysis=risk_analysis,
            prioritized_recommendations=prioritized_recommendations,
            total_findings=len(rule_findings),
            critical_count=severity_counts["critical"],
            high_count=severity_counts["high"],
            medium_count=severity_counts["medium"],
            low_count=severity_counts["low"],
            info_count=severity_counts["info"],
            files_analyzed=files_analyzed,
        )

        self.db.add(report)
        await self.db.flush()

        return report

    def _update_progress(
        self,
        callback: Optional[Callable[[int, str], None]],
        progress: int,
        message: str,
    ) -> None:
        """Update progress if callback provided."""
        if callback:
            callback(progress, message)
