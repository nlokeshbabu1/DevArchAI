"""Integration status routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.cloud import CloudConnection
from app.models.github_installation import GitHubInstallation
from app.models.user import User

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class IntegrationStatusResponse(BaseModel):
    github: bool
    gitlab: bool
    aws: bool
    azure: bool
    bitbucket: bool


@router.get("/status", response_model=IntegrationStatusResponse)
async def get_integration_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IntegrationStatusResponse:
    """Return the connection status of each integration provider."""
    github_connected = False
    gitlab_connected = False
    aws_connected = False
    azure_connected = False

    # Check GitHub installations
    gh_result = await db.execute(
        select(GitHubInstallation).where(GitHubInstallation.user_id == user.id)
    )
    if gh_result.scalar_one_or_none() is not None:
        github_connected = True

    # Check cloud connections
    cloud_result = await db.execute(
        select(CloudConnection).where(CloudConnection.user_id == user.id)
    )
    for conn in cloud_result.scalars().all():
        if conn.status == "active":
            if conn.provider == "aws":
                aws_connected = True
            elif conn.provider == "azure":
                azure_connected = True

    return IntegrationStatusResponse(
        github=github_connected,
        gitlab=gitlab_connected,
        aws=aws_connected,
        azure=azure_connected,
        bitbucket=False,
    )
