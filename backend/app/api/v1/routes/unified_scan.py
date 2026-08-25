"""
Unified Scan API - Works for BOTH guest and authenticated users.

Provides real-time progress tracking with step-by-step updates.
"""

import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.security import get_optional_user
from app.core.validators import parse_uuid, validate_branch, validate_repository_url
from app.db.session import get_db, get_sync_session_factory
from app.models.anonymous_scan import AnonymousScan
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.services.scan_progress_store import get_scan_progress_store
from app.services.technology_classifier import classify_technology
from app.workers.tasks.scan_repository import SyncScanService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/scan", tags=["Unified Scan"])


class UnifiedScanRequest(BaseModel):
    """Request model for unified scan endpoint."""

    repository_id: str | None = Field(default=None, max_length=64)
    repository_url: str = Field(
        ...,
        min_length=10,
        max_length=500,
    )
    branch: str = Field(
        default="main",
        max_length=100,
    )
    include_ai_explanations: bool = True

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, v: str) -> str:
        """Validate repository URL format."""
        return validate_repository_url(v)

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        """Validate branch name format."""
        return validate_branch(v)


def _run_scan_in_background(
    scan_id: str,
    repository_url: str,
    branch: str,
    include_ai_explanations: bool,
    session_token: str | None = None,
):
    """Run scan in a background thread with proper progress tracking."""
    # Import at function level to avoid scoping issues
    import asyncio

    from app.services.scan_progress_store import get_scan_progress_store

    # Create a persistent event loop for this background thread
    # KEEP IT ALIVE for the entire scan duration — never close it before execute_scan completes
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    try:
        logger.info(f"🚀 Starting background scan for {scan_id}")

        # Get sync database session
        SessionLocal = get_sync_session_factory()
        sync_db = SessionLocal()

        try:
            # Get scan record
            from app.models.scan import Scan as SyncScan

            sync_scan = sync_db.get(SyncScan, scan_id)

            if not sync_scan:
                logger.error(f"Scan not found in background task: {scan_id}")
                return

            # Initialize progress store FIRST before creating service
            store = get_scan_progress_store()

            # Ensure scan exists in progress store — use the persistent loop
            try:
                _loop.run_until_complete(store.create_scan(scan_id))
                _loop.run_until_complete(
                    store.add_log(scan_id, f"Scan started for {repository_url}")
                )
                _loop.run_until_complete(store.add_log(scan_id, f"Branch: {branch}"))
                _loop.run_until_complete(
                    store.update_status(scan_id, "running", 5, "Initializing scan...")
                )
                logger.info(
                    f"[LIFECYCLE] scan={scan_id} event=PROGRESS_STORE_INIT "
                    f"status=running progress=5 timestamp={datetime.utcnow().isoformat()}"
                )
            except Exception as e:
                logger.warning(f"Progress store initialization warning: {e}")

            # Create scan service with progress store
            scan_service = SyncScanService(
                db=sync_db,
                include_ai_explanations=include_ai_explanations,
                progress_store=store,
                scan_id=scan_id,
                event_loop=_loop,  # Pass the persistent loop so SyncScanService reuses it
            )

            # Execute scan (this takes 30-60 seconds)
            updated_scan = scan_service.execute_scan(sync_scan)

            logger.info(
                f"✅ Background scan completed: {scan_id}, status={updated_scan.status.value}"
            )
            logger.info(
                f"[LIFECYCLE] scan={scan_id} event=SCAN_EXEC_COMPLETE "
                f"db_status={updated_scan.status.value} "
                f"timestamp={datetime.utcnow().isoformat()}"
            )

        finally:
            sync_db.close()

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"❌ Background scan failed: {error_msg}")

        # Update progress store with failure — use the same persistent loop
        store = get_scan_progress_store()
        try:
            _loop.run_until_complete(store.fail_scan(scan_id, error_msg))
        except Exception as update_error:
            logger.error(f"Failed to update progress store on error: {update_error}")
    finally:
        # Clean up the persistent event loop only after everything is done
        try:
            _loop.run_until_complete(asyncio.sleep(0))  # flush any pending callbacks
            _loop.close()
        except Exception:
            pass


