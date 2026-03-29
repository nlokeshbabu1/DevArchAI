"""Scan routes - Fixed UUID types and removed duplicates."""

import structlog
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ScanNotFoundException
from app.core.security import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.finding import Finding
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.schemas.scan import (
    ScanCancelResponse,
    ScanCreate,
    ScanProgressResponse,
    ScanResponse,
)
from app.workers.tasks.scan_repository import cancel_scan_task, scan_repository_task

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/scans", tags=["Scans"])


def _parse_scan_id(scan_id: str) -> UUID:
    """Parse scan ID string to UUID."""
    try:
        return UUID(scan_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scan ID format: {scan_id}. Expected UUID."
        )


@router.get("", response_model=list)
async def list_scans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status_filter"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List all scans with pagination."""
    offset = (page - 1) * page_size

    # Build query
    query = select(Scan).order_by(Scan.created_at.desc())

    # Filter by status if provided
    if status_filter:
        query = query.where(Scan.status == status_filter)

    # Filter by user if authenticated
    if current_user:
        # Show ALL scans for authenticated user (including anonymous scans they made)
        query = query.where(
            (Scan.user_id == current_user.id) | (Scan.user_id.is_(None))
        )
        logger.info(f"Listing scans for user {current_user.id}")
    else:
        # For unauthenticated users, show only anonymous scans (last 7 days)
        from datetime import datetime, timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        query = query.where(
            (Scan.user_id.is_(None)) & (Scan.created_at >= seven_days_ago)
        )
        logger.info("Listing anonymous scans for guest user")

    # Apply pagination
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    scans = result.scalars().all()

    logger.info(f"Returning {len(scans)} scans")

    # Convert to list of dicts for JSON serialization
    return [
        {
            "id": str(scan.id),
            "user_id": str(scan.user_id) if scan.user_id else None,
            "repository_id": str(scan.repository_id) if scan.repository_id else None,
            "repository_url": scan.repository_url,
            "branch": scan.branch,
            "commit_hash": scan.commit_hash,
            "status": scan.status.value,
            "progress": scan.progress,
            "error_message": scan.error_message,
            "overall_score": scan.overall_score,
            "security_score": scan.security_score,
            "scalability_score": scan.scalability_score,
            "reliability_score": scan.reliability_score,
            "cost_score": scan.cost_score,
            "observability_score": scan.observability_score,
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "analysis_duration_seconds": scan.analysis_duration_seconds,
            "created_at": scan.created_at.isoformat(),
            "updated_at": scan.updated_at.isoformat(),
        }
        for scan in scans
    ]


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific scan with findings."""
    scan_uuid = _parse_scan_id(scan_id)

    query = select(Scan).where(Scan.id == scan_uuid)

    # If authenticated, filter by user - but also allow scans without user_id (guest scans)
    if current_user:
        query = query.where(
            (Scan.user_id == current_user.id) | (Scan.user_id == None)
        )

    result = await db.execute(query)
    scan = result.scalar_one_or_none()

    if not scan:
        raise ScanNotFoundException(scan_id)

    # Get findings count
    from app.models.finding import Finding
    logger.error(f"DEBUG: Getting scan {scan_id}")  # DEBUG LINE
    findings_count = await db.execute(
        select(func.count()).select_from(Finding).where(Finding.scan_id == scan_id)
    )
    findings_count = findings_count.scalar() or 0
    logger.error(f"DEBUG: findings_count={findings_count}")  # DEBUG LINE
    
    # Calculate files analyzed from detected_stack
    files_analyzed = 0
    if scan.detected_stack:
        stack = scan.detected_stack
        files_analyzed = (
            len(stack.get('docker_files', [])) +
            len(stack.get('terraform_files', [])) +
            len(stack.get('kubernetes_files', [])) +
            len(stack.get('github_actions_files', [])) +
            len(stack.get('gitlab_ci_files', [])) +
            len(stack.get('jenkins_files', [])) +
            len(stack.get('docker_compose_files', [])) +
            len(stack.get('helm_files', []))
        )
    
    # Convert to dict with additional fields
    # Build clean detected technologies list
    detected_tech_names = []
    if scan.detected_stack:
        stack = scan.detected_stack
        if stack.get('has_docker') or stack.get('docker_files'):
            detected_tech_names.append('Docker')
        if stack.get('has_terraform') or stack.get('terraform_files'):
            detected_tech_names.append('Terraform')
        if stack.get('has_kubernetes') or stack.get('kubernetes_files'):
            detected_tech_names.append('Kubernetes')
        if stack.get('has_helm') or stack.get('helm_files'):
            detected_tech_names.append('Helm')
        if stack.get('has_github_actions') or stack.get('github_actions_files'):
            detected_tech_names.append('GitHub Actions')
        if stack.get('has_gitlab_ci') or stack.get('gitlab_ci_files'):
            detected_tech_names.append('GitLab CI')
        if stack.get('has_jenkins') or stack.get('jenkins_files'):
            detected_tech_names.append('Jenkins')
        if stack.get('has_docker_compose') or stack.get('docker_compose_files'):
            detected_tech_names.append('Docker Compose')
        if stack.get('has_ansible') or stack.get('ansible_files'):
            detected_tech_names.append('Ansible')
        if stack.get('has_circleci') or stack.get('circleci_files'):
            detected_tech_names.append('CircleCI')
        if stack.get('has_azure_devops') or stack.get('azure_devops_files'):
            detected_tech_names.append('Azure DevOps')
        if stack.get('has_travis') or stack.get('travis_files'):
            detected_tech_names.append('Travis CI')
        if stack.get('has_drone') or stack.get('drone_files'):
            detected_tech_names.append('Drone CI')
    
    return {
        "id": str(scan.id),
        "user_id": str(scan.user_id) if scan.user_id else None,
        "repository_id": str(scan.repository_id) if scan.repository_id else None,
        "repository_url": scan.repository_url,
        "branch": scan.branch,
        "commit_hash": scan.commit_hash,
        "status": scan.status.value,
        "progress": scan.progress,
        "error_message": scan.error_message,
        "overall_score": scan.overall_score,
        "security_score": scan.security_score,
        "scalability_score": scan.scalability_score,
        "reliability_score": scan.reliability_score,
        "cost_score": scan.cost_score,
        "observability_score": scan.observability_score,
        "detected_stack": scan.detected_stack,
        "detected_technologies": detected_tech_names,
        "files_analyzed": files_analyzed,
        "findings_count": findings_count,
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "analysis_duration_seconds": scan.analysis_duration_seconds,
        "created_at": scan.created_at.isoformat(),
        "updated_at": scan.updated_at.isoformat(),
    }


@router.get("/{scan_id}/progress", response_model=ScanProgressResponse)
async def get_scan_progress(
    scan_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get scan progress."""
    scan_uuid = _parse_scan_id(scan_id)
    
    query = select(Scan).where(Scan.id == scan_uuid)

    if current_user:
        query = query.where(Scan.user_id == current_user.id)

    result = await db.execute(query)
    scan = result.scalar_one_or_none()

    if not scan:
        raise ScanNotFoundException(scan_id)

    # Get Celery task status if available
    progress = scan.progress
    status_message = scan.status_message or scan.status.value

    if scan.celery_task_id:
        try:
            from celery.result import AsyncResult
            task_result = AsyncResult(scan.celery_task_id)
            if task_result.state == "PROGRESS":
                info = task_result.info
                if isinstance(info, dict):
                    progress = info.get("progress", progress)
                    status_message = info.get("status", status_message)
        except Exception as e:
            logger.warning(f"Celery task status unavailable: {e}")

    return ScanProgressResponse(
        id=str(scan.id),
        status=scan.status.value,
        progress=progress,
        status_message=status_message,
        error_message=scan.error_message,
        created_at=scan.created_at.isoformat(),
        completed_at=scan.completed_at.isoformat() if scan.completed_at else None,
    )


