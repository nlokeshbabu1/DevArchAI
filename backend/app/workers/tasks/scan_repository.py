"""
Celery Tasks for Repository Scanning with Dynamic Scanner Execution
"""

import asyncio
import json
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.logging import get_logger
from app.db.session import get_sync_session_factory
from app.models.finding import Category, Finding as FindingModel
from app.models.report import Report
from app.models.scan import Scan, ScanStatus
from app.parsers.base import ParsedFile, ParserRegistry
from app.parsers.cicd import CICDParser
from app.parsers.dockerfile import DockerfileParser
from app.parsers.kubernetes import KubernetesParser
from app.parsers.terraform import TerraformParser
from app.rule_engine.base import RuleFinding, RuleRegistry
from app.scanners.azure_scanner import AzureScanner
from app.scanners.deduplicator import deduplicate_across_scanners
from app.scanners.helm_scanner import HelmScanner
from app.scanners.registry import ScannerRegistry
from app.scoring.engine import ScoringEngine
from app.services.ai_suggestion_service import schedule_ai_suggestions_generation
from app.services.report_service import ReportService
from app.utils.repository_scanner import RepositoryScanner
from app.workers.celery_config import celery_app

logger = get_logger(__name__)


def _run_ai_enrichment_in_process(findings_data, file_contents_data):
    """Run AI enrichment in a separate process with its own event loop.

    This function MUST be at module level for multiprocessing to work.
    """
    import asyncio

    from app.rule_engine.base import Category, RuleFinding, Severity
    from app.services.findings_enricher import enrich_findings_with_ai

    # Recreate findings from serialized data
    findings = []
    for f_data in findings_data:
        finding = RuleFinding(
            rule_id=f_data['rule_id'],
            rule_name=f_data['rule_name'],
            severity=Severity(f_data['severity']),
            category=Category(f_data['category']),
            description=f_data['description'],
            recommendation=f_data['recommendation'],
            file_path=f_data.get('file_path'),
            line_number=f_data.get('line_number'),
            resource_name=f_data.get('resource_name'),
        )
        findings.append(finding)

    # Create NEW event loop for this process (avoids uvloop conflict)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        enriched = loop.run_until_complete(enrich_findings_with_ai(findings, file_contents_data))
        return enriched
    finally:
        loop.close()


def _safe_await(coro, loop=None):
    """
    Safely await a coroutine from sync code.
    ALWAYS runs synchronously to ensure progress updates complete.

    Args:
        coro: The coroutine to await.
        loop: Optional persistent event loop. If provided, uses this loop
              instead of creating/destroying loops repeatedly.
    """
    import structlog as _structlog
    _logger = _structlog.get_logger(__name__)

    # If a persistent loop is provided, use it directly
    if loop is not None:
        try:
            if loop.is_closed():
                _logger.error("Persistent event loop is closed — cannot execute coroutine")
                return None
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(loop.run_until_complete, coro)
                    return future.result(timeout=30.0)
            else:
                return loop.run_until_complete(coro)
        except Exception as e:
            _logger.error(f"Progress update failed on persistent loop: {e}")
            return None

    # Fallback: no loop provided — use dynamic loop resolution
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=5.0)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
    except Exception as e:
        _logger.warning(f"Progress update failed (fallback): {e}")
        return None


class DetectedTechnologyStack:
    """Detected technology stack for dynamic scanner execution."""

    def __init__(self):
        self.has_docker = False
        self.docker_files: list[str] = []
        self.has_terraform = False
        self.terraform_files: list[str] = []
        self.has_kubernetes = False
        self.kubernetes_files: list[str] = []
        self.has_github_actions = False
        self.github_actions_files: list[str] = []
        self.has_docker_compose = False
        self.docker_compose_files: list[str] = []
        self.has_jenkins = False
        self.jenkins_files: list[str] = []
        self.has_gitlab_ci = False
        self.gitlab_ci_files: list[str] = []
        self.has_circleci = False
        self.circleci_files: list[str] = []
        self.has_azure_devops = False
        self.azure_devops_files: list[str] = []
        self.has_ansible = False
        self.ansible_files: list[str] = []
        self.has_helm = False
        self.helm_files: list[str] = []
        self.has_prometheus = False
        self.prometheus_files: list[str] = []
        self.has_grafana = False
        self.grafana_files: list[str] = []

    def get_detected_technologies(self) -> list[str]:
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
        if self.has_jenkins:
            technologies.append("jenkins")
        if self.has_gitlab_ci:
            technologies.append("gitlab_ci")
        if self.has_circleci:
            technologies.append("circleci")
        if self.has_azure_devops:
            technologies.append("azure_devops")
        if self.has_ansible:
            technologies.append("ansible")
        if self.has_helm:
            technologies.append("helm")
        if self.has_prometheus:
            technologies.append("prometheus")
        if self.has_grafana:
            technologies.append("grafana")
        return technologies

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'has_docker': self.has_docker,
            'docker_files': self.docker_files,
            'has_terraform': self.has_terraform,
            'terraform_files': self.terraform_files,
            'has_kubernetes': self.has_kubernetes,
            'kubernetes_files': self.kubernetes_files,
            'has_github_actions': self.has_github_actions,
            'github_actions_files': self.github_actions_files,
            'has_docker_compose': self.has_docker_compose,
            'docker_compose_files': self.docker_compose_files,
            'has_jenkins': self.has_jenkins,
            'jenkins_files': self.jenkins_files,
            'has_gitlab_ci': self.has_gitlab_ci,
            'gitlab_ci_files': self.gitlab_ci_files,
            'has_circleci': self.has_circleci,
            'circleci_files': self.circleci_files,
            'has_azure_devops': self.has_azure_devops,
            'azure_devops_files': self.azure_devops_files,
            'has_ansible': self.has_ansible,
            'ansible_files': self.ansible_files,
            'has_helm': self.has_helm,
            'helm_files': self.helm_files,
            'has_prometheus': self.has_prometheus,
            'prometheus_files': self.prometheus_files,
            'has_grafana': self.has_grafana,
            'grafana_files': self.grafana_files,
        }


