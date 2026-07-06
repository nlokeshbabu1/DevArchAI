"""Repository routes - Fixed UUID types."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.finding import Finding
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryResponse,
    RepositoryUpdate,
)
from app.utils.repo_downloader import RepoDownloader
from app.workers.tasks.scan_repository import scan_repository_task

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/repositories", tags=["Repositories"])


def _parse_repo_id(repo_id: str) -> UUID:
    """Parse repository ID string to UUID."""
    try:
        return UUID(repo_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository ID format: {repo_id}. Expected UUID."
        )


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repo_data: RepositoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new repository to track."""
    # Validate repository URL
    downloader = RepoDownloader()
    is_valid = await downloader.validate_repository(repo_data.url)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inaccessible repository",
        )

    # Parse repository name from URL if not provided
    name = repo_data.name
    if not name:
        # Extract from URL
        parts = repo_data.url.rstrip("/").split("/")
        if len(parts) >= 2:
            name = "/".join(parts[-2:]).replace(".git", "")

    # Check if repository already exists for user
    result = await db.execute(
        select(Repository).where(
            Repository.user_id == current_user.id,
            Repository.url == repo_data.url,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.is_active:
            return existing
        # Reactivate
        existing.is_active = True
        await db.commit()
        await db.refresh(existing)
        return existing

    # Create repository
    repository = Repository(
        user_id=current_user.id,
        name=name,
        url=repo_data.url,
        default_branch="main",
    )

    db.add(repository)
    await db.commit()
    await db.refresh(repository)

    return repository


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all repositories for the current user with enhanced data."""
    offset = (page - 1) * page_size

    # Get repositories with scan count
    query = (
        select(
            Repository,
            func.count(Scan.id).label("scan_count"),
        )
        .outerjoin(Scan, Repository.id == Scan.repository_id)
        .where(Repository.user_id == current_user.id, Repository.is_active.is_(True))
        .group_by(Repository.id)
        .order_by(Repository.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    rows = result.all()

    # Get total count
    count_query = select(func.count(Repository.id)).where(
        Repository.user_id == current_user.id,
        Repository.is_active.is_(True),
    )
    total = await db.scalar(count_query)

    repositories = []
    for repo, scan_count in rows:
        repo_dict = RepositoryResponse.model_validate(repo)
        repo_dict.scan_count = scan_count

        # Get latest scan for status and score
        latest_scan_query = (
            select(Scan)
            .where(Scan.repository_id == repo.id)
            .order_by(Scan.created_at.desc())
            .limit(1)
        )
        latest_scan_result = await db.execute(latest_scan_query)
        latest_scan = latest_scan_result.scalar_one_or_none()

        if latest_scan:
            repo_dict.last_scan_at = latest_scan.created_at
            repo_dict.scan_status = latest_scan.status.value
            repo_dict.overall_score = latest_scan.overall_score

        # Get tech stack from latest scan's findings
        if latest_scan:
            findings_query = (
                select(func.distinct(Finding.rule_id), Finding.category)
                .where(Finding.scan_id == latest_scan.id)
            )
            findings_result = await db.execute(findings_query)
            findings = findings_result.all()

            # Infer tech stack from rule IDs and file paths
            tech_stack = set()
            for rule_id, category in findings:
                if 'DOCKER' in rule_id.upper() or 'DKR' in rule_id.upper():
                    tech_stack.add('Docker')
                elif 'K8S' in rule_id.upper() or 'KUBERNETES' in rule_id.upper():
                    tech_stack.add('Kubernetes')
                elif 'TF' in rule_id.upper() or 'TERRAFORM' in rule_id.upper():
                    tech_stack.add('Terraform')
                elif 'CI' in rule_id.upper() or 'GITHUB' in rule_id.upper():
                    tech_stack.add('CI/CD')
                elif 'HELM' in rule_id.upper():
                    tech_stack.add('Helm')
                elif 'ANSIBLE' in rule_id.upper():
                    tech_stack.add('Ansible')

            repo_dict.tech_stack = list(tech_stack)

        # Get issue counts from latest scan's findings
        if latest_scan:
            severity_query = (
                select(Finding.severity, func.count(Finding.id))
                .where(Finding.scan_id == latest_scan.id)
                .group_by(Finding.severity)
            )
            severity_result = await db.execute(severity_query)
            severity_counts = {sev.value: count for sev, count in severity_result.all()}

            repo_dict.issues = {
                'critical': severity_counts.get('critical', 0),
                'high': severity_counts.get('high', 0),
                'medium': severity_counts.get('medium', 0),
                'low': severity_counts.get('low', 0),
            }

        repositories.append(repo_dict)

    return RepositoryListResponse(
        repositories=repositories,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific repository."""
    repo_uuid = _parse_repo_id(repo_id)

    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_uuid,
            Repository.user_id == current_user.id,
            Repository.is_active == True,
        )
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    return repository


@router.put("/{repo_id}", response_model=RepositoryResponse)
async def update_repository(
    repo_id: str,
    repo_data: RepositoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a repository."""
    repo_uuid = _parse_repo_id(repo_id)

    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_uuid,
            Repository.user_id == current_user.id,
        )
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    # Update fields
    if repo_data.name is not None:
        repository.name = repo_data.name
    if repo_data.description is not None:
        repository.description = repo_data.description
    if repo_data.is_active is not None:
        repository.is_active = repo_data.is_active

    await db.commit()
    await db.refresh(repository)

    return repository


@router.delete("/{repo_id}", response_model=MessageResponse)
async def delete_repository(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a repository (soft delete)."""
    repo_uuid = _parse_repo_id(repo_id)

    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_uuid,
            Repository.user_id == current_user.id,
        )
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    # Soft delete
    repository.is_active = False
    await db.commit()

    return MessageResponse(message="Repository deleted successfully")


@router.post("/{repo_id}/scan", response_model=MessageResponse)
async def trigger_repository_scan(
    repo_id: str,
    branch: str = Query(default="main"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a new scan for the repository."""
    repo_uuid = _parse_repo_id(repo_id)

    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_uuid,
            Repository.user_id == current_user.id,
            Repository.is_active == True,
        )
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    # Create scan
    scan = Scan(
        user_id=current_user.id,
        repository_id=repository.id,
        repository_url=repository.url,
        branch=branch,
        status=ScanStatus.PENDING,
    )

    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Start Celery task
    try:
        task = scan_repository_task.delay(
            scan_id=str(scan.id),
            repository_url=repository.url,
            branch=branch,
            include_ai_explanations=True,
        )
        scan.celery_task_id = task.id
        scan.status = ScanStatus.QUEUED
        await db.commit()

        logger.info(f"Scan triggered for repository {repository.name}", scan_id=str(scan.id))
    except Exception as e:
        logger.exception(f"Failed to trigger scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger scan: {str(e)}",
        )

    return MessageResponse(
        message=f"Scan triggered for repository {repository.name}",
        success=True,
    )
