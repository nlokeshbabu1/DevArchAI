"""GitHub App installation management endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.pull_requests import _extract_repo_full_name
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.github_installation import GitHubInstallation
from app.models.user import User
from app.schemas.github_installation import (
    InstallationCreate,
    InstallationListResponse,
    InstallationResponse,
    InstallationValidateRequest,
    InstallationValidateResponse,
)
from app.services.github_app_service import GitHubAppService, GitHubAppServiceError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/github/installations", tags=["GitHub App Installations"])


@router.get("/", response_model=InstallationListResponse)
async def list_installations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all GitHub App installations for the current user.

    Returns all repositories where the GitHub App is installed.
    """
    logger.info("Listing user installations", user_id=str(current_user.id))

    result = await db.execute(
        select(GitHubInstallation)
        .where(GitHubInstallation.user_id == current_user.id)
        .order_by(GitHubInstallation.created_at.desc())
    )
    installations = result.scalars().all()

    return InstallationListResponse(
        installations=[
            InstallationResponse(
                id=str(inst.id),
                repo_full_name=inst.repo_full_name,
                installation_id=inst.installation_id,
                created_at=inst.created_at,
            )
            for inst in installations
        ],
        total=len(installations),
    )


@router.post("/", response_model=InstallationResponse, status_code=status.HTTP_201_CREATED)
async def create_installation(
    request: InstallationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a GitHub App installation for a repository.

    This endpoint is typically called after a user installs the GitHub App
    on a repository to register the installation in the system.

    Note: In production, this should be handled by the webhook automatically.
    This endpoint is provided for manual registration if needed.
    """
    repo_full_name = _extract_repo_full_name(request.repository_url)

    logger.info(
        "Creating installation registration",
        user_id=str(current_user.id),
        repo=repo_full_name,
        installation_id=request.installation_id,
    )

    # Check if installation already exists
    existing = await db.execute(
        select(GitHubInstallation).where(
            GitHubInstallation.user_id == current_user.id,
            GitHubInstallation.repo_full_name == repo_full_name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"GitHub App installation already registered for '{repo_full_name}'",
        )

    # Validate installation by getting token
    try:
        app_service = GitHubAppService()
        token_data = await app_service.get_installation_token(request.installation_id)

        if not token_data.get("token"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to validate GitHub App installation",
            )

        logger.info(
            "Installation validated successfully",
            installation_id=request.installation_id,
            permissions=token_data.get("permissions"),
        )
    except GitHubAppServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GitHub App installation: {exc.message}",
        ) from exc

    # Create installation record
    installation = GitHubInstallation(
        user_id=current_user.id,
        repo_full_name=repo_full_name,
        installation_id=request.installation_id,
    )
    db.add(installation)
    await db.commit()
    await db.refresh(installation)

    logger.info(
        "Installation registered",
        installation_id=installation.id,
        repo=repo_full_name,
    )

    return InstallationResponse(
        id=str(installation.id),
        repo_full_name=installation.repo_full_name,
        installation_id=installation.installation_id,
        created_at=installation.created_at,
    )


@router.delete("/{installation_id}")
async def delete_installation(
    installation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a GitHub App installation registration.

    This removes the installation from the system but does NOT uninstall
    the GitHub App from the repository (that must be done via GitHub).
    """
    from uuid import UUID

    try:
        installation_uuid = UUID(installation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid installation ID format",
        )

    result = await db.execute(
        select(GitHubInstallation).where(
            GitHubInstallation.id == installation_uuid,
            GitHubInstallation.user_id == current_user.id,
        )
    )
    installation = result.scalar_one_or_none()

    if not installation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installation not found or access denied",
        )

    logger.info(
        "Deleting installation registration",
        installation_id=str(installation.id),
        repo=installation.repo_full_name,
    )

    await db.delete(installation)
    await db.commit()

    return {
        "message": f"Installation for '{installation.repo_full_name}' removed successfully",
        "repo_full_name": installation.repo_full_name,
    }


@router.post("/validate", response_model=InstallationValidateResponse)
async def validate_installation(
    request: InstallationValidateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate a GitHub App installation has access to a repository.

    This endpoint:
    1. Gets an installation token
    2. Validates the token can access the specified repository
    3. Returns installation permissions and details
    """
    repo_full_name = _extract_repo_full_name(request.repository_url)
    owner, repo = repo_full_name.split("/")

    logger.info(
        "Validating installation",
        user_id=str(current_user.id),
        repo=repo_full_name,
        installation_id=request.installation_id,
    )

    try:
        app_service = GitHubAppService()
        validation_result = await app_service.validate_installation(
            installation_id=request.installation_id,
            owner=owner,
            repo=repo,
        )

        return InstallationValidateResponse(
            installation_id=validation_result["installation_id"],
            app_id=validation_result["app_id"],
            permissions=validation_result["permissions"],
            events=validation_result["events"],
            repository_selection=validation_result["repository_selection"],
            repo_full_name=repo_full_name,
        )

    except GitHubAppServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Installation validation failed: {exc.message}",
        ) from exc


@router.get("/app/installations")
async def list_app_installations(
    current_user: User = Depends(get_current_user),
):
    """
    List all GitHub App installations from GitHub's perspective.

    This fetches installations directly from GitHub API (not from our database).
    Useful for debugging and showing users all repositories where the app is installed.
    """
    if current_user.role.value not in ("admin", "enterprise"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can list app installations",
        )

    try:
        app_service = GitHubAppService()
        installations = await app_service.get_app_installations()

        return {
            "installations": [
                {
                    "id": inst["id"],
                    "account": inst.get("account", {}).get("login"),
                    "account_type": inst.get("account", {}).get("type"),
                    "repository_selection": inst.get("repository_selection"),
                    "permissions": inst.get("permissions", {}),
                }
                for inst in installations
            ],
            "total": len(installations),
        }

    except GitHubAppServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch installations: {exc.message}",
        ) from exc
