"""
Celery Tasks for Repository Scanning with Dynamic Scanner Execution
"""

from celery import states
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime
from pathlib import Path
import time
import yaml

from app.workers.celery_config import celery_app
from app.db.session import get_sync_session_factory
from app.models.scan import Scan, ScanStatus
from app.models.finding import Finding as FindingModel, Severity, Category
from app.models.report import Report
from app.utils.repository_scanner import RepositoryScanner
from app.core.logging import get_logger
from app.config import settings
from app.rule_engine.base import RuleRegistry, RuleFinding
from app.scoring.engine import ScoringEngine
from app.parsers.base import ParserRegistry, ParsedFile
from app.parsers.terraform import TerraformParser
from app.parsers.kubernetes import KubernetesParser
from app.parsers.dockerfile import DockerfileParser
from app.parsers.cicd import CICDParser

logger = get_logger(__name__)


class DetectedTechnologyStack:
    """Detected technology stack for dynamic scanner execution."""

    def __init__(self):
        self.has_docker = False
        self.docker_files: List[str] = []
        self.has_terraform = False
        self.terraform_files: List[str] = []
        self.has_kubernetes = False
        self.kubernetes_files: List[str] = []
        self.has_github_actions = False
        self.github_actions_files: List[str] = []
        self.has_docker_compose = False
        self.docker_compose_files: List[str] = []

    def get_detected_technologies(self) -> List[str]:
        """Get list of detected technology names."""
        technologies = []
        if self.has_docker:
            technologies.append("docker")
        if self.has_terraform:
            technologies.append("terraform")
        if self.has_kubernetes:
            technologies.append("kubernetes")
        if self.has_github_actions:
            technologies.append("github_actions")
        if self.has_docker_compose:
            technologies.append("docker_compose")
        return technologies


def detect_technology_stack_from_files(files: List[str]) -> DetectedTechnologyStack:
    """Detect technology stack from file list."""
    stack = DetectedTechnologyStack()

    for file_path in files:
        file_name = file_path.split("/")[-1].lower()
        file_lower = file_path.lower()

        # Docker detection
        if file_name in ["dockerfile", "containerfile"] or "dockerfile" in file_name:
            stack.has_docker = True
            stack.docker_files.append(file_path)

        # Docker Compose
        if file_name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            stack.has_docker_compose = True
            stack.docker_compose_files.append(file_path)

        # Terraform
        if file_path.endswith((".tf", ".tf.json", ".tfvars")):
            stack.has_terraform = True
            stack.terraform_files.append(file_path)

        # Kubernetes - check path and content
        if file_path.endswith((".yaml", ".yml")):
            if _is_kubernetes_file(file_path):
                stack.has_kubernetes = True
                stack.kubernetes_files.append(file_path)

        # GitHub Actions
        if ".github/workflows/" in file_path and file_path.endswith((".yml", ".yaml")):
            stack.has_github_actions = True
            stack.github_actions_files.append(file_path)

    return stack


def _is_kubernetes_file(file_path: str) -> bool:
    """Check if file is likely a Kubernetes manifest based on path."""
    file_lower = file_path.lower()
    k8s_indicators = ["kubernetes", "k8s", "manifests", "deployments", "helm", "charts"]
    if any(indicator in file_lower for indicator in k8s_indicators):
        return True
    k8s_file_patterns = ["deployment", "service", "pod", "configmap", "secret", "ingress"]
    file_name = file_path.split("/")[-1].lower()
    if any(pattern in file_name for pattern in k8s_file_patterns):
        return True
    return False


