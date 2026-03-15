"""Scan routes - Updated to use Celery tasks."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
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

router = APIRouter(prefix="/scans", tags=["Scans"])


@router.get("", response_model=list)
async def list_scans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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

    # Filter by user if authenticated, otherwise show recent public scans
    if current_user:
        query = query.where(Scan.user_id == current_user.id)
    else:
        # For unauthenticated users, show scans without user_id (anonymous scans)
        query = query.where(Scan.user_id.is_(None))

    # Apply pagination
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    scans = result.scalars().all()

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


@router.post("", response_model=ScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    scan_data: ScanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scan for a repository using Celery."""
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

    # Start Celery task
    task = scan_repository_task.delay(
        scan_id=scan.id,
        repository_url=scan.repository_url,
        branch=scan.branch,
        commit_hash=scan.commit_hash,
        include_ai_explanations=True,
    )

    # Update scan with Celery task ID
    scan.celery_task_id = task.id
    scan.status = ScanStatus.QUEUED
    await db.commit()

    return scan


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
        scan_id=scan.id,
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


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: str,  # UUID as string
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific scan with findings."""
    from uuid import UUID
    try:
        scan_uuid = UUID(scan_id)
    except ValueError:
        raise ScanNotFoundException(scan_id)

    query = select(Scan).where(Scan.id == scan_uuid)

    # If authenticated, filter by user
    if current_user:
        query = query.where(Scan.user_id == current_user.id)

    result = await db.execute(query)
    scan = result.scalar_one_or_none()

    if not scan:
        raise ScanNotFoundException(scan_id)

    return scan


@router.get("/{scan_id}/progress", response_model=ScanProgressResponse)
async def get_scan_progress(
    scan_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get scan progress."""
    query = select(Scan).where(Scan.id == scan_id)

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
        except Exception:
            pass  # Celery task status unavailable

    return ScanProgressResponse(
        id=scan.id,
        status=scan.status,
        progress=progress,
        status_message=status_message,
        error_message=scan.error_message,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
    )


@router.post("/{scan_id}/cancel", response_model=ScanCancelResponse)
async def cancel_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running scan."""
    result = await db.execute(
        select(Scan).where(
            Scan.id == scan_id,
            Scan.user_id == current_user.id,
        )
    )
    scan = result.scalar_one_or_none()

    if not scan:
        raise ScanNotFoundException(scan_id)

    if scan.status not in [ScanStatus.PENDING, ScanStatus.PROCESSING, ScanStatus.QUEUED]:
        return ScanCancelResponse(
            id=scan.id,
            status="already_completed",
            message=f"Scan is already {scan.status.value}",
        )

    # Cancel Celery task
    if scan.celery_task_id:
        cancel_scan_task.delay(scan_id)

    # Update database status
    scan.status = ScanStatus.CANCELLED
    scan.error_message = "Scan cancelled by user"
    await db.commit()

    return ScanCancelResponse(
        id=scan.id,
        status="cancelled",
        message="Scan cancelled successfully",
    )


@router.get("/{scan_id}/findings", response_model=list)
async def get_scan_findings(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get findings for a scan - no authentication required."""
    # Verify scan exists
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise ScanNotFoundException(scan_id)

    # Get all findings for this scan
    query = select(Finding).where(Finding.scan_id == scan_id)
    result = await db.execute(query)
    findings = result.scalars().all()

    return findings


# Import selectinload for get_scan
