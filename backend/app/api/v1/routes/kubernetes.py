"""Kubernetes integration routes.

Supports:
- Generic kubeconfig-based connections (DEV/UAT).
- EKS cluster discovery and connection reusing an existing AWS connection.

Credentials (kubeconfig) are encrypted at rest and never returned to the client.
"""

from __future__ import annotations

import base64
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import get_encryption_service
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.cloud import CloudConnection
from app.models.kubernetes import KubernetesConnection
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/kubernetes", tags=["Kubernetes"])


class KubernetesConnectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    kubeconfig: str = Field(..., min_length=1, description="Base64-encoded kubeconfig YAML")
    context_name: str | None = Field(default=None, max_length=200)


class EksDiscoveryRequest(BaseModel):
    region: str = Field(default="us-east-1", max_length=64)


class EksConnectRequest(BaseModel):
    cluster_name: str = Field(..., min_length=1, max_length=200)
    region: str = Field(..., min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=200)


class KubernetesInfo(BaseModel):
    id: str
    name: str
    provider: str
    kind: str
    context_name: str | None = None
    cluster_endpoint: str | None = None
    aws_account_id: str | None = None
    aws_region: str | None = None
    eks_cluster_name: str | None = None
    status: str
    is_active: bool
    created_at: str | None = None


def _to_info(c: KubernetesConnection) -> KubernetesInfo:
    return KubernetesInfo(
        id=str(c.id),
        name=c.name,
        provider=c.provider,
        kind=c.kind,
        context_name=c.context_name,
        cluster_endpoint=c.cluster_endpoint,
        aws_account_id=c.aws_account_id,
        aws_region=c.aws_region,
        eks_cluster_name=c.eks_cluster_name,
        status=c.status,
        is_active=c.is_active,
        created_at=c.created_at.isoformat() if c.created_at else None,
    )


async def _owned_connection(connection_id: str, user: User, db: AsyncSession) -> KubernetesConnection:
    result = await db.execute(
        select(KubernetesConnection).where(
            KubernetesConnection.id == connection_id,
            KubernetesConnection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@router.post("/connect", response_model=KubernetesInfo)
async def connect_kubernetes(
    payload: KubernetesConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect a Kubernetes cluster from a kubeconfig."""
    try:
        kubeconfig_text = base64.b64decode(payload.kubeconfig).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 kubeconfig")

    encryption = get_encryption_service()

    # Basic validation: must contain clusters/contexts/users.
    if "clusters:" not in kubeconfig_text or "contexts:" not in kubeconfig_text:
        raise HTTPException(
            status_code=400,
            detail="Invalid kubeconfig: missing clusters or contexts",
        )

    conn = KubernetesConnection(
        user_id=user.id,
        name=payload.name,
        provider="kubernetes",
        kind="generic",
        kubeconfig_encrypted=encryption.encrypt(kubeconfig_text),
        context_name=payload.context_name,
        status="connected",
        is_active=True,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    logger.info("kubernetes_connected", user_id=str(user.id), connection_id=str(conn.id))

    return _to_info(conn)


@router.post("/test", response_model=dict[str, Any])
async def test_kubernetes(
    payload: KubernetesConnectRequest,
    user: User = Depends(get_current_user),
):
    """Validate a kubeconfig without persisting it."""
    try:
        kubeconfig_text = base64.b64decode(payload.kubeconfig).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 kubeconfig")

    if "clusters:" not in kubeconfig_text or "contexts:" not in kubeconfig_text:
        raise HTTPException(
            status_code=400,
            detail="Invalid kubeconfig: missing clusters or contexts",
        )

    return {"ok": True, "message": "kubeconfig is valid"}


@router.get("/connections", response_model=list[KubernetesInfo])
async def list_kubernetes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KubernetesConnection)
        .where(KubernetesConnection.user_id == user.id)
        .order_by(KubernetesConnection.created_at.desc())
    )
    return [_to_info(c) for c in result.scalars().all()]


@router.delete("/connections/{connection_id}")
async def disconnect_kubernetes(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    conn.is_active = False
    conn.status = "disconnected"
    await db.commit()
    return {"message": "Connection disconnected"}


# ── EKS ──


@router.get("/eks/aws-available", response_model=dict[str, Any])
async def eks_aws_available(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check whether the user has an active AWS connection to power EKS discovery."""
    result = await db.execute(
        select(CloudConnection).where(
            CloudConnection.user_id == user.id,
            CloudConnection.provider == "aws",
            CloudConnection.status == "active",
        )
    )
    conn = result.scalars().first()
    if not conn:
        return {"available": False, "message": "Connecting an AWS account is required for EKS discovery."}
    return {
        "available": True,
        "account_id": conn.account_id,
        "connection_id": str(conn.id),
    }


@router.get("/eks/clusters", response_model=list[dict[str, Any]])
async def list_eks_clusters(
    region: str = "us-east-1",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Discover EKS clusters using the user's active AWS connection."""
    result = await db.execute(
        select(CloudConnection).where(
            CloudConnection.user_id == user.id,
            CloudConnection.provider == "aws",
            CloudConnection.status == "active",
        )
    )
    conn = result.scalars().first()
    if not conn:
        raise HTTPException(
            status_code=400,
            detail="Connecting an AWS account is required before discovering EKS clusters.",
        )

    from app.cloud.aws.sts import STSAssumeRoleError, assume_customer_role

    encryption = get_encryption_service()
    external_id = encryption.decrypt(conn.external_id_encrypted or "")
    role_name = conn.role_arn.split("/")[-1]

    try:
        session = assume_customer_role(
            customer_account_id=conn.account_id,
            customer_role_name=role_name,
            external_id=external_id,
            session_name="devarchai-eks-discovery",
        )
        eks = session.client("eks", region_name=region)
        paginator = eks.get_paginator("list_clusters")
        cluster_names: list[str] = []
        for page in paginator.paginate():
            cluster_names.extend(page.get("clusters", []))
    except STSAssumeRoleError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to assume AWS role: {exc.message}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("eks_discovery_error", error=str(exc))
        raise HTTPException(status_code=400, detail=f"Failed to discover EKS clusters: {exc}")

    clusters: list[dict[str, Any]] = []
    for name in cluster_names:
        try:
            info = eks.describe_cluster(name=name)
            cluster = info.get("cluster", {})
            clusters.append(
                {
                    "name": name,
                    "region": region,
                    "status": cluster.get("status", "UNKNOWN"),
                    "version": cluster.get("version", ""),
                    "endpoint": cluster.get("endpoint", ""),
                    "arn": cluster.get("arn", ""),
                }
            )
        except Exception:  # noqa: BLE001
            continue

    return clusters


@router.post("/eks/connect", response_model=KubernetesInfo)
async def connect_eks_cluster(
    payload: EksConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist a selected EKS cluster as a Kubernetes connection."""
    result = await db.execute(
        select(CloudConnection).where(
            CloudConnection.user_id == user.id,
            CloudConnection.provider == "aws",
            CloudConnection.status == "active",
        )
    )
    aws_conn = result.scalars().first()
    if not aws_conn:
        raise HTTPException(
            status_code=400,
            detail="Connecting an AWS account is required before connecting EKS.",
        )

    conn = KubernetesConnection(
        user_id=user.id,
        name=payload.name or payload.cluster_name,
        provider="aws",
        kind="eks",
        aws_account_id=aws_conn.account_id,
        aws_region=payload.region,
        eks_cluster_name=payload.cluster_name,
        status="connected",
        is_active=True,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    logger.info("eks_connected", user_id=str(user.id), cluster=payload.cluster_name)

    return _to_info(conn)