@router.post("/start", response_model=dict[str, Any])
async def start_unified_scan(
    request: UnifiedScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Start a unified scan that works for BOTH guest and authenticated users.

    Returns:
    - scan_id: Unique identifier for tracking progress
    - session_token: For guest users to retrieve results
    - status: Initial scan status
    """
    try:
        # Generate identifiers
        scan_id = str(uuid4())
        session_token = None
        repository = None
        repository_url = request.repository_url.strip()

        if request.repository_id:
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Authentication required for repository-linked scans",
                )

            try:
                repository_uuid = UUID(request.repository_id)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid repository_id: {request.repository_id}",
                ) from exc

            repository_result = await db.execute(
                select(Repository).where(
                    Repository.id == repository_uuid,
                    Repository.user_id == current_user.id,
                    Repository.is_active.is_(True),
                )
            )
            repository = repository_result.scalar_one_or_none()

            if not repository:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found",
                )

            repository_url = repository.url

            existing_scan_result = await db.execute(
                select(Scan)
                .where(
                    Scan.user_id == current_user.id,
                    Scan.repository_id == repository.id,
                    Scan.status.in_([ScanStatus.PENDING, ScanStatus.PROCESSING, ScanStatus.QUEUED]),
                )
                .order_by(Scan.created_at.desc())
                .limit(1)
            )
            existing_scan = existing_scan_result.scalar_one_or_none()

            if existing_scan:
                return {
                    "scan_id": str(existing_scan.id),
                    "session_token": None,
                    "status": existing_scan.status.value,
                    "message": "A scan is already in progress for this repository",
                    "repository_id": str(repository.id),
                    "repository_url": repository.url,
                    "branch": existing_scan.branch,
                }

        # Auto-detect branch from GitHub API if not specified or is 'main'
        branch = request.branch or "main"
        if branch == "main":
            try:
                import httpx

                # Extract owner and repo from URL
                url_parts = repository_url.rstrip("/").split("/")
                if len(url_parts) >= 2:
                    owner = url_parts[-2]
                    repo = url_parts[-1].replace(".git", "")

                    # Try to get default branch from GitHub API
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        api_url = f"https://api.github.com/repos/{owner}/{repo}"
                        headers = {}
                        if settings.GITHUB_TOKEN:
                            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
                        response = await client.get(api_url, headers=headers)
                        if response.status_code == 200:
                            repo_data = response.json()
                            branch = repo_data.get("default_branch", "main")
                            logger.info(f"✅ Detected default branch: {branch} for {owner}/{repo}")
                        else:
                            logger.warning(
                                f"GitHub API returned {response.status_code}, using default: main"
                            )
            except Exception as e:
                logger.warning(
                    f"❌ Could not detect branch from GitHub API: {e}, using default: main"
                )

        # Create scan record FIRST so we always use a single scan_id everywhere
        scan_id_uuid = uuid4()
        scan = Scan(
            id=scan_id_uuid,
            user_id=current_user.id if current_user else None,
            repository_id=repository.id if repository else None,
            repository_url=repository_url,
            branch=branch,
            status=ScanStatus.PENDING,
            progress=0,
        )
        scan_id = str(scan_id_uuid)

        # For guest users, create anonymous scan record
        if not current_user:
            session_token = AnonymousScan.generate_session_token()
            expires_at = AnonymousScan.get_expiry()

            # Extract repo name
            repo_name = request.repository_url.rstrip("/").split("/")[-1].replace(".git", "")

            # Create anonymous scan session linked to the same scan_id
            anon_scan = AnonymousScan(
                session_token=session_token,
                repository_url=repository_url,
                repository_name=repo_name,
                branch=branch,
                expires_at=expires_at,
                status="pending",
                linked_scan_id=scan_id,
            )
            db.add(anon_scan)
            logger.info(f"Anonymous scan session created: {session_token}")

        db.add(scan)
        await db.commit()
        await db.refresh(scan)

        # Initialize progress tracking with the SAME scan_id
        store = get_scan_progress_store()
        await store.create_scan(scan_id)
        await store.add_log(scan_id, f"Scan started for {repository_url}")
        await store.add_log(scan_id, f"Branch: {branch}")

        # Run scan in BACKGROUND - returns immediately
        logger.info(f"🚀 Queueing background scan for {scan_id}")
        logger.info(
            f"[LIFECYCLE] scan={scan_id} event=START_API_RESPONSE "
            f"status=running timestamp={datetime.utcnow().isoformat()}"
        )
        background_tasks.add_task(
            _run_scan_in_background,
            scan_id=scan_id,
            repository_url=repository_url,
            branch=branch,
            include_ai_explanations=request.include_ai_explanations,
            session_token=session_token,
        )

        # Return response IMMEDIATELY — scan hasn't started yet, status is PENDING
        return {
            "scan_id": scan_id,
            "session_token": session_token,
            "status": "pending",
            "message": "Scan queued — progress will be streamed via WebSocket",
            "repository_id": str(repository.id) if repository else None,
            "repository_url": repository_url,
            "branch": branch,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to start scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scan: {str(e)}",
        )


@router.get("/stages", response_model=dict[str, Any])
async def get_scan_stages():
    """
    Get user-facing scan lifecycle stage metadata for the frontend.

    Returns the ordered list of lifecycle steps with display labels and icons.
    The frontend renders these directly — no hardcoded stage definitions.
    """
    from app.services.scan_lifecycle import lifecycle_stages_payload

    return {"stages": lifecycle_stages_payload()}


@router.get("/status/{scan_id}", response_model=dict[str, Any])
async def get_scan_status(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Get real-time scan progress status.

    Returns current step, progress percentage, and logs.
    Works for BOTH guest and authenticated users.

    CRITICAL: Falls back to DB if progress store is stale/missing,
    ensuring the frontend always detects terminal states (completed/failed).
    """
    from app.services.scan_progress_store import get_scan_progress_store

    parse_uuid(scan_id, "scan_id")
    store = get_scan_progress_store()
    progress = await store.get_progress(scan_id)

    # Always fetch DB status for cross-checking (avoids stale progress store lock)
    db_result = await db.execute(select(Scan).where(Scan.id == scan_id))
    db_scan = db_result.scalar_one_or_none()

    if not db_scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    # Check access for authenticated scans
    if db_scan.user_id and not current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required",
        )

    if db_scan.user_id and current_user and db_scan.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # ---- DB is the AUTHORITY for terminal states ----
    # If the DB says completed/failed, ALWAYS return that — even if progress store
    # has a stale "running" entry. This is the key fix for the stuck overlay.
    if db_scan.status in (ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED):
        # Clean up any stale progress store entry
        if progress:
            logger.info(f"🗑️ Cleaning up stale progress store entry for completed scan {scan_id}")
            await store.cleanup_scan(scan_id)

        detected_techs = []
        if db_scan.detected_stack:
            if isinstance(db_scan.detected_stack, dict):
                detected_techs = db_scan.detected_stack.get("detected_stack", [])
            elif isinstance(db_scan.detected_stack, list):
                detected_techs = db_scan.detected_stack

        is_terminal = db_scan.status == ScanStatus.COMPLETED
        logger.info(
            f"[STATUS] scan={scan_id} db_status={db_scan.status.value} "
            f"progress_store={'present' if progress else 'absent'} "
            f"transition=DB_TERMINAL timestamp={datetime.utcnow().isoformat()}"
        )
        return {
            "scan_id": str(db_scan.id),
            "status": db_scan.status.value,
            "progress": 100 if is_terminal else db_scan.progress,
            "current_step": "Scan completed" if is_terminal else db_scan.status.value,
            "steps": [],
            "detected_stack": detected_techs,
            "logs": [f"Scan {db_scan.status.value} at {db_scan.created_at}"],
            "created_at": db_scan.created_at.isoformat(),
            "completed_at": db_scan.completed_at.isoformat() if db_scan.completed_at else None,
            "error_message": db_scan.error_message,
        }

    # ---- Progress store is the authority for IN-FLIGHT state ----
    if not progress:
        # No progress store entry and DB says non-terminal → in-flight but not yet started
        logger.info(
            f"[STATUS] scan={scan_id} db_status={db_scan.status.value} "
            f"progress_store=absent transition=NO_STORE timestamp={datetime.utcnow().isoformat()}"
        )
        return {
            "scan_id": str(db_scan.id),
            "status": db_scan.status.value,
            "progress": db_scan.progress or 0,
            "current_step": db_scan.status.value,
            "steps": [],
            "detected_stack": [],
            "logs": [f"Scan {db_scan.status.value}"],
            "created_at": db_scan.created_at.isoformat(),
            "completed_at": None,
            "error_message": db_scan.error_message,
        }

    # ---- Progress store has an in-flight entry ----
    # Check if the store entry is stale (no progress movement for 60+ seconds)
    stale_threshold = datetime.utcnow() - timedelta(seconds=60)
    if (
        progress.created_at
        and progress.created_at.replace(tzinfo=None) < stale_threshold
        and progress.progress == progress._last_progress
    ):
        logger.warning(
            f"[STATUS] scan={scan_id} db_status={db_scan.status.value} "
            f"progress_store_status={progress.status} progress_store_pct={progress.progress} "
            f"transition=STALE timestamp={datetime.utcnow().isoformat()}"
        )

    logger.info(
        f"[STATUS] scan={scan_id} db_status={db_scan.status.value} "
        f"progress_store_status={progress.status} progress_store_pct={progress.progress} "
        f"current_step={progress.current_step} transition=IN_FLIGHT timestamp={datetime.utcnow().isoformat()}"
    )

    return {
        "scan_id": progress.scan_id,
        "status": progress.status,
        "progress": progress.progress,
        "current_step": progress.current_step,
        "steps": [step.dict() for step in progress.steps],
        "detected_stack": progress.detected_stack,
        "logs": progress.logs,
        "files_list": progress.files_list if hasattr(progress, "files_list") else [],
        "files_scanned": progress.files_scanned if hasattr(progress, "files_scanned") else 0,
        "total_files": progress.total_files if hasattr(progress, "total_files") else 0,
        "created_at": progress.created_at.isoformat(),
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "error_message": progress.error_message,
    }