class SyncScanService:
    """Synchronous scan service for Celery tasks with dynamic scanner execution."""

    def __init__(self, db, include_ai_explanations: bool = True):
        self.db = db
        self.include_ai_explanations = include_ai_explanations
        self.rule_registry = RuleRegistry()
        self.scoring_engine = ScoringEngine()
        self.repo_scanner = RepositoryScanner()
        self.parser_registry = self._setup_parsers()
        self.detected_stack = DetectedTechnologyStack()

    def _setup_parsers(self) -> ParserRegistry:
        """Initialize and register all parsers."""
        registry = ParserRegistry()
        registry.register(TerraformParser())
        registry.register(KubernetesParser())
        registry.register(DockerfileParser())
        registry.register(CICDParser())
        return registry

    def execute_scan(
        self,
        scan: Scan,
        progress_callback: Optional[callable] = None,
    ) -> Scan:
        """Execute a complete scan workflow synchronously with dynamic scanner execution."""
        start_time = time.time()
        repo_path = None

        try:
            # Update status to processing
            scan.status = ScanStatus.PROCESSING
            scan.started_at = datetime.utcnow()
            self.db.commit()

            self._update_progress(progress_callback, 10, "Cloning repository...")

            # Clone repository
            repo_path, repo_info = self.repo_scanner.clone_repository(
                scan.repository_url,
                scan.branch,
                scan.commit_hash,
                settings.GITHUB_TOKEN,
            )

            self._update_progress(progress_callback, 20, "Detecting technology stack...")

            # Detect technology stack from file list
            all_files = self._collect_all_files(Path(repo_path))
            self.detected_stack = detect_technology_stack_from_files(all_files)

            logger.info(
                "Technology stack detected",
                stack=",".join(self.detected_stack.get_detected_technologies()) or "none",
            )

            self._update_progress(progress_callback, 30, "Loading files...")

            # Load and parse files
            parsed_files = self._load_and_parse_files(Path(repo_path))

            if not parsed_files:
                raise ValueError("No analyzable files found in repository")

            self._update_progress(progress_callback, 50, f"Running rule engine ({len(parsed_files)} files)...")

            # Extract resources and run rules
            resources = self._extract_resources(parsed_files)
            rule_findings = self._run_rules(resources, parsed_files)

            self._update_progress(progress_callback, 80, "Calculating scores...")

            # Calculate scores
            scores = self.scoring_engine.calculate_scores(rule_findings)

            self._update_progress(progress_callback, 90, "Saving results...")

            # Save findings to database
            self._save_findings(scan.id, rule_findings)

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

            self.db.commit()

            self._update_progress(progress_callback, 100, "Scan complete")

            logger.info(
                "Scan completed successfully",
                scan_id=scan.id,
                duration=analysis_duration,
                overall_score=scores.score,
                findings_count=len(rule_findings),
                detected_stack=",".join(self.detected_stack.get_detected_technologies()) or "none",
            )

        except Exception as e:
            logger.exception("Scan failed", scan_id=scan.id, error=str(e))
            scan.status = ScanStatus.FAILED
            scan.error_message = str(e)
            scan.completed_at = datetime.utcnow()
            self.db.commit()

            self._update_progress(progress_callback, 0, f"Failed: {str(e)}")
            raise

        finally:
            # Cleanup
            if repo_path:
                self.repo_scanner.cleanup(repo_path)

        return scan

    def _collect_all_files(self, repo_path: Path) -> List[str]:
        """Collect all file paths in repository."""
        files = []
        for file_path in repo_path.rglob("*"):
            if file_path.is_file():
                if ".git" in str(file_path) and ".github" not in str(file_path):
                    continue
                if "__pycache__" in str(file_path):
                    continue
                if "node_modules" in str(file_path):
                    continue
                files.append(str(file_path.relative_to(repo_path)))
        return files

    def _load_and_parse_files(self, repo_path: Path) -> List[ParsedFile]:
        """Load and parse all files in repository."""
        parsed_files = []

        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue

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
                logger.warning("Failed to parse file", file=str(file_path), error=str(e))

        return parsed_files

    def _extract_resources(self, parsed_files: List[ParsedFile]):
        """Extract resources from parsed files."""
        all_resources = []

        for parsed_file in parsed_files:
            resources = parsed_file.parsed_data
            if isinstance(resources, dict):
                if parsed_file.file_type == "terraform":
                    for resource in resources.get("resources", []):
                        resource["file_path"] = str(parsed_file.file_path)
                        resource["file_type"] = "terraform"
                        all_resources.append(resource)

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
                    resources["file_path"] = str(parsed_file.file_path)
                    resources["file_type"] = "dockerfile"
                    all_resources.append(resources)

                elif parsed_file.file_type == "cicd":
                    resources["file_path"] = str(parsed_file.file_path)
                    resources["file_type"] = "cicd"
                    all_resources.append(resources)

        return all_resources

    def _run_rules(self, resources, parsed_files: List[ParsedFile]):
        """Run rule engine against resources."""
        all_findings = []

        resources_by_file = {}
        for resource in resources:
            file_path = resource.get("file_path", "unknown")
            if file_path not in resources_by_file:
                resources_by_file[file_path] = []
            resources_by_file[file_path].append(resource)

        for parsed_file in parsed_files:
            file_path = str(parsed_file.file_path)
            file_resources = resources_by_file.get(file_path, [])
            file_findings = self.rule_registry.evaluate_all(file_resources, file_path)
            all_findings.extend(file_findings)

        return all_findings

    def _save_findings(self, scan_id, findings: List[RuleFinding]):
        """Save findings to database."""
        for finding in findings:
            db_finding = FindingModel(
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

        self.db.flush()

    def _update_progress(self, callback, progress: int, message: str):
        """Update progress if callback provided."""
        if callback:
            callback(progress, message)


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def scan_repository_task(
    self,
    scan_id: str,
    repository_url: str,
    branch: str = "main",
    commit_hash: Optional[str] = None,
    include_ai_explanations: bool = True,
) -> Dict[str, Any]:
    """Celery task to scan a repository."""
    scanner = RepositoryScanner()
    repo_path = None
    SessionLocal = get_sync_session_factory()

    try:
        db = SessionLocal()
        try:
            from uuid import UUID
            scan_uuid = scan_id if isinstance(scan_id, UUID) else UUID(scan_id)
            scan = db.get(Scan, scan_uuid)
            if not scan:
                logger.error("Scan not found", scan_id=scan_id)
                return {"status": "failed", "error": "Scan not found"}

            scan.status = ScanStatus.PROCESSING
            scan.started_at = datetime.utcnow()
            scan.celery_task_id = self.request.id
            db.commit()
        finally:
            db.close()

        logger.info(
            "Starting repository scan",
            scan_id=scan_id,
            repo_url=repository_url,
            task_id=self.request.id,
        )

        self.update_state(state="PROGRESS", meta={"progress": 10, "status": "Cloning repository..."})
        repo_path, scan_result = scanner.clone_repository(
            repository_url,
            branch,
            commit_hash,
            settings.GITHUB_TOKEN,
        )

        db = SessionLocal()
        try:
            scan_service = SyncScanService(
                db=db,
                include_ai_explanations=include_ai_explanations,
            )

            from uuid import UUID
            scan_uuid = scan_id if isinstance(scan_id, UUID) else UUID(scan_id)
            scan = db.get(Scan, scan_uuid)

            def progress_callback(progress: int, message: str):
                self.update_state(state="PROGRESS", meta={"progress": progress, "status": message})

            updated_scan = scan_service.execute_scan(scan, progress_callback)
            
            # Get findings count before session closes
            findings_count = len(updated_scan.findings) if hasattr(updated_scan, 'findings') else 0
            overall_score = updated_scan.overall_score
        finally:
            db.close()

        logger.info(
            "Repository scan completed",
            scan_id=scan_id,
            score=overall_score,
        )

        return {
            "status": "completed",
            "scan_id": str(scan_id),
            "overall_score": overall_score,
            "findings_count": findings_count,
        }

    except Exception as exc:
        logger.exception("Scan failed", scan_id=scan_id, error=str(exc))

        try:
            db = SessionLocal()
            try:
                from uuid import UUID
                scan_uuid = scan_id if isinstance(scan_id, UUID) else UUID(scan_id)
                scan = db.get(Scan, scan_uuid)
                if scan:
                    scan.status = ScanStatus.FAILED
                    scan.error_message = str(exc)
                    scan.completed_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
        except Exception as db_exc:
            logger.error("Failed to update scan status on error", scan_id=scan_id, error=str(db_exc))

        raise self.retry(exc=exc)

    finally:
        if repo_path:
            scanner.cleanup(repo_path)


@celery_app.task(bind=True)
def cancel_scan_task(self, scan_id: int) -> Dict[str, Any]:
    """Cancel a running scan."""
    from app.db.session import get_session_factory
    session_factory = get_session_factory()

    with session_factory() as db:
        scan = db.get(Scan, scan_id)

        if not scan:
            return {"status": "not_found", "error": "Scan not found"}

        if scan.status not in [ScanStatus.PENDING, ScanStatus.PROCESSING, ScanStatus.QUEUED]:
            return {"status": "already_completed", "message": f"Scan is already {scan.status.value}"}

        scan.status = ScanStatus.CANCELLED
        scan.error_message = "Scan cancelled by user"
        scan.completed_at = datetime.utcnow()
        db.commit()

        if scan.celery_task_id:
            celery_app.control.revoke(scan.celery_task_id, terminate=True)

        logger.info("Scan cancelled", scan_id=scan_id)

        return {"status": "cancelled", "scan_id": str(scan_id)}


@celery_app.task(bind=True, max_retries=3)
def cleanup_old_scans_task(self, days_old: int = 30) -> Dict[str, Any]:
    """Clean up old scans and their data."""
    from sqlalchemy import delete, select, func
    from datetime import timedelta

    from app.db.session import get_session_factory
    session_factory = get_session_factory()
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)

    try:
        with session_factory() as db:
            count_query = select(func.count(Scan.id)).where(
                Scan.created_at < cutoff_date,
                Scan.status.in_([ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED]),
            )
            count = db.scalar(count_query) or 0

            if count == 0:
                return {"status": "completed", "deleted_count": 0}

            logger.info("Cleaning up old scans", count=count, cutoff_date=cutoff_date)

            delete_stmt = delete(FindingModel).where(
                FindingModel.scan_id.in_(
                    select(Scan.id).where(
                        Scan.created_at < cutoff_date,
                        Scan.status.in_([ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED]),
                    )
                )
            )
            db.execute(delete_stmt)

            delete_stmt = delete(Report).where(
                Report.scan_id.in_(
                    select(Scan.id).where(
                        Scan.created_at < cutoff_date,
                        Scan.status.in_([ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED]),
                    )
                )
            )
            db.execute(delete_stmt)

            delete_stmt = delete(Scan).where(
                Scan.created_at < cutoff_date,
                Scan.status.in_([ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED]),
            )
            db.execute(delete_stmt)

            db.commit()

            logger.info("Cleanup completed", deleted_count=count)

            return {"status": "completed", "deleted_count": count}

    except Exception as exc:
        logger.exception("Cleanup failed", error=str(exc))
        raise self.retry(exc=exc)
