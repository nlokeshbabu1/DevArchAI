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
from app.models.kubernetes import KubernetesConnection
from app.models.user import User

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class IntegrationStatusResponse(BaseModel):
    github: bool
    gitlab: bool
    aws: bool
    azure: bool
    bitbucket: bool
    kubernetes: bool
    eks: bool


@router.get("/status", response_model=IntegrationStatusResponse)
async def get_integration_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IntegrationStatusResponse:
    """Return the connection status of each integration provider.

    Status is derived from persisted user-scoped records so an integration can
    be connected independently of the user's application login method.
    """
    # GitHub: an OAuth identity attached to the user OR an app installation.
    github_connected = bool(
        user.github_id or user.github_access_token or user.github_access_token_encrypted
    )
    if not github_connected:
        gh_result = await db.execute(
            select(GitHubInstallation).where(GitHubInstallation.user_id == user.id)
        )
        github_connected = gh_result.scalars().first() is not None

    # GitLab: an OAuth identity attached to the user.
    gitlab_connected = bool(
        user.gitlab_id or user.gitlab_access_token or user.gitlab_access_token_encrypted
    )

    aws_connected = False
    azure_connected = False

    cloud_result = await db.execute(
        select(CloudConnection).where(CloudConnection.user_id == user.id)
    )
    for conn in cloud_result.scalars().all():
        if conn.status == "active":
            if conn.provider == "aws":
                aws_connected = True
            elif conn.provider == "azure":
                azure_connected = True

    # Kubernetes: an independent kubeconfig-based connection (includes EKS clusters).
    k8s_result = await db.execute(
        select(KubernetesConnection).where(KubernetesConnection.user_id == user.id)
    )
    k8s_connections = k8s_result.scalars().all()
    kubernetes_connected = any(c.is_active for c in k8s_connections)
    eks_connected = any(c.is_active and c.kind == "eks" for c in k8s_connections)

    return IntegrationStatusResponse(
        github=github_connected,
        gitlab=gitlab_connected,
        aws=aws_connected,
        azure=azure_connected,
        bitbucket=False,
        kubernetes=kubernetes_connected,
        eks=eks_connected,
    )