def _severity_key(finding: Any) -> str:
    """Return the normalized lowercase severity bucket for a finding."""
    sev = finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)
    return (sev or "info").lower()


SEVERITY_BUCKETS = ("critical", "high", "medium", "low", "info")


def _finding_matches_tech(finding: Any, tech: str) -> bool:
    """Check if a finding belongs to a specific technology.

    Uses the canonical technology classifier so each finding can match at
    most one technology (a Helm chart file is never also a Kubernetes file).
    """
    return classify_technology(finding.file_path, finding.scanner_name) == tech


def _detect_finding_technology(finding: Any) -> str:
    """Detect the canonical technology for a finding.

    Every finding is assigned EXACTLY one technology based on its file path
    (priority: Helm > Docker > GitHub Actions > Terraform > Kubernetes), so a
    finding can never appear on more than one Technology Coverage card.
    """
    return classify_technology(finding.file_path, finding.scanner_name)


@router.get("/results/{scan_id}", response_model=dict[str, Any])
async def get_scan_results(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Get complete scan results after completion.

    Returns:
    - Security score
    - Findings with severity counts
    - AI suggestions
    - Detected technology stack
    """
    parse_uuid(scan_id, "scan_id")
    # Get scan (eagerly load scanner_executions to avoid lazy-load in async context)
    result = await db.execute(
        select(Scan).options(selectinload(Scan.scanner_executions)).where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Check access
    if scan.user_id and not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")

    if scan.user_id and current_user and scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if scan.status != ScanStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Scan not completed. Status: {scan.status.value}",
        )

    # Get findings
    from app.models.finding import Finding

    findings_result = await db.execute(select(Finding).where(Finding.scan_id == scan_id))
    findings = findings_result.scalars().all()

    # Count by severity. All five buckets are always present (zero-filled) so
    # consumers can rely on total == sum(severity_counts.values()).
    severity_counts = {bucket: 0 for bucket in SEVERITY_BUCKETS}
    for f in findings:
        severity_counts[_severity_key(f)] = severity_counts.get(_severity_key(f), 0) + 1

    # Get AI suggestions
    from app.models.ai_suggestion import AISuggestion

    suggestions_result = await db.execute(
        select(AISuggestion).where(AISuggestion.scan_id == scan_id)
    )
    suggestions = suggestions_result.scalars().all()

    # Get detected technologies from findings file paths.
    # (Progress store data expires, so we extract from permanent findings data.)
    # Each finding contributes EXACTLY ONE canonical technology so a Helm chart
    # under a kubernetes/ directory is not falsely reported as Kubernetes.
    detected_technologies = []

    for f in findings:
        if not f.file_path:
            continue

        tech = classify_technology(f.file_path, f.scanner_name)
        if tech in ("code", "secrets", "dependencies"):
            # No technology card exists for these; they are not file-type
            # technologies and must not trigger a coverage card.
            continue
        if tech not in detected_technologies:
            detected_technologies.append(tech)

    # PHASE 2: Also add technologies from detected_stack (even if no findings for them)
    if scan.detected_stack:
        stack = scan.detected_stack
        if stack.get("has_jenkins") or stack.get("jenkins_files"):
            if "jenkins" not in detected_technologies:
                detected_technologies.append("jenkins")
        if stack.get("has_gitlab_ci") or stack.get("gitlab_ci_files"):
            if "gitlab_ci" not in detected_technologies:
                detected_technologies.append("gitlab_ci")
        if stack.get("has_circleci") or stack.get("circleci_files"):
            if "circleci" not in detected_technologies:
                detected_technologies.append("circleci")
        if stack.get("has_azure_devops") or stack.get("azure_devops_files"):
            if "azure_devops" not in detected_technologies:
                detected_technologies.append("azure_devops")
        if stack.get("has_ansible") or stack.get("ansible_files"):
            if "ansible" not in detected_technologies:
                detected_technologies.append("ansible")
        if stack.get("has_prometheus") or stack.get("prometheus_files"):
            if "prometheus" not in detected_technologies:
                detected_technologies.append("prometheus")
        if stack.get("has_grafana") or stack.get("grafana_files"):
            if "grafana" not in detected_technologies:
                detected_technologies.append("grafana")

    # Calculate files analyzed from detected_stack (stored in scan.detected_stack)
    # This ensures we show files analyzed even if no findings were detected
    files_analyzed = 0
    if scan.detected_stack:
        # Count total files from all technologies
        stack = scan.detected_stack
        files_analyzed = (
            len(stack.get("docker_files", []))
            + len(stack.get("terraform_files", []))
            + len(stack.get("kubernetes_files", []))
            + len(stack.get("github_actions_files", []))
            + len(stack.get("gitlab_ci_files", []))
            + len(stack.get("jenkins_files", []))
            + len(stack.get("docker_compose_files", []))
            + len(stack.get("helm_files", []))
            + len(stack.get("ansible_files", []))
            + len(stack.get("circleci_files", []))
            + len(stack.get("azure_devops_files", []))
            + len(stack.get("travis_files", []))
            + len(stack.get("drone_files", []))
        )

    # Fallback to counting from findings if detected_stack is empty
    if files_analyzed == 0:
        files_analyzed = len({f.file_path for f in findings if f.file_path})

    # Compute scanners_used and total_rules_executed
    scanner_execs = scan.scanner_executions or []
    scanners_used = len([
        se for se in scanner_execs
        if se.status in ("COMPLETED", "COMPLETED_WITH_FINDINGS", "COMPLETED_NO_FINDINGS")
    ])
    total_rules_executed = sum(se.rules_executed or 0 for se in scanner_execs)

    # Derive repository name from URL
    repo_parts = scan.repository_url.rstrip("/").split("/")
    repository_name = "/".join(repo_parts[-2:]) if len(repo_parts) >= 2 else repo_parts[-1]

    # Compute directories_scanned from findings
    directories_scanned = len({
        "/".join(f.file_path.split("/")[:-1])
        for f in findings if f.file_path and "/" in f.file_path
    })

    # Derive repository_size from repository relationship (if available)
    repository_size = None
    if scan.repository and hasattr(scan.repository, "size") and scan.repository.size:
        size_kb = scan.repository.size
        if size_kb >= 1048576:
            repository_size = f"{size_kb / 1048576:.1f} GB"
        elif size_kb >= 1024:
            repository_size = f"{size_kb / 1024:.1f} MB"
        else:
            repository_size = f"{size_kb} KB"

    # Build per-technology file counts from detected_stack + findings.
    # Every file is assigned to its canonical technology (each file belongs
    # to exactly one card) and findings are counted the same way, so the sum
    # of findings across all cards equals the total findings on the page.
    technology_details = []
    if scan.detected_stack:
        stack = scan.detected_stack
        tech_file_map = {
            "docker": stack.get("docker_files", []),
            "terraform": stack.get("terraform_files", []),
            "kubernetes": stack.get("kubernetes_files", []),
            "github_actions": stack.get("github_actions_files", []),
            "gitlab_ci": stack.get("gitlab_ci_files", []),
            "jenkins": stack.get("jenkins_files", []),
            "helm": stack.get("helm_files", []),
            "ansible": stack.get("ansible_files", []),
            "circleci": stack.get("circleci_files", []),
            "azure_devops": stack.get("azure_devops_files", []),
            "docker_compose": stack.get("docker_compose_files", []),
        }

        # Canonical per-file ownership across all detected stack files. The
        # raw detected_stack lists overlap (a Helm chart under a kubernetes/
        # directory appears in both), so ownership is re-derived here.
        canonical_file_counts: dict[str, int] = {}
        for files in tech_file_map.values():
            for fp in files:
                tech = classify_technology(fp)
                canonical_file_counts[tech] = canonical_file_counts.get(tech, 0) + 1

        # Technologies with detected files are reportable even when they
        # produced no findings (e.g. Helm charts in a clean repo), keeping
        # detected_technologies aligned with the coverage cards below.
        for tech, files in tech_file_map.items():
            if files and tech not in detected_technologies:
                detected_technologies.append(tech)

        # Report an entry for every detected technology so the frontend always
        # partitions findings by the canonical `technology` field (never by
        # fuzzy substring matching that could double-count a finding).
        techs_to_report = set(detected_technologies) | set(tech_file_map.keys())
        for tech in sorted(techs_to_report):
            tech_findings = [f for f in findings if _finding_matches_tech(f, tech)]
            tech_sev: dict[str, int] = {bucket: 0 for bucket in SEVERITY_BUCKETS}
            for tf in tech_findings:
                tech_sev[_severity_key(tf)] = tech_sev.get(_severity_key(tf), 0) + 1
            tech_files_count = canonical_file_counts.get(tech, 0)
            technology_details.append({
                "technology": tech,
                "files_count": tech_files_count,
                "findings_count": len(tech_findings),
                "total_findings": len(tech_findings),
                "severity_counts": tech_sev,
                "status": "DETECTED"
                if tech_files_count
                else ("HAS_FINDINGS" if tech_findings else "CLEAN"),
            })

    # Build risk_distribution from the normalized severity counts (just
    # counts, no duplication with technology_details).
    risk_distribution = {bucket: severity_counts.get(bucket, 0) for bucket in SEVERITY_BUCKETS}

    # Build top_files (files sorted by findings count, deduplicated)
    file_findings_map: dict[str, dict] = {}
    for f in findings:
        fp = f.file_path or ""
        if not fp:
            continue
        if fp not in file_findings_map:
            file_findings_map[fp] = {"file_path": fp, "findings_count": 0, "severities": {}}
        file_findings_map[fp]["findings_count"] += 1
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        file_findings_map[fp]["severities"][sev] = file_findings_map[fp]["severities"].get(sev, 0) + 1
    top_files = sorted(file_findings_map.values(), key=lambda x: x["findings_count"], reverse=True)[:15]

    return {
        "scan_id": str(scan.id),
        "id": str(scan.id),
        "repository_url": scan.repository_url,
        "repository_name": repository_name,
        "branch": scan.branch,
        "commit_hash": scan.commit_hash,
        "status": "completed",
        "ai_status": scan.ai_status or "completed",
        "overall_score": scan.overall_score,
        "security_score": scan.security_score,
        "scalability_score": scan.scalability_score,
        "reliability_score": scan.reliability_score,
        "cost_score": scan.cost_score,
        "observability_score": scan.observability_score,
        "findings_count": len(findings),
        "severity_counts": severity_counts,
        "risk_distribution": risk_distribution,
        "files_analyzed": files_analyzed,
        "directories_scanned": directories_scanned,
        "repository_size": repository_size,
        "detected_technologies": detected_technologies,
        "technology_details": technology_details,
        "top_files": top_files,
        "scanners_used": scanners_used,
        "rules_executed": total_rules_executed,
        "scanner_executions": [
            {
                "scanner_name": se.scanner_name,
                "scanner_id": se.scanner_id,
                "version": se.version,
                "status": se.status,
                "applicable": se.applicable,
                "enabled": se.enabled,
                "execution_start": se.execution_start.isoformat() if se.execution_start else None,
                "execution_end": se.execution_end.isoformat() if se.execution_end else None,
                "duration_ms": se.duration_ms,
                "files_scanned": se.files_scanned,
                "rules_executed": se.rules_executed,
                "findings_count": se.findings_count,
                "skipped_reason": se.skipped_reason,
                "error_message": se.error_message,
            }
            for se in (scan.scanner_executions or [])
        ],
        "findings": [
            {
                "id": str(f.id),
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "category": f.category.value if hasattr(f.category, "value") else str(f.category),
                "description": f.description,
                "recommendation": f.recommendation,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "ai_explanation": f.ai_explanation,
                "summary": f.summary,
                "risk": f.risk,
                "impact": f.impact,
                "fix_code": f.fix_code,
                "fix_example": f.fix_example,
                "full_example": f.full_example,
                "best_practices": json.loads(f.best_practices)
                if isinstance(f.best_practices, str)
                else (f.best_practices or []),
                "confidence_score": f.confidence_score or f.confidence or 0.8,
                "confidence": f.confidence
                or f.confidence_score
                or 0.8,
                "documentation_url": f.documentation_url,
                "ai_generated": bool(f.ai_generated),
                "scanner_name": f.scanner_name,
                "scanner_rule_id": f.scanner_rule_id,
                "package": f.package,
                "installed_version": f.installed_version,
                "fixed_version": f.fixed_version,
                "cve": f.cve,
                "cwe": f.cwe,
                "references": json.loads(f.references)
                if isinstance(f.references, str)
                else (f.references or []),
                "evidence": f.evidence,
                "technology": _detect_finding_technology(f),
            }
            for f in findings
        ],
        "ai_suggestions_count": len(suggestions),
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "analysis_duration_seconds": scan.analysis_duration_seconds,
    }


@router.get("/state/{scan_id}", response_model=dict[str, Any])
async def get_scan_state(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Get authoritative scan state for WebSocket reconnect synchronization.

    This endpoint is called by the frontend when:
    - WebSocket reconnects after disconnection
    - Page is refreshed during an active scan
    - Browser recovers from crash

    Returns the single source of truth from the database, including:
    - current_stage (granular stage enum)
    - status (terminal state)
    - progress percentage
    - Whether the scan is in a terminal state
    """
    parse_uuid(scan_id, "scan_id")
    from app.services.scan_state_service import build_scan_state_snapshot_async

    snapshot = await build_scan_state_snapshot_async(db, scan_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    # Access check
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    if scan.user_id and not current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authentication required")
    if scan.user_id and current_user and scan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    logger.info(
        f"[RECONNECT] scan={scan_id} status={snapshot.get('status')} "
        f"stage={snapshot.get('stage')} progress={snapshot.get('progress')} "
        f"is_terminal={snapshot.get('is_terminal')}"
    )
    return snapshot
