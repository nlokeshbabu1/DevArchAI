"""Repository routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.repository import Repository
from app.models.scan import Scan
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryResponse,
    RepositoryListResponse,
)
from app.schemas.common import MessageResponse
from app.core.security import get_current_user
from app.core.exceptions import RepositoryNotFoundException
from app.utils.repo_downloader import RepoDownloader

router = APIRouter(prefix="/repositories", tags=["Repositories"])


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
    """List all repositories for the current user."""
    offset = (page - 1) * page_size

    # Get repositories with scan count
    query = (
        select(
            Repository,
            func.count(Scan.id).label("scan_count"),
        )
        .outerjoin(Scan, Repository.id == Scan.repository_id)
        .where(Repository.user_id == current_user.id, Repository.is_active == True)
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
        Repository.is_active == True,
    )
    total = await db.scalar(count_query)

    repositories = []
    for repo, scan_count in rows:
        repo_dict = RepositoryResponse.model_validate(repo)
        repo_dict.scan_count = scan_count
        repositories.append(repo_dict)

    return RepositoryListResponse(
        repositories=repositories,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific repository."""
    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_id,
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
    repo_id: int,
    repo_data: RepositoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a repository."""
    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_id,
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
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a repository (soft delete)."""
    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_id,
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
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a new scan for the repository."""
    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_id,
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
        branch=repository.default_branch,
        status="pending",
    )

    db.add(scan)
    await db.commit()

    # Trigger background scan (in production, use Celery)
    from app.workers.scan_worker import execute_scan_background
    asyncio.create_task(execute_scan_background(scan.id))

    return MessageResponse(
        message=f"Scan triggered for repository {repository.name}",
        success=True,
    )


# Import asyncio for background task
import asyncio