@router.post("/{scan_id}/cancel", response_model=ScanCancelResponse)
async def cancel_scan(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running scan."""
    scan_uuid = _parse_scan_id(scan_id)
    
    result = await db.execute(
        select(Scan).where(
            Scan.id == scan_uuid,
            Scan.user_id == current_user.id,
        )
    )
    scan = result.scalar_one_or_none()

    if not scan:
        raise ScanNotFoundException(scan_id)

    if scan.status not in [ScanStatus.PENDING, ScanStatus.PROCESSING, ScanStatus.QUEUED]:
        return ScanCancelResponse(
            id=str(scan.id),
            status="already_completed",
            message=f"Scan is already {scan.status.value}",
        )

    # Cancel Celery task
    if scan.celery_task_id:
        try:
            cancel_scan_task.delay(str(scan.id))
        except Exception as e:
            logger.warning(f"Failed to cancel Celery task: {e}")

    # Update database status
    scan.status = ScanStatus.CANCELLED
    scan.error_message = "Scan cancelled by user"
    await db.commit()

    return ScanCancelResponse(
        id=str(scan.id),
        status="cancelled",
        message="Scan cancelled successfully",
    )


@router.get("/{scan_id}/findings", response_model=list)
async def get_scan_findings(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get all findings for a specific scan."""
    scan_uuid = _parse_scan_id(scan_id)
    
    # Verify scan exists
    result = await db.execute(select(Scan).where(Scan.id == scan_uuid))
    scan = result.scalar_one_or_none()

    if not scan:
        raise ScanNotFoundException(scan_id)

    # Check access - allow if scan has no user_id (public) or user owns the scan
    if scan.user_id:
        if not current_user or scan.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't have permission to view this scan's findings"
            )

    # Get findings
    findings_result = await db.execute(
        select(Finding)
        .where(Finding.scan_id == scan_id)
        .order_by(Finding.severity, Finding.created_at)
    )
    findings = findings_result.scalars().all()

    # Convert to dicts
    import json
    return [
        {
            "id": str(finding.id),
            "scan_id": str(finding.scan_id),
            "rule_id": finding.rule_id,
            "rule_name": finding.rule_name,
            "severity": finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
            "category": finding.category.value if hasattr(finding.category, 'value') else str(finding.category),
            "description": finding.description,
            "recommendation": finding.recommendation,
            "file_path": finding.file_path,
            "line_number": finding.line_number,
            "ai_explanation": finding.ai_explanation,
            "ai_generated": finding.ai_generated,
            "summary": finding.summary,
            "risk": finding.risk,
            "impact": finding.impact,
            "fix_code": finding.fix_code,
            "fix_example": finding.fix_example,
            "full_example": finding.full_example,
            "best_practices": json.loads(finding.best_practices) if finding.best_practices else [],
            "confidence_score": finding.confidence_score,
            "documentation_url": finding.documentation_url,
            "created_at": finding.created_at.isoformat(),
        }
        for finding in findings
    ]