def detect_technology_stack_from_files(files: list[str]) -> DetectedTechnologyStack:
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

        # Jenkins
        if file_name.lower() == "jenkinsfile" or file_name.lower().startswith("jenkinsfile.") or file_name.lower().startswith("jenkinsfile-"):
            stack.has_jenkins = True
            stack.jenkins_files.append(file_path)

        # GitLab CI
        if file_name == ".gitlab-ci.yml" or file_name == ".gitlab-ci.yaml":
            stack.has_gitlab_ci = True
            stack.gitlab_ci_files.append(file_path)

        # CircleCI
        if ".circleci/" in file_path and file_path.endswith((".yml", ".yaml")):
            stack.has_circleci = True
            stack.circleci_files.append(file_path)

        # Azure DevOps
        if file_name in ["azure-pipelines.yml", "azure-pipelines.yaml"]:
            stack.has_azure_devops = True
            stack.azure_devops_files.append(file_path)

        # Ansible
        if file_name in ["ansible.cfg", ".ansible.cfg"] or file_path.endswith((".ansible.yml", ".ansible.yaml")):
            stack.has_ansible = True
            stack.ansible_files.append(file_path)
        if "/roles/" in file_path or "/playbooks/" in file_path:
            if file_path.endswith((".yml", ".yaml")):
                stack.has_ansible = True
                stack.ansible_files.append(file_path)

        # Helm
        if file_name == "chart.yaml" or file_name == "helmfile.yaml" or file_name == "helmfile.yml":
            stack.has_helm = True
            stack.helm_files.append(file_path)

        # Prometheus
        if file_name in ["prometheus.yml", "prometheus.yaml", "prometheus.rules.yml", "prometheus.rules.yaml"]:
            stack.has_prometheus = True
            stack.prometheus_files.append(file_path)

        # Grafana
        if "grafana" in file_lower and file_path.endswith((".yml", ".yaml", ".json")):
            stack.has_grafana = True
            stack.grafana_files.append(file_path)

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

    def __init__(
        self,
        db,
        include_ai_explanations: bool = True,
        progress_store = None,
        scan_id: str = None,
        event_loop = None,
    ):
        self.db = db
        self.include_ai_explanations = include_ai_explanations
        self.progress_store = progress_store
        self.scan_id = scan_id
        self.event_loop = event_loop
        self.rule_registry = RuleRegistry()
        self.scoring_engine = ScoringEngine()
        self.repo_scanner = RepositoryScanner()
        self.parser_registry = self._setup_parsers()
        self.detected_stack = DetectedTechnologyStack()
        self.report_service = ReportService()

    async def _update_progress_async(self, progress: int, message: str, step_name: str | None = None, stage: str | None = None, files_scanned: int = 0, total_files: int = 0):
        """Update progress in the store (async)."""
        if self.progress_store and self.scan_id:
            await self.progress_store.update_status(self.scan_id, "running", progress, step_name or message)
            if message:
                await self.progress_store.add_log(self.scan_id, message)
                try:
                    from app.websockets.scan_progress import scan_progress_manager
                    await scan_progress_manager.broadcast_log(self.scan_id, message)
                except Exception:
                    pass
            if stage:
                await self.progress_store.update_stage(self.scan_id, stage, files_scanned, total_files)
            if step_name:
                from app.schemas.scan_progress import StepStatus
                # Mark previous running step as completed
                for step in (await self.progress_store.get_progress(self.scan_id)).steps:
                    if step.status == StepStatus.RUNNING:
                        await self.progress_store.update_step(self.scan_id, step.name, StepStatus.COMPLETED, 100)
                        break
                # Mark current step as running
                await self.progress_store.update_step(self.scan_id, step_name, StepStatus.RUNNING, progress)

            # Broadcast progress update to all connected WebSocket clients
            try:
                from app.websockets.scan_progress import scan_progress_manager
                progress_obj = await self.progress_store.get_progress(self.scan_id)
                if progress_obj:
                    sent = await scan_progress_manager.broadcast_progress(
                        scan_id=self.scan_id,
                        progress=progress,
                        status="running",
                        current_step=step_name or message,
                        steps=[s.dict() for s in progress_obj.steps],
                        logs=progress_obj.logs,
                        detected_stack=progress_obj.detected_stack,
                        files_list=getattr(progress_obj, 'files_list', None),
                    )
                    logger.debug(f"Broadcasted progress update to {sent} clients: {progress}% - {step_name or message}")
            except Exception as e:
                logger.warning(f"Failed to broadcast progress update: {e}")

    def _exec_async(self, coro):
        """Execute a coroutine synchronously using the persistent event loop."""
        return _safe_await(coro, loop=self.event_loop)

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
        progress_callback: Callable | None = None,
    ) -> Scan:
        """Execute a complete scan workflow synchronously with dynamic scanner execution."""

        start_time = time.time()
        repo_path = None

        logger.info(
            f"[LIFECYCLE] scan={self.scan_id} event=EXECUTE_SCAN_START "
            f"repo={scan.repository_url} branch={scan.branch} "
            f"timestamp={datetime.utcnow().isoformat()}"
        )

        # PHASE 6: Record scan start (NEW - Observability)
        try:
            from app.services.metrics import record_scan, record_scan_start
            record_scan_start()
        except Exception:
            pass  # Don't break scan if metrics fail

        try:
            # Update status to processing
            scan.status = ScanStatus.PROCESSING
            scan.started_at = datetime.utcnow()
            self.db.commit()

            # Initialize progress tracking
            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(10, "Cloning repository...", "Connecting to GitHub", stage="cloning"))

            self._update_progress(progress_callback, 10, "Cloning repository...")

            # Clone repository
            repo_path, repo_info = self.repo_scanner.clone_repository(
                scan.repository_url,
                scan.branch,
                scan.commit_hash,
                settings.GITHUB_TOKEN,
            )

            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(20, "Detecting technology stack...", "Fetching repository", stage="detecting"))

            self._update_progress(progress_callback, 20, "Detecting technology stack...")

            # Detect technology stack from file list
            all_files = self._collect_all_files(Path(repo_path))
            self.detected_stack = detect_technology_stack_from_files(all_files)

            # Update detected stack in progress store and get detected technologies
            detected = []
            if self.progress_store and self.scan_id:
                detected = self.detected_stack.get_detected_technologies()
                if detected:
                    self._exec_async(self.progress_store.update_detected_stack(self.scan_id, detected))

            logger.info(
                "Technology stack detected",
                stack=",".join(detected) or "none",
            )

            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(30, "Loading files...", "Detecting technologies", stage="detecting"))

            self._update_progress(progress_callback, 30, "Loading files...")

            # Load and parse files with progress tracking
            logger.info("Starting file parsing...")
            parsed_files = self._load_and_parse_files(Path(repo_path))

            if not parsed_files:
                raise ValueError("No analyzable files found in repository")

            logger.info(f"✅ File parsing completed: {len(parsed_files)} files parsed")

            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(40, f"Parsed {len(parsed_files)} files...", "Detecting technologies", stage="detecting"))
            self._update_progress(progress_callback, 40, f"Parsed {len(parsed_files)} files...")

            # Extract file paths from parsed files
            file_paths = [str(pf.file_path) for pf in parsed_files]
            logger.info(f"📁 Extracted {len(file_paths)} file paths from parsed files")

            # Clean file paths for display (remove /tmp/devarchai/... prefix)
            import re
            cleaned_file_paths = []
            for fp in file_paths:
                # Remove /tmp/devarchai/{hash}_{repo_name}/ prefix
                match = re.search(r'/tmp/devarchai/[a-zA-Z0-9]+_[^/]+/(.*)', fp)
                if match:
                    cleaned_file_paths.append(match.group(1))
                else:
                    cleaned_file_paths.append(fp)

            logger.info(f"📁 Cleaned file paths example: {cleaned_file_paths[:3] if len(cleaned_file_paths) >= 3 else cleaned_file_paths}")

            # Update progress with actual file count and file list
            if self.progress_store and self.scan_id:
                # Store the file list in the progress store (use cleaned paths)
                logger.info(f"📁 Updating files_list with {len(cleaned_file_paths)} files")
                self._exec_async(self.progress_store.update_files_list(self.scan_id, cleaned_file_paths))
                self._exec_async(self._update_progress_async(
                    50,
                    f"Running rule engine ({len(parsed_files)} files)...",
                    "Running security rules",
                    stage="scanning",
                    files_scanned=len(parsed_files),
                    total_files=len(parsed_files)
                ))
                # Broadcast file list via WebSocket (fire and forget, don't block on it)
                try:
                    from app.websockets.scan_progress import scan_progress_manager
                    self._exec_async(
                        scan_progress_manager.broadcast_progress(
                            self.scan_id,
                            50,
                            "running",
                            current_step="Running security rules",
                            files_list=cleaned_file_paths
                        )
                    )
                except Exception as broadcast_error:
                    logger.warning(f"WebSocket broadcast failed (non-critical): {broadcast_error}")

            self._update_progress(progress_callback, 50, f"Running rule engine ({len(parsed_files)} files)...")

            # Extract resources and run rules with progress updates
            logger.info("Extracting resources from parsed files...")
            resources = self._extract_resources(parsed_files)
            logger.info(f"Extracted {len(resources)} resources")

            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(60, "Running security rules...", "Running security rules", stage="scanning"))
            self._update_progress(progress_callback, 60, "Running security rules...")

            rule_findings = self._run_rules(resources, parsed_files)
            logger.info(f"Rule engine completed with {len(rule_findings)} findings")

            # PHASE: Run external scanners (after rule engine, before enrichment)
            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(63, "Running external scanners...", "Running external scanners", stage="scanning"))
            self._update_progress(progress_callback, 63, "Running external scanners...")

            scanner_results: list[Any] = []
            try:
                from pathlib import Path as _Path

                from app.models.scanner_execution import ScannerExecutionRecord
                scanner_registry = ScannerRegistry()
                scanner_results = scanner_registry.run_for_repo(
                    repo_path=_Path(repo_path),
                    detected_stack=self.detected_stack.to_dict(),
                )
                external_findings: list[RuleFinding] = []
                for result in scanner_results:
                    if result.status.value in ("COMPLETED_WITH_FINDINGS", "COMPLETED_NO_FINDINGS"):
                        external_findings.extend(result.findings)
                        logger.info(f"External scanner {result.scanner_id} completed: {result.findings_count} findings")

                # Persist scanner execution records
                for result in scanner_results:
                    try:
                        db_record = ScannerExecutionRecord(
                            scan_id=self.scan_id,
                            scanner_name=result.scanner_name,
                            scanner_id=result.scanner_id,
                            version=result.version,
                            status=result.status.value,
                            applicable=result.applicable,
                            enabled=result.enabled,
                            execution_start=result.execution_start,
                            execution_end=result.execution_end,
                            duration_ms=result.duration_ms,
                            files_scanned=result.files_scanned,
                            rules_executed=result.rules_executed,
                            findings_count=result.findings_count,
                            skipped_reason=result.skipped_reason,
                            error_message=result.error_message,
                        )
                        self.db.add(db_record)
                    except Exception as db_err:
                        logger.warning("Failed to persist scanner execution record for %s: %s", result.scanner_id, db_err)
                self.db.commit()

                if external_findings:
                    all_findings = rule_findings + external_findings
                    cross_deduped, cross_stats = deduplicate_across_scanners(all_findings)
                    logger.info(
                        "Cross-scanner deduplication",
                        original=len(all_findings),
                        deduplicated=len(cross_deduped),
                        merges=cross_stats.merges,
                    )
                    rule_findings = cross_deduped

                    if self.progress_store and self.scan_id:
                        self._exec_async(self.progress_store.add_log(
                            self.scan_id,
                            f"🔀 External scanners: {len(external_findings)} findings, "
                            f"merged into {len(all_findings) - len(cross_deduped)} duplicates",
                        ))
            except Exception as e:
                logger.error(f"❌ External scanner integration failed: {e}")
                # Recover the session so subsequent DB operations don't fail
                try:
                    self.db.rollback()
                    logger.info("Session rolled back after scanner integration failure")
                except Exception as rb_err:
                    logger.warning("Session rollback after scanner failure also failed: %s", rb_err)
                # Continue with rule engine findings only

            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(70, "Building recommendations...", "Preparing findings", stage="scanning"))
            self._update_progress(progress_callback, 70, "Building recommendations...")

            logger.info("Applying static enrichment before background AI generation", findings_count=len(rule_findings))
            from app.services.findings_enricher import enrich_findings

            rule_findings = enrich_findings(rule_findings)

            if self.progress_store and self.scan_id:
                self._exec_async(
                    self.progress_store.add_log(
                        self.scan_id,
                        "Background AI suggestions queued after static scan results are saved",
                    )
                )

            # PHASE 1C: Deduplicate findings (NEW - Production Grade)
            try:
                from app.services.findings_deduplicator import deduplicate_findings
                rule_findings, dedup_stats = deduplicate_findings(rule_findings)
                dedup_ratio = (dedup_stats.original_count - dedup_stats.deduplicated_count) / max(dedup_stats.original_count, 1) * 100
                logger.info(
                    "Findings deduplicated",
                    original_count=dedup_stats.original_count,
                    deduplicated_count=dedup_stats.deduplicated_count,
                    duplicates_removed=dedup_stats.duplicates_removed,
                    dedup_ratio=f"{dedup_ratio:.1f}%",
                )

                if self.progress_store and self.scan_id:
                    self._exec_async(self.progress_store.add_log(self.scan_id, f"🔍 Deduplicated: {dedup_stats.deduplicated_count} findings ({dedup_stats.duplicates_removed} duplicates removed)"))
            except Exception as e:
                logger.error(f"❌ Deduplication failed: {e}")
                # Continue with non-deduplicated findings - don't break pipeline

            # PHASE 4: Validate findings before DB insert (NEW - Production Grade)
            try:
                from app.services.finding_validator import validate_findings
                rule_findings, validation_stats = validate_findings(rule_findings)
                fallback_rate = validation_stats.findings_with_fallbacks / max(validation_stats.total_findings, 1) * 100
                logger.info(
                    "Findings validated",
                    total_count=validation_stats.total_findings,
                    valid_count=validation_stats.valid_findings,
                    fallbacks_applied=validation_stats.total_fallbacks_applied,
                    fallback_rate=f"{fallback_rate:.1f}%",
                )

                if self.progress_store and self.scan_id:
                    self._exec_async(self._update_progress_async(88, "Validating findings...", "Quality check", stage="completed"))
                    self._exec_async(self.progress_store.add_log(self.scan_id, f"✅ Validated {validation_stats.total_findings} findings"))
            except Exception as e:
                logger.error(f"❌ Validation failed: {e}")
                # Continue with non-validated findings - don't break pipeline

            logger.info(
                "Findings enriched",
                findings_count=len(rule_findings),
                with_fix_examples=sum(1 for f in rule_findings if f.fix_example),
                ai_generated=sum(1 for f in rule_findings if getattr(f, 'ai_generated', False)),
            )

            # Log individual AI findings for debugging
            for f in rule_findings:
                if getattr(f, 'ai_generated', False):
                    logger.info(
                        "AI finding generated",
                        rule_id=f.rule_id,
                        has_summary=bool(f.summary),
                        has_risk=bool(f.risk),
                        has_impact=bool(f.impact),
                        has_fix_code=bool(f.fix_code),
                        has_fix_example=bool(f.fix_example),
                        has_full_example=bool(f.full_example),
                        has_best_practices=bool(f.best_practices),
                        confidence=getattr(f, 'confidence', None),
                    )

            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(90, "Calculating scores...", "Computing metrics", stage="completed"))

            self._update_progress(progress_callback, 90, "Calculating scores...")

            # Calculate scores
            scores = self.scoring_engine.calculate_scores(rule_findings)

            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(92, f"Security score: {scores.score:.0f}%", "Score calculation complete", stage="completed"))

            self._update_progress(progress_callback, 92, f"Security score: {scores.score:.0f}%")

            # Save findings to database
            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(94, "Saving findings to database...", "Persisting results", stage="completed"))
                self._exec_async(self.progress_store.add_log(self.scan_id, "💾 Saving findings to database..."))

            self._save_findings(scan.id, rule_findings)

            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(96, "Generating downloadable reports...", "Building reports", stage="completed"))

            if self.progress_store and self.scan_id:
                self._exec_async(self.progress_store.add_log(self.scan_id, "📄 Building downloadable reports..."))

            self._create_report(
                scan=scan,
                rule_findings=rule_findings,
                scores=scores,
                files_analyzed=cleaned_file_paths,
            )

            if self.progress_store and self.scan_id:
                self._exec_async(self._update_progress_async(98, "Finalizing scan...", "Almost done", stage="completed"))
                self._exec_async(self.progress_store.add_log(self.scan_id, "✅ Scan complete! Preparing results..."))

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
            scan.detected_stack = self.detected_stack.to_dict() if self.detected_stack else None  # Save detected technologies
            scan.ai_status = "pending" if self.include_ai_explanations and rule_findings else "completed"
            scan.ai_error_message = None
            if scan.ai_status == "completed":
                scan.ai_completed_at = datetime.utcnow()

            self.db.commit()

            # Small delay to ensure database commit is visible to other connections
            time.sleep(0.1)

            # Mark scan as complete in progress store
            if self.progress_store and self.scan_id:
                logger.info(
                    f"[LIFECYCLE] scan={self.scan_id} event=COMPLETING "
                    f"timestamp={datetime.utcnow().isoformat()}"
                )
                self._exec_async(self.progress_store.complete_scan(self.scan_id))
                self._exec_async(self.progress_store.add_log(self.scan_id, "Scan completed successfully"))
                if scan.ai_status == "pending":
                    self._exec_async(
                        self.progress_store.add_log(
                            self.scan_id,
                            "AI suggestions are being generated in the background",
                        )
                    )

                # Broadcast scan completion to all connected WebSocket clients
                try:
                    from app.websockets.scan_progress import scan_progress_manager
                    progress_obj = self._exec_async(self.progress_store.get_progress(self.scan_id))
                    if progress_obj:
                        sent = self._exec_async(scan_progress_manager.broadcast_progress(
                            scan_id=self.scan_id,
                            progress=100,
                            status="completed",
                            current_step="Scan completed",
                            steps=[s.dict() for s in progress_obj.steps],
                            logs=progress_obj.logs,
                            detected_stack=progress_obj.detected_stack,
                        ))
                        logger.info(f"Broadcasted scan_complete to {sent} clients for scan {self.scan_id}")
                except Exception as e:
                    logger.warning(f"Failed to broadcast scan completion: {e}")

            self._update_progress(progress_callback, 100, "Scan complete")

            if scan.ai_status == "pending":
                schedule_ai_suggestions_generation(scan.id)

            # PHASE 6: Record scan metrics (NEW - Observability)
            detected = self.detected_stack.get_detected_technologies() if self.detected_stack else []
            try:
                from app.services.metrics import record_scan, record_scan_end
                duration = time.time() - start_time
                record_scan_end()

                # Record for each detected technology
                if detected:
                    for tech in detected:
                        record_scan(status="completed", technology=tech, duration=duration)
                else:
                    record_scan(status="completed", technology="none", duration=duration)

                logger.info(
                    "Scan metrics recorded",
                    duration=duration,
                    technologies=detected,
                )
            except Exception as e:
                logger.warning(f"Failed to record scan metrics: {e}")

            logger.info(
                "Scan completed successfully",
                scan_id=scan.id,
                duration=analysis_duration,
                overall_score=scores.score,
                findings_count=len(rule_findings),
                detected_stack=",".join(detected) or "none",
            )

        except Exception as e:
            logger.exception("Scan failed", scan_id=scan.id, error=str(e))
            scan.status = ScanStatus.FAILED
            scan.ai_status = "failed"
            scan.error_message = str(e)
            scan.completed_at = datetime.utcnow()
            self.db.commit()

            # Mark scan as failed in progress store
            if self.progress_store and self.scan_id:
                self._exec_async(self.progress_store.fail_scan(self.scan_id, str(e)))

                # Broadcast scan failure to all connected WebSocket clients
                try:
                    from app.websockets.scan_progress import scan_progress_manager
                    sent = self._exec_async(scan_progress_manager.broadcast_progress(
                        scan_id=self.scan_id,
                        progress=0,
                        status="failed",
                        current_step="Scan failed",
                        error_message=str(e),
                        logs=[str(e)],
                    ))
                    logger.info(f"Broadcasted scan_failed to {sent} clients for scan {self.scan_id}")
                except Exception as broadcast_error:
                    logger.warning(f"Failed to broadcast scan failure: {broadcast_error}")

            self._update_progress(progress_callback, 0, f"Failed: {str(e)}")
            raise

        finally:
            # Cleanup
            if repo_path:
                self.repo_scanner.cleanup(repo_path)

        return scan

    def _collect_all_files(self, repo_path: Path) -> list[str]:
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

    def _load_and_parse_files(self, repo_path: Path) -> list[ParsedFile]:
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

    def _extract_resources(self, parsed_files: list[ParsedFile]):
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

    def _run_rules(self, resources, parsed_files: list[ParsedFile]):
        """Run rule engine against resources."""
        all_findings = []

        # Run Azure scanner on Terraform files
        azure_scanner = AzureScanner()
        azure_findings = azure_scanner.scan(parsed_files)
        all_findings.extend(azure_findings)

        # Run Helm scanner on chart files
        helm_scanner = HelmScanner()
        helm_findings = helm_scanner.scan("", [
            {"file_path": pf.file_path, "content": pf.raw_content}
            for pf in parsed_files if pf.file_type == "helm"
        ])
        all_findings.extend(helm_findings)

        # Run standard rule engine
        resources_by_file = {}
        for resource in resources:
            file_path = resource.get("file_path", "unknown")
            if file_path not in resources_by_file:
                resources_by_file[file_path] = []
            resources_by_file[file_path].append(resource)

        for parsed_file in parsed_files:
            file_path = str(parsed_file.file_path)
            file_resources = resources_by_file.get(file_path, [])
            # Pass file type to enable proper rule filtering
            file_findings = self.rule_registry.evaluate_all(
                file_resources,
                file_path,
                file_type=parsed_file.file_type
            )
            all_findings.extend(file_findings)

        return all_findings

    def _save_findings(self, scan_id, findings: list[RuleFinding]):
        """Save findings to database with deduplication and error handling."""
        import re
        try:
            # Track unique findings to avoid duplicates
            seen = set()

            for finding in findings:
                try:
                    # Create unique key based on rule_id + file_path + line_number
                    finding_key = (
                        finding.rule_id,
                        finding.file_path or '',
                        finding.line_number or 0
                    )

                    # Skip if we've already seen this exact finding
                    if finding_key in seen:
                        logger.debug(
                            "Skipping duplicate finding",
                            rule_id=finding.rule_id,
                            file_path=finding.file_path,
                            line_number=finding.line_number
                        )
                        continue

                    seen.add(finding_key)

                    # ✅ CRITICAL FIX: Ensure ALL text fields are strings, not dicts/lists
                    def ensure_text_field(value, field_name=""):
                        """Ensure a field value is always a string or None."""
                        if value is None:
                            return None
                        if isinstance(value, str):
                            return value
                        if isinstance(value, dict | list):
                            logger.debug(f"Converting {field_name} from {type(value).__name__} to JSON string")
                            return json.dumps(value)
                        return str(value)

                    # Debug: Check for dict values before creating model
                    text_fields = {
                        'description': finding.description,
                        'recommendation': finding.recommendation,
                        'summary': finding.summary,
                        'risk': finding.risk,
                        'impact': finding.impact,
                        'fix_code': finding.fix_code,
                        'fix_example': finding.fix_example,
                        'full_example': finding.full_example,
                        'best_practices': finding.best_practices,
                        'documentation_url': finding.documentation_url,
                        'ai_explanation': finding.ai_explanation,
                        'impact_analysis': finding.impact_analysis,
                    }

                    # Log any dict/list values
                    for field_name, value in text_fields.items():
                        if isinstance(value, dict | list):
                            logger.warning(
                                f"⚠️ Field '{field_name}' is {type(value).__name__}, converting to string"
                            )

                    # Strip temp directory prefix from file_path for clean relative paths
                    raw_file_path = finding.file_path
                    cleaned_file_path = str(raw_file_path) if raw_file_path else None
                    if cleaned_file_path:
                        match = re.search(r'/tmp/devarchai/[a-zA-Z0-9]+_[^/]+/(.*)', str(cleaned_file_path))
                        if match:
                            cleaned_file_path = match.group(1)

                    db_finding = FindingModel(
                        scan_id=scan_id,
                        rule_id=finding.rule_id,
                        rule_name=finding.rule_name,
                        severity=finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
                        category=finding.category.value if hasattr(finding.category, 'value') else str(finding.category),
                        description=ensure_text_field(finding.description, 'description'),
                        recommendation=ensure_text_field(finding.recommendation, 'recommendation'),
                        # AI Fix Generator fields - ALL ensured to be strings
                        summary=ensure_text_field(finding.summary, 'summary'),
                        risk=ensure_text_field(finding.risk, 'risk'),
                        impact=ensure_text_field(finding.impact, 'impact'),
                        fix_code=ensure_text_field(finding.fix_code, 'fix_code'),
                        fix_example=ensure_text_field(finding.fix_example, 'fix_example'),
                        full_example=ensure_text_field(finding.full_example, 'full_example'),
                        best_practices=ensure_text_field(finding.best_practices, 'best_practices'),
                        confidence=finding.confidence,
                        confidence_score=finding.confidence or 1.0,
                        documentation_url=ensure_text_field(finding.documentation_url, 'documentation_url'),
                        ai_generated=getattr(finding, 'ai_generated', False),
                        # Legacy fields
                        file_path=cleaned_file_path,
                        line_number=finding.line_number,
                        resource_name=finding.resource_name,
                        ai_explanation=ensure_text_field(finding.ai_explanation, 'ai_explanation'),
                        impact_analysis=ensure_text_field(finding.impact_analysis, 'impact_analysis'),
                        # Scanner metadata fields
                        scanner_name=getattr(finding, 'scanner_name', None),
                        scanner_rule_id=getattr(finding, 'scanner_rule_id', None),
                        package=getattr(finding, 'package', None),
                        installed_version=getattr(finding, 'installed_version', None),
                        fixed_version=getattr(finding, 'fixed_version', None),
                        cve=getattr(finding, 'cve', None),
                        cwe=getattr(finding, 'cwe', None),
                        references=ensure_text_field(
                            json.dumps(finding.references) if getattr(finding, 'references', None) else None,
                            'references',
                        ),
                        evidence=getattr(finding, 'evidence', None),
                    )
                    self.db.add(db_finding)
                except Exception as finding_error:
                    logger.warning(
                        f"Failed to save finding {finding.rule_id}: {finding_error}"
                    )
                    import traceback
                    logger.warning(traceback.format_exc())
                    # Continue with next finding - don't break the pipeline

            self.db.flush()
            logger.info(
                "Findings saved",
                total_findings=len(findings),
                unique_findings=len(seen),
                duplicates_removed=len(findings) - len(seen)
            )
        except Exception as e:
            logger.error(f"Error in _save_findings: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Rollback the session to clear the error state
            try:
                self.db.rollback()
                logger.info("Session rolled back after error")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
            # Re-raise to stop the pipeline if save fails
            raise

    def _create_ai_suggestions(self, scan_id, findings: list[RuleFinding]):
        """Create AI suggestions from findings and store in PostgreSQL."""
        try:
            from app.models.ai_suggestion import AISuggestion, FixType, SuggestionStatus

            with self.db.begin_nested():
                # Get all findings from database for this scan
                from sqlalchemy import select

                from app.models.finding import Finding as FindingModel

                result = self.db.execute(
                    select(FindingModel).where(FindingModel.scan_id == scan_id)
                )
                db_findings = result.scalars().all()

                suggestions_created = 0

                for db_finding in db_findings:
                    try:
                        # Skip if suggestion already exists
                        existing = self.db.execute(
                            select(AISuggestion).where(AISuggestion.finding_id == db_finding.id)
                        )
                        if existing.scalars().first():
                            continue

                        # Determine fix type based on file path or category
                        fix_type = FixType.GENERAL
                        if db_finding.file_path:
                            path_lower = db_finding.file_path.lower()
                            if '.tf' in path_lower or 'terraform' in path_lower:
                                fix_type = FixType.TERRAFORM
                            elif 'dockerfile' in path_lower or 'docker' in path_lower:
                                fix_type = FixType.DOCKERFILE
                            elif 'kubernetes' in path_lower or 'k8s' in path_lower or '.yaml' in path_lower:
                                fix_type = FixType.KUBERNETES
                            elif '.github' in path_lower or 'jenkins' in path_lower or 'ci' in path_lower:
                                fix_type = FixType.CI_CD

                        # Create AI suggestion
                        ai_suggestion = AISuggestion(
                            finding_id=db_finding.id,
                            scan_id=scan_id,
                            title=db_finding.summary or db_finding.rule_name or f"Fix {db_finding.rule_id}",
                            description=db_finding.ai_explanation or db_finding.description or "",
                            severity=db_finding.severity,
                            confidence=db_finding.confidence_score or db_finding.confidence or 0.8,
                            category=db_finding.category,
                            fix_type=fix_type,
                            file_path=db_finding.file_path or "",
                            line_number=db_finding.line_number,
                            fix_code=db_finding.fix_code,
                            auto_fix_available=bool(db_finding.fix_code or db_finding.fix_example),
                            status=SuggestionStatus.OPEN,
                            # ✅ CRITICAL FIX: Ensure additional_data is always a JSON string
                            additional_data=json.dumps({
                                "rule_id": db_finding.rule_id,
                                "recommendation": db_finding.recommendation,
                                "best_practices": db_finding.best_practices,
                                "ai_generated": db_finding.ai_generated,
                            }) if db_finding.best_practices or db_finding.recommendation else None,
                        )

                        self.db.add(ai_suggestion)
                        suggestions_created += 1
                    except Exception as suggestion_error:
                        logger.warning(
                            f"Failed to create AI suggestion for finding {db_finding.id}: {suggestion_error}"
                        )
                        continue

                self.db.flush()
            logger.info(
                "AI suggestions created",
                scan_id=scan_id,
                suggestions_count=suggestions_created,
            )
        except Exception as e:
            logger.error(f"Failed to create AI suggestions: {e}")
            # Don't break the pipeline if AI suggestion creation fails

    def _create_report(
        self,
        scan: Scan,
        rule_findings: list[RuleFinding],
        scores: Any,
        files_analyzed: list[str],
    ) -> None:
        """Create the report record and upload PDF/XLSX artifacts to S3."""
        try:
            with self.db.begin_nested():
                report = self.report_service.upsert_report_record_sync(
                    db=self.db,
                    scan=scan,
                    findings=rule_findings,
                    scores=scores,
                    files_analyzed=files_analyzed,
                )
                self.report_service.generate_and_store_artifacts(
                    scan=scan,
                    report=report,
                    findings=rule_findings,
                )
                self.db.flush()
        except Exception as exc:
            logger.exception(
                "Report generation failed",
                scan_id=scan.id,
                error=str(exc),
            )
            if self.progress_store and self.scan_id:
                _safe_await(
                    self.progress_store.add_log(
                        self.scan_id,
                        "⚠️ Report generation failed; scan results were saved without downloadable artifacts",
                    )
                )

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
    commit_hash: str | None = None,
    include_ai_explanations: bool = True,
) -> dict[str, Any]:
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

            # Extract detected technologies from findings
            detected_technologies = []
            devops_stack = {
                'docker': False,
                'terraform': False,
                'kubernetes': False,
                'helm': False,
                'cicd': None,
                'monitoring': False,
                'prometheus': False,
                'grafana': False,
                'ansible': False,
                'pulumi': False,
                'security_scanning': False,
                'aws': False,
                'azure': False,
                'gcp': False,
            }

            # Analyze findings to detect technologies
            if hasattr(updated_scan, 'findings') and updated_scan.findings:
                categories = set()
                for finding in updated_scan.findings:
                    if hasattr(finding, 'category'):
                        cat = finding.category.value if hasattr(finding.category, 'value') else str(finding.category)
                        categories.add(cat.lower())

                    # Detect from file paths
                    if hasattr(finding, 'file_path') and finding.file_path:
                        path = finding.file_path.lower()

                        # Containerization
                        if 'docker' in path or 'dockerfile' in path or 'docker-compose' in path:
                            if 'docker' not in detected_technologies:
                                detected_technologies.append('docker')
                            devops_stack['docker'] = True

                        # Infrastructure as Code - Terraform
                        if 'terraform' in path or '.tf' in path or '.tfvars' in path:
                            if 'terraform' not in detected_technologies:
                                detected_technologies.append('terraform')
                            devops_stack['terraform'] = True

                        # Kubernetes
                        if 'kubernetes' in path or 'k8s' in path or '.yaml' in path or '.yml' in path:
                            if 'kubernetes' not in detected_technologies:
                                detected_technologies.append('kubernetes')
                            devops_stack['kubernetes'] = True

                        # Helm
                        if 'helm' in path or 'chart.yaml' in path or 'chart.yml' in path or 'values.yaml' in path:
                            if 'helm' not in detected_technologies:
                                detected_technologies.append('helm')
                            devops_stack['helm'] = True

                        # CI/CD
                        if '.github/workflows' in path or 'circleci' in path or 'jenkins' in path or 'gitlab-ci' in path or '.gitlab-ci.yml' in path or 'azure-pipelines' in path or 'buildkite' in path:
                            if '.github' in path:
                                devops_stack['cicd'] = 'github_actions'
                            elif 'circleci' in path:
                                devops_stack['cicd'] = 'circleci'
                            elif 'jenkins' in path:
                                devops_stack['cicd'] = 'jenkins'
                            elif 'gitlab' in path:
                                devops_stack['cicd'] = 'gitlab_ci'
                            elif 'azure-pipelines' in path:
                                devops_stack['cicd'] = 'azure_devops'
                            else:
                                devops_stack['cicd'] = 'other'
                            if 'cicd' not in detected_technologies:
                                detected_technologies.append('cicd')

                        # Monitoring & Observability
                        if 'prometheus' in path or 'alertmanager' in path or 'promtail' in path:
                            if 'prometheus' not in detected_technologies:
                                detected_technologies.append('prometheus')
                            devops_stack['prometheus'] = True
                            devops_stack['monitoring'] = True
                        if 'grafana' in path:
                            if 'grafana' not in detected_technologies:
                                detected_technologies.append('grafana')
                            devops_stack['grafana'] = True
                            devops_stack['monitoring'] = True
                        if 'loki' in path or 'tempo' in path:
                            if 'loki' not in detected_technologies:
                                detected_technologies.append('loki')
                            devops_stack['monitoring'] = True
                        if 'jaeger' in path:
                            if 'jaeger' not in detected_technologies:
                                detected_technologies.append('jaeger')
                            devops_stack['monitoring'] = True

                        # Configuration Management
                        if 'ansible' in path or '.yml' in path and 'playbook' in path or 'inventory' in path:
                            if 'ansible' not in detected_technologies:
                                detected_technologies.append('ansible')
                            devops_stack['ansible'] = True

                        # Infrastructure as Code - Pulumi
                        if 'pulumi' in path or 'Pulumi.yaml' in path or 'Pulumi.dev.yaml' in path:
                            if 'pulumi' not in detected_technologies:
                                detected_technologies.append('pulumi')
                            devops_stack['pulumi'] = True

                        # Security Scanning
                        if 'security' in path or 'trivy' in path or 'snyk' in path or 'sonarqube' in path or 'aquasec' in path:
                            if 'security_scanning' not in detected_technologies:
                                detected_technologies.append('security_scanning')
                            devops_stack['security_scanning'] = True

                        # Cloud Providers - AWS
                        if 'aws' in path or 'amazon' in path or '.aws' in path or 'ec2' in path or 's3' in path or 'lambda' in path or 'cloudformation' in path or 'iam' in path or 'vpc' in path or 'rds' in path or 'eks' in path or 'ecs' in path or 'dynamodb' in path or 'sqs' in path or 'sns' in path or 'cloudwatch' in path or 'cloudfront' in path or 'route53' in path or 'elastic' in path:
                            if 'aws' not in detected_technologies:
                                detected_technologies.append('aws')
                            devops_stack['aws'] = True

                        # Cloud Providers - Azure
                        if 'azure' in path or 'microsoft' in path or '.azure' in path or 'aks' in path or 'arm' in path or 'bicep' in path or 'app service' in path or 'function app' in path or 'cosmos' in path or 'blob storage' in path or 'azure devops' in path or 'azure ad' in path or 'key vault' in path or 'service bus' in path:
                            if 'azure' not in detected_technologies:
                                detected_technologies.append('azure')
                            devops_stack['azure'] = True

                        # Cloud Providers - GCP
                        if 'gcp' in path or 'google' in path or '.gcp' in path or 'gke' in path or 'bigquery' in path or 'cloud functions' in path or 'cloud run' in path or 'gcs' in path or 'pubsub' in path or 'cloud sql' in path or 'iam' in path and 'google' in path:
                            if 'gcp' not in detected_technologies:
                                detected_technologies.append('gcp')
                            devops_stack['gcp'] = True

                        # Additional DevOps Tools
                        if 'nginx' in path or 'apache' in path or 'traefik' in path or 'envoy' in path:
                            if 'load_balancer' not in detected_technologies:
                                detected_technologies.append('load_balancer')
                        if 'redis' in path or 'memcached' in path:
                            if 'redis' not in detected_technologies:
                                detected_technologies.append('redis')
                        if 'postgres' in path or 'postgresql' in path or 'mysql' in path or 'mongodb' in path or 'database' in path:
                            if 'database' not in detected_technologies:
                                detected_technologies.append('database')
                        if 'vault' in path or 'secrets' in path:
                            if 'vault' not in detected_technologies:
                                detected_technologies.append('vault')
                        if 'consul' in path:
                            if 'consul' not in detected_technologies:
                                detected_technologies.append('consul')
                        if 'istio' in path or 'linkerd' in path or 'service mesh' in path:
                            if 'service_mesh' not in detected_technologies:
                                detected_technologies.append('service_mesh')
                        if 'argocd' in path or 'flux' in path or 'gitops' in path:
                            if 'gitops' not in detected_technologies:
                                detected_technologies.append('gitops')
                        if 'jenkins' in path:
                            if 'jenkins' not in detected_technologies:
                                detected_technologies.append('jenkins')
                        if 'nexus' in path or 'artifactory' in path or 'package registry' in path:
                            if 'artifact_registry' not in detected_technologies:
                                detected_technologies.append('artifact_registry')

                # Add categories as detected technologies
                if 'security' in categories and 'security_scanning' not in detected_technologies:
                    detected_technologies.append('security')
                if 'reliability' in categories:
                    detected_technologies.append('reliability')
                if 'scalability' in categories:
                    detected_technologies.append('scalability')
                if 'cost' in categories:
                    detected_technologies.append('cost_optimization')
                if 'observability' in categories:
                    if 'observability' not in detected_technologies:
                        detected_technologies.append('observability')
                    if 'monitoring' not in detected_technologies:
                        detected_technologies.append('monitoring')
                        devops_stack['monitoring'] = True

            # Remove duplicates and sort
            detected_technologies = sorted(set(detected_technologies))
        finally:
            db.close()

        logger.info(
            "Repository scan completed",
            scan_id=scan_id,
            score=overall_score,
            findings=findings_count,
            technologies=len(detected_technologies),
        )

        return {
            "status": "completed",
            "scan_id": str(scan_id),
            "overall_score": overall_score,
            "findings_count": findings_count,
            "detected_technologies": detected_technologies,
            "devops_stack": devops_stack,
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
def cancel_scan_task(self, scan_id: int) -> dict[str, Any]:
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
def cleanup_old_scans_task(self, days_old: int = 30) -> dict[str, Any]:
    """Clean up old scans and their data."""
    from datetime import timedelta

    from sqlalchemy import delete, func, select

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
