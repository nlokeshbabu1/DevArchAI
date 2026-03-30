"""
Celery Tasks for Repository Scanning with Dynamic Scanner Execution
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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
from app.scanners.helm_scanner import HelmScanner
from app.scoring.engine import ScoringEngine
from app.utils.repository_scanner import RepositoryScanner
from app.workers.celery_config import celery_app

logger = get_logger(__name__)


def _run_ai_enrichment_in_process(findings_data, file_contents_data):
    """Run AI enrichment in a separate process with its own event loop.
    
    This function MUST be at module level for multiprocessing to work.
    """
    from app.services.findings_enricher import enrich_findings_with_ai
    from app.rule_engine.base import RuleFinding, Severity, Category
    import asyncio
    
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


def _safe_await(coro):
    """
    Safely await a coroutine from sync code.
    If there's a running event loop, schedule the coroutine; otherwise run it.
    """
    try:
        loop = asyncio.get_running_loop()
        # Running in async context - schedule the task but don't await
        # This is a fire-and-forget approach for progress updates
        asyncio.create_task(coro)
        return None
    except RuntimeError:
        # No running loop - safe to run synchronously
        return asyncio.run(coro)


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
    ):
        self.db = db
        self.include_ai_explanations = include_ai_explanations
        self.progress_store = progress_store
        self.scan_id = scan_id
        self.rule_registry = RuleRegistry()
        self.scoring_engine = ScoringEngine()
        self.repo_scanner = RepositoryScanner()
        self.parser_registry = self._setup_parsers()
        self.detected_stack = DetectedTechnologyStack()

    async def _update_progress_async(self, progress: int, message: str, step_name: Optional[str] = None):
        """Update progress in the store (async)."""
        if self.progress_store and self.scan_id:
            await self.progress_store.update_status(self.scan_id, "running", progress, message)
            if message:
                await self.progress_store.add_log(self.scan_id, message)
            if step_name:
                from app.schemas.scan_progress import StepStatus
                # Mark previous running step as completed
                for step in (await self.progress_store.get_progress(self.scan_id)).steps:
                    if step.status == StepStatus.RUNNING:
                        await self.progress_store.update_step(self.scan_id, step.name, StepStatus.COMPLETED, 100)
                        break
                # Mark current step as running
                await self.progress_store.update_step(self.scan_id, step_name, StepStatus.RUNNING, progress)

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
        import asyncio
        
        start_time = time.time()
        repo_path = None

        try:
            # Update status to processing
            scan.status = ScanStatus.PROCESSING
            scan.started_at = datetime.utcnow()
            self.db.commit()

            # Initialize progress tracking
            if self.progress_store and self.scan_id:
                _safe_await(self._update_progress_async(10, "Cloning repository...", "Connecting to GitHub"))

            self._update_progress(progress_callback, 10, "Cloning repository...")

            # Clone repository
            repo_path, repo_info = self.repo_scanner.clone_repository(
                scan.repository_url,
                scan.branch,
                scan.commit_hash,
                settings.GITHUB_TOKEN,
            )

            if self.progress_store and self.scan_id:
                _safe_await(self._update_progress_async(20, "Detecting technology stack...", "Fetching repository"))

            self._update_progress(progress_callback, 20, "Detecting technology stack...")

            # Detect technology stack from file list
            all_files = self._collect_all_files(Path(repo_path))
            self.detected_stack = detect_technology_stack_from_files(all_files)

            # Update detected stack in progress store and get detected technologies
            detected = []
            if self.progress_store and self.scan_id:
                detected = self.detected_stack.get_detected_technologies()
                if detected:
                    _safe_await(self.progress_store.update_detected_stack(self.scan_id, detected))

            logger.info(
                "Technology stack detected",
                stack=",".join(detected) or "none",
            )

            if self.progress_store and self.scan_id:
                _safe_await(self._update_progress_async(30, "Loading files...", "Detecting technologies"))

            self._update_progress(progress_callback, 30, "Loading files...")

            # Load and parse files
            parsed_files = self._load_and_parse_files(Path(repo_path))

            if not parsed_files:
                raise ValueError("No analyzable files found in repository")

            if self.progress_store and self.scan_id:
                _safe_await(self._update_progress_async(50, f"Running rule engine ({len(parsed_files)} files)...", "Running security rules"))

            self._update_progress(progress_callback, 50, f"Running rule engine ({len(parsed_files)} files)...")

            # Extract resources and run rules
            resources = self._extract_resources(parsed_files)
            rule_findings = self._run_rules(resources, parsed_files)

            # Enrich findings with AI fix data
            logger.info("Enriching findings with AI data...", findings_count=len(rule_findings))

            # Use AI-powered enrichment (with static fallback)
            from app.services.findings_enricher import enrich_findings_with_ai

            # Get file contents for AI context
            file_contents = {}
            for finding in rule_findings:
                if finding.file_path and not file_contents.get(finding.file_path):
                    try:
                        file_path = Path(finding.file_path)
                        if file_path.exists():
                            file_contents[str(file_path)] = file_path.read_text(encoding="utf-8")
                            logger.debug(f"✅ Read file content for {finding.file_path} ({len(file_contents[str(file_path)])} chars)")
                        else:
                            logger.warning(f"❌ File not found: {finding.file_path}")
                    except Exception as e:
                        logger.error(f"❌ Could not read file {finding.file_path}: {e}")

            logger.info(f"File contents loaded: {len(file_contents)} files")
            logger.info(f"Mistral API key configured: {bool(settings.MISTRAL_API_KEY)}")

            # Run AI enrichment in a SEPARATE PROCESS to avoid uvloop conflicts
            try:
                logger.info("🚀 Starting AI enrichment in separate process...")
                
                import multiprocessing
                
                # Serialize findings for multiprocessing
                findings_data = []
                for f in rule_findings:
                    findings_data.append({
                        'rule_id': f.rule_id,
                        'rule_name': f.rule_name,
                        'severity': f.severity.value if hasattr(f.severity, 'value') else str(f.severity),
                        'category': f.category.value if hasattr(f.category, 'value') else str(f.category),
                        'description': f.description,
                        'recommendation': f.recommendation,
                        'file_path': f.file_path,
                        'line_number': f.line_number,
                        'resource_name': f.resource_name,
                    })
                
                # Run AI enrichment in separate process using module-level function
                with multiprocessing.Pool(processes=1) as pool:
                    enriched_findings = pool.apply(_run_ai_enrichment_in_process, (findings_data, file_contents))
                
                # Merge enriched data back into original findings
                enriched_map = {f.rule_id: f for f in enriched_findings}
                for finding in rule_findings:
                    if finding.rule_id in enriched_map:
                        enriched = enriched_map[finding.rule_id]
                        # Copy AI-generated fields
                        if not finding.summary and enriched.summary:
                            finding.summary = enriched.summary
                        if not finding.risk and enriched.risk:
                            finding.risk = enriched.risk
                        if not finding.impact and enriched.impact:
                            finding.impact = enriched.impact
                        if not finding.fix_code and enriched.fix_code:
                            finding.fix_code = enriched.fix_code
                        if not finding.fix_example and enriched.fix_example:
                            finding.fix_example = enriched.fix_example
                        if not finding.full_example and enriched.full_example:
                            finding.full_example = enriched.full_example
                        if not finding.best_practices and enriched.best_practices:
                            finding.best_practices = enriched.best_practices
                        if enriched.ai_generated:
                            finding.ai_generated = True
                        if enriched.confidence:
                            finding.confidence = enriched.confidence
                        # Copy ai_explanation (IMPORTANT - don't lose this!)
                        if not finding.ai_explanation and enriched.ai_explanation:
                            finding.ai_explanation = enriched.ai_explanation
                        # Copy diff fields from metadata
                        if enriched.metadata.get('before_code'):
                            finding.metadata['before_code'] = enriched.metadata['before_code']
                        if enriched.metadata.get('after_code'):
                            finding.metadata['after_code'] = enriched.metadata['after_code']
                        if enriched.metadata.get('unified_diff'):
                            finding.metadata['unified_diff'] = enriched.metadata['unified_diff']
                
                ai_count = sum(1 for f in rule_findings if getattr(f, 'ai_generated', False))
                logger.info(f"✅ AI enrichment completed successfully! Generated {ai_count}/{len(rule_findings)} AI findings")
                
            except Exception as e:
                logger.error(f"❌ AI enrichment failed: {e}")
                logger.warning("Using static enrichment as fallback")
                from app.services.findings_enricher import enrich_findings
                rule_findings = enrich_findings(rule_findings)
            
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
                _safe_await(self._update_progress_async(80, "Calculating scores...", "Generating AI suggestions"))

            self._update_progress(progress_callback, 80, "Calculating scores...")

            # Calculate scores
            scores = self.scoring_engine.calculate_scores(rule_findings)

            if self.progress_store and self.scan_id:
                _safe_await(self._update_progress_async(90, "Saving results...", "Calculating score"))

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
            scan.detected_stack = self.detected_stack.to_dict() if self.detected_stack else None  # Save detected technologies

            self.db.commit()

            # Mark scan as complete in progress store
            if self.progress_store and self.scan_id:
                _safe_await(self.progress_store.complete_scan(self.scan_id))
                _safe_await(self.progress_store.add_log(self.scan_id, "Scan completed successfully"))

            self._update_progress(progress_callback, 100, "Scan complete")

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
            scan.error_message = str(e)
            scan.completed_at = datetime.utcnow()
            self.db.commit()

            # Mark scan as failed in progress store
            if self.progress_store and self.scan_id:
                _safe_await(self.progress_store.fail_scan(self.scan_id, str(e)))

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
        """Save findings to database with deduplication."""
        # Track unique findings to avoid duplicates
        seen = set()
        
        for finding in findings:
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
            
            db_finding = FindingModel(
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
                confidence_score=finding.confidence or 1.0,
                documentation_url=finding.documentation_url,
                ai_generated=getattr(finding, 'ai_generated', False),
                # Legacy fields
                file_path=finding.file_path,
                line_number=finding.line_number,
                resource_name=finding.resource_name,
                ai_explanation=finding.ai_explanation,
                impact_analysis=finding.impact_analysis,
            )
            self.db.add(db_finding)

        self.db.flush()
        logger.info(
            "Findings saved",
            total_findings=len(findings),
            unique_findings=len(seen),
            duplicates_removed=len(findings) - len(seen)
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
    commit_hash: Optional[str] = None,
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
            detected_technologies = sorted(list(set(detected_technologies)))
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