@router.post("", response_model=ScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    scan_data: ScanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scan for a repository. Uses synchronous scanning for immediate results."""
    from app.db.session import get_sync_session_factory
    from app.workers.tasks.scan_repository import SyncScanService
    
    # Check if repository exists, create if not
    result = await db.execute(
        select(Repository).where(
            Repository.user_id == current_user.id,
            Repository.url == scan_data.repository_url,
        )
    )
    repository = result.scalar_one_or_none()

    if not repository:
        # Create repository
        name = scan_data.repository_url.split("/")[-1].replace(".git", "")
        repository = Repository(
            user_id=current_user.id,
            name=name,
            url=scan_data.repository_url,
            default_branch=scan_data.branch or "main",
        )
        db.add(repository)
        await db.flush()
        await db.refresh(repository)

    # Create scan
    scan = Scan(
        user_id=current_user.id,
        repository_id=repository.id,
        repository_url=scan_data.repository_url,
        branch=scan_data.branch or "main",
        commit_hash=scan_data.commit_hash,
        status=ScanStatus.PENDING,
    )

    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Run scan synchronously for immediate results
    # This avoids dependency on Celery workers
    try:
        SessionLocal = get_sync_session_factory()
        sync_db = SessionLocal()
        try:
            scan_service = SyncScanService(
                db=sync_db,
                include_ai_explanations=True,
            )

            # Get fresh scan from sync db
            from app.models.scan import Scan as SyncScan
            sync_scan = sync_db.get(SyncScan, scan.id)

            if sync_scan:
                # Update status to processing
                sync_scan.status = ScanStatus.PROCESSING
                sync_db.commit()
                
                # Execute scan synchronously with timeout
                import signal
                from app.core.exceptions import ScanTimeoutError
                
                def timeout_handler(signum, frame):
                    raise ScanTimeoutError("Scan exceeded maximum execution time")
                
                # Set timeout (5 minutes)
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(300)  # 5 minutes
                
                try:
                    updated_scan = scan_service.execute_scan(sync_scan)
                    signal.alarm(0)  # Cancel alarm
                    
                    # Copy results back to async session
                    scan.status = updated_scan.status
                    scan.progress = updated_scan.progress
                    scan.overall_score = updated_scan.overall_score
                    scan.security_score = updated_scan.security_score
                    scan.completed_at = updated_scan.completed_at
                    await db.commit()

                    logger.info(f"Sync scan completed: {scan.status.value}, score: {scan.overall_score}")
                except ScanTimeoutError as e:
                    logger.error(f"Scan timed out: {scan.id}")
                    scan.status = ScanStatus.FAILED
                    scan.error_message = str(e)
                    await db.commit()
                    raise
                finally:
                    signal.signal(signal.SIGALRM, old_handler)  # Restore handler
        finally:
            sync_db.close()
    except Exception as scan_error:
        logger.exception(f"Sync scan failed: {scan_error}")
        scan.status = ScanStatus.FAILED
        scan.error_message = str(scan_error)
        await db.commit()
        # Don't re-raise - return failed scan so frontend can show error

    # Convert to dict to avoid SQLAlchemy serialization and UUID issues
    return {
        "id": str(scan.id),
        "user_id": str(scan.user_id) if scan.user_id else None,
        "repository_id": str(scan.repository_id) if scan.repository_id else None,
        "repository_url": scan.repository_url,
        "branch": scan.branch,
        "commit_hash": scan.commit_hash,
        "status": scan.status.value,
        "progress": scan.progress,
        "error_message": scan.error_message,
        "overall_score": scan.overall_score,
        "security_score": scan.security_score,
        "scalability_score": scan.scalability_score,
        "reliability_score": scan.reliability_score,
        "cost_score": scan.cost_score,
        "observability_score": scan.observability_score,
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "analysis_duration_seconds": scan.analysis_duration_seconds,
        "created_at": scan.created_at.isoformat(),
        "updated_at": scan.updated_at.isoformat(),
    }


@router.post("/analyze", response_model=ScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_repository(
    scan_data: ScanCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Backward-compatible endpoint: Start analysis of a GitHub repository.
    Uses anonymous user for unauthenticated requests.
    """
    # Get or create anonymous user
    result = await db.execute(select(User).where(User.username == "anonymous"))
    anonymous_user = result.scalar_one_or_none()
    user_id = anonymous_user.id if anonymous_user else None

    # Create repository
    name = scan_data.repository_url.split("/")[-1].replace(".git", "")
    repository = Repository(
        user_id=user_id,
        name=name,
        url=scan_data.repository_url,
        default_branch=scan_data.branch or "main",
    )
    db.add(repository)
    await db.flush()
    await db.refresh(repository)

    # Create scan
    scan = Scan(
        user_id=user_id,
        repository_id=repository.id,
        repository_url=scan_data.repository_url,
        branch=scan_data.branch or "main",
        commit_hash=scan_data.commit_hash,
        status=ScanStatus.PENDING,
    )

    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Start Celery task
    task = scan_repository_task.delay(
        scan_id=str(scan.id),
        repository_url=scan.repository_url,
        branch=scan.branch,
        commit_hash=scan.commit_hash,
        include_ai_explanations=True,
    )

    scan.celery_task_id = task.id
    scan.status = ScanStatus.QUEUED
    await db.commit()
    await db.refresh(scan)

    # Convert to dict to avoid SQLAlchemy serialization issues
    return {
        "id": str(scan.id),
        "user_id": str(scan.user_id) if scan.user_id else None,
        "repository_id": str(scan.repository_id) if scan.repository_id else None,
        "repository_url": scan.repository_url,
        "branch": scan.branch,
        "commit_hash": scan.commit_hash,
        "status": scan.status.value,
        "progress": scan.progress,
        "error_message": scan.error_message,
        "overall_score": scan.overall_score,
        "security_score": scan.security_score,
        "scalability_score": scan.scalability_score,
        "reliability_score": scan.reliability_score,
        "cost_score": scan.cost_score,
        "observability_score": scan.observability_score,
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "analysis_duration_seconds": scan.analysis_duration_seconds,
        "created_at": scan.created_at.isoformat(),
        "updated_at": scan.updated_at.isoformat(),
    }
# reload trigger
