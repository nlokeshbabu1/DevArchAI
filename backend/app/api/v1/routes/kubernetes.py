"""Kubernetes integration routes.

Supports generic kubeconfig and EKS connections with live validation,
cluster collection, security analysis, and async AI analysis.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import get_encryption_service
from app.core.security import get_current_user
from app.db.session import get_db
from app.kubernetes.service import (
    get_or_collect_snapshot,
    validate_connection,
    validate_kubeconfig_text,
)
from app.kubernetes.types import ConnectionStatus
from app.models.cloud import CloudConnection
from app.models.cluster_ai_job import ClusterAIJob, ClusterAIJobStatus
from app.models.kubernetes import KubernetesConnection
from app.models.user import User
from app.schemas.kubernetes import (
    AIAnalysisRequest,
    ClusterAIJobInfo,
    EksConnectRequest,
    KubernetesConnectRequest,
    KubernetesInfo,
    PermissionInfo,
    UpgradeAnalysisRequest,
)
from app.services.audit_logger import AuditLogger

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/kubernetes", tags=["Kubernetes"])


def _to_info(c: KubernetesConnection) -> KubernetesInfo:
    permissions = None
    if c.metadata_ and c.metadata_.get("permissions"):
        permissions = [PermissionInfo(**p) for p in c.metadata_["permissions"]]

    return KubernetesInfo(
        id=str(c.id),
        name=c.name,
        provider=c.provider,
        kind=c.kind,
        context_name=c.context_name,
        cluster_name=c.cluster_name or c.eks_cluster_name or c.name,
        cluster_endpoint=c.cluster_endpoint,
        aws_account_id=c.aws_account_id,
        aws_region=c.aws_region,
        eks_cluster_name=c.eks_cluster_name,
        kubernetes_version=c.kubernetes_version,
        health_status=c.health_status or c.status,
        status=c.status,
        is_active=c.is_active,
        node_count=c.node_count,
        pod_count=c.pod_count,
        service_count=c.service_count,
        namespace_count=c.namespace_count,
        deployment_count=c.deployment_count,
        ingress_count=c.ingress_count,
        last_verified_at=c.last_verified_at.isoformat() if c.last_verified_at else None,
        error_message=c.error_message,
        permissions=permissions,
        created_at=c.created_at.isoformat() if c.created_at else None,
        updated_at=c.updated_at.isoformat() if c.updated_at else None,
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


def _decode_kubeconfig(payload: KubernetesConnectRequest) -> str:
    try:
        return base64.b64decode(payload.kubeconfig).decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 kubeconfig") from exc


@router.post("/connect", response_model=KubernetesInfo)
async def connect_kubernetes(
    payload: KubernetesConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect a Kubernetes cluster from a kubeconfig with live validation."""
    kubeconfig_text = _decode_kubeconfig(payload)

    if "clusters:" not in kubeconfig_text or "contexts:" not in kubeconfig_text:
        raise HTTPException(status_code=400, detail="Invalid kubeconfig: missing clusters or contexts")

    validation = await validate_kubeconfig_text(kubeconfig_text, payload.context_name)
    if validation.status in (ConnectionStatus.UNREACHABLE, ConnectionStatus.AUTH_FAILED, ConnectionStatus.ERROR):
        raise HTTPException(
            status_code=400,
            detail={
                "message": validation.error_message or "Connection validation failed",
                "status": validation.status.value,
                "code": validation.error_code,
            },
        )

    encryption = get_encryption_service()
    conn = KubernetesConnection(
        user_id=user.id,
        name=payload.name,
        provider="kubernetes",
        kind="generic",
        kubeconfig_encrypted=encryption.encrypt(kubeconfig_text),
        context_name=payload.context_name,
        cluster_name=validation.cluster_name or payload.name,
        cluster_endpoint=validation.cluster_endpoint,
        kubernetes_version=validation.kubernetes_version,
        status=validation.status.value,
        health_status=validation.status.value,
        is_active=True,
        error_message=validation.error_message,
        last_verified_at=datetime.now(UTC),
    )
    if validation.permissions:
        conn.metadata_ = {
            "permissions": [
                {"resource": p.resource, "granted": p.granted, "error": p.error}
                for p in validation.permissions
            ]
        }

    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    await AuditLogger.log(
        actor_id=str(user.id),
        action="kubernetes.connection.created",
        resource_type="kubernetes_connection",
        resource_id=str(conn.id),
        details={"provider": "kubernetes", "status": conn.status},
        db=db,
    )

    logger.info("kubernetes_connected", user_id=str(user.id), connection_id=str(conn.id))
    return _to_info(conn)


@router.post("/test", response_model=dict[str, Any])
async def test_kubernetes(
    payload: KubernetesConnectRequest,
    user: User = Depends(get_current_user),
):
    """Validate a kubeconfig without persisting it."""
    kubeconfig_text = _decode_kubeconfig(payload)

    if "clusters:" not in kubeconfig_text or "contexts:" not in kubeconfig_text:
        raise HTTPException(status_code=400, detail="Invalid kubeconfig: missing clusters or contexts")

    validation = await validate_kubeconfig_text(kubeconfig_text, payload.context_name)
    return {
        "ok": validation.status in (ConnectionStatus.CONNECTED, ConnectionStatus.DEGRADED),
        "status": validation.status.value,
        "kubernetes_version": validation.kubernetes_version,
        "cluster_name": validation.cluster_name,
        "cluster_endpoint": validation.cluster_endpoint,
        "missing_permissions": validation.missing_permissions,
        "message": validation.error_message or "Connection validated successfully",
    }


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


@router.get("/connections/{connection_id}", response_model=KubernetesInfo)
async def get_kubernetes_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    return _to_info(conn)


@router.delete("/connections/{connection_id}")
async def disconnect_kubernetes(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    conn.is_active = False
    conn.status = ConnectionStatus.DISCONNECTED.value
    conn.health_status = ConnectionStatus.DISCONNECTED.value
    await db.commit()

    await AuditLogger.log(
        actor_id=str(user.id),
        action="kubernetes.connection.disconnected",
        resource_type="kubernetes_connection",
        resource_id=str(conn.id),
        db=db,
    )

    return {"message": "Connection disconnected"}


@router.post("/connections/{connection_id}/validate", response_model=KubernetesInfo)
async def validate_kubernetes_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    if not conn.is_active:
        raise HTTPException(status_code=400, detail="Connection is not active")

    await validate_connection(conn, db, actor_id=str(user.id))
    await db.refresh(conn)
    return _to_info(conn)


@router.post("/connections/{connection_id}/refresh")
async def refresh_kubernetes_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    if not conn.is_active:
        raise HTTPException(status_code=400, detail="Connection is not active")

    snapshot = await get_or_collect_snapshot(conn, db, force_refresh=True)
    await AuditLogger.log(
        actor_id=str(user.id),
        action="kubernetes.cluster.refreshed",
        resource_type="kubernetes_connection",
        resource_id=str(conn.id),
        db=db,
    )
    return snapshot


async def _queue_ai_analysis(
    conn: KubernetesConnection,
    user: User,
    db: AsyncSession,
    background_tasks: BackgroundTasks | None = None,
) -> ClusterAIJob | None:
    """Queue AI analysis if no active job exists."""
    active = await db.execute(
        select(ClusterAIJob).where(
            ClusterAIJob.connection_id == conn.id,
            ClusterAIJob.user_id == user.id,
            ClusterAIJob.status.in_([
                ClusterAIJobStatus.QUEUED.value,
                ClusterAIJobStatus.RUNNING.value,
                ClusterAIJobStatus.RAG_RETRIEVING.value,
                ClusterAIJobStatus.GENERATING.value,
                ClusterAIJobStatus.CHECKING_CACHE.value,
                ClusterAIJobStatus.COLLECTING.value,
            ]),
        )
    )
    if active.scalars().first():
        return None

    job = ClusterAIJob(
        connection_id=conn.id,
        user_id=user.id,
        status=ClusterAIJobStatus.QUEUED.value,
        analysis_type="cluster",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from app.workers.tasks.cluster_ai import enqueue_cluster_ai_job

    enqueue_cluster_ai_job(str(job.id))
    return job


@router.get("/connections/{connection_id}/overview")
async def get_cluster_overview(
    connection_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    if not conn.is_active:
        raise HTTPException(status_code=400, detail="Connection is not active")

    snapshot = await get_or_collect_snapshot(conn, db)
    ai_job = await _queue_ai_analysis(conn, user, db, background_tasks)

    latest_job = None
    if not ai_job:
        job_result = await db.execute(
            select(ClusterAIJob)
            .where(ClusterAIJob.connection_id == conn.id, ClusterAIJob.user_id == user.id)
            .order_by(ClusterAIJob.created_at.desc())
            .limit(1)
        )
        latest = job_result.scalars().first()
        if latest:
            latest_job = ClusterAIJobInfo(
                id=str(latest.id),
                connection_id=str(latest.connection_id),
                status=latest.status,
                analysis_type=latest.analysis_type,
                result=latest.result,
                error_message=latest.error_message,
                finding_count=latest.finding_count,
                recommendation_count=latest.recommendation_count,
                started_at=latest.started_at.isoformat() if latest.started_at else None,
                completed_at=latest.completed_at.isoformat() if latest.completed_at else None,
                created_at=latest.created_at.isoformat() if latest.created_at else None,
            )
    elif ai_job:
        latest_job = ClusterAIJobInfo(
            id=str(ai_job.id),
            connection_id=str(ai_job.connection_id),
            status=ai_job.status,
            analysis_type=ai_job.analysis_type,
            created_at=ai_job.created_at.isoformat() if ai_job.created_at else None,
        )

    await AuditLogger.log(
        actor_id=str(user.id),
        action="kubernetes.cluster.viewed",
        resource_type="kubernetes_connection",
        resource_id=str(conn.id),
        db=db,
    )
    await db.refresh(conn)
    return {
        "connection": _to_info(conn).model_dump(),
        "overview": snapshot.get("overview"),
        "health_score": snapshot.get("health_score"),
        "version_advisor": snapshot.get("version_advisor"),
        "security_findings": snapshot.get("security_findings", [])[:20],
        "collected_at": snapshot.get("collected_at"),
        "ai_job": latest_job.model_dump() if latest_job else None,
    }


@router.get("/connections/{connection_id}/nodes")
async def get_cluster_nodes(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    return {"nodes": snapshot.get("nodes", []), "collected_at": snapshot.get("collected_at")}


@router.get("/connections/{connection_id}/pods")
async def get_cluster_pods(
    connection_id: str,
    namespace: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    pods = snapshot.get("pods", [])
    if namespace:
        pods = [p for p in pods if p.get("namespace") == namespace]
    return {"pods": pods, "collected_at": snapshot.get("collected_at")}


@router.get("/connections/{connection_id}/pods/{namespace}/{pod_name}")
async def get_cluster_pod_detail(
    connection_id: str,
    namespace: str,
    pod_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    pod = next(
        (p for p in snapshot.get("pods", []) if p.get("namespace") == namespace and p.get("name") == pod_name),
        None,
    )
    if not pod:
        raise HTTPException(status_code=404, detail="Pod not found")
    events = [
        e for e in snapshot.get("events", [])
        if e.get("resource") == f"Pod/{pod_name}" and (not e.get("namespace") or e.get("namespace") == namespace)
    ]
    return {"pod": pod, "events": events}


@router.get("/connections/{connection_id}/namespaces")
async def get_cluster_namespaces(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    return {"namespaces": snapshot.get("namespaces", []), "collected_at": snapshot.get("collected_at")}


@router.get("/connections/{connection_id}/deployments")
async def get_cluster_deployments(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    return {"deployments": snapshot.get("deployments", []), "collected_at": snapshot.get("collected_at")}


@router.get("/connections/{connection_id}/services")
async def get_cluster_services(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    return {"services": snapshot.get("services", []), "collected_at": snapshot.get("collected_at")}


@router.get("/connections/{connection_id}/ingresses")
async def get_cluster_ingresses(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    return {"ingresses": snapshot.get("ingresses", []), "collected_at": snapshot.get("collected_at")}


@router.get("/connections/{connection_id}/events")
async def get_cluster_events(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    return {"events": snapshot.get("events", []), "collected_at": snapshot.get("collected_at")}


@router.get("/connections/{connection_id}/security-findings")
async def get_security_findings(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    return {
        "findings": snapshot.get("security_findings", []),
        "collected_at": snapshot.get("collected_at"),
    }


@router.post("/connections/{connection_id}/security-scan")
async def run_security_scan(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db, force_refresh=True)
    await AuditLogger.log(
        actor_id=str(user.id),
        action="kubernetes.security_scan.started",
        resource_type="kubernetes_connection",
        resource_id=str(conn.id),
        db=db,
    )
    return {
        "findings": snapshot.get("security_findings", []),
        "health_score": snapshot.get("health_score"),
        "collected_at": snapshot.get("collected_at"),
    }


@router.get("/connections/{connection_id}/health-score")
async def get_health_score(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    return snapshot.get("health_score") or {}


@router.get("/connections/{connection_id}/version-advisor")
async def get_version_advisor(
    connection_id: str,
    target_version: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    snapshot = await get_or_collect_snapshot(conn, db)
    advisor = snapshot.get("version_advisor") or {}

    if target_version:
        from app.kubernetes.cache import get_cluster_cache
        from app.kubernetes.upgrade_readiness import explain_version_risk

        cache = get_cluster_cache()
        k8s_version = snapshot.get("kubernetes_version", "unknown")
        cached = await cache.get_upgrade_analysis(str(conn.id), k8s_version, target_version)
        if cached:
            advisor = {**advisor, **cached}
            advisor["version_detail"] = explain_version_risk(cached, target_version)
        else:
            advisor["version_detail"] = {"target_version": target_version, "status": "analysis_required"}

    return advisor


def _active_job_filter(user_id: Any, connection_id: Any) -> Any:
    return (
        ClusterAIJob.connection_id == connection_id,
        ClusterAIJob.user_id == user_id,
        ClusterAIJob.status.in_([
            ClusterAIJobStatus.QUEUED.value,
            ClusterAIJobStatus.RUNNING.value,
            ClusterAIJobStatus.RAG_RETRIEVING.value,
            ClusterAIJobStatus.GENERATING.value,
            ClusterAIJobStatus.CHECKING_CACHE.value,
            ClusterAIJobStatus.COLLECTING.value,
            ClusterAIJobStatus.MCP_RETRIEVING.value,
        ]),
    )


async def _create_analysis_job(
    conn: KubernetesConnection,
    user: User,
    db: AsyncSession,
    *,
    analysis_type: str,
    request_payload: dict[str, Any] | None = None,
) -> ClusterAIJob:
    active_result = await db.execute(
        select(ClusterAIJob).where(
            *_active_job_filter(user.id, conn.id),
            ClusterAIJob.analysis_type == analysis_type,
        ).order_by(ClusterAIJob.created_at.desc()).limit(1)
    )
    existing = active_result.scalars().first()
    if existing:
        from app.workers.tasks.cluster_ai import enqueue_cluster_ai_job

        enqueue_cluster_ai_job(str(existing.id))
        return existing

    job = ClusterAIJob(
        connection_id=conn.id,
        user_id=user.id,
        status=ClusterAIJobStatus.QUEUED.value,
        analysis_type=analysis_type,
        result={"_request": request_payload or {}},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from app.workers.tasks.cluster_ai import enqueue_cluster_ai_job

    enqueue_cluster_ai_job(str(job.id))
    return job


@router.post("/connections/{connection_id}/upgrade-analysis", response_model=ClusterAIJobInfo)
async def start_upgrade_analysis(
    connection_id: str,
    body: UpgradeAnalysisRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    if not conn.is_active:
        raise HTTPException(status_code=400, detail="Connection is not active")

    payload = {"target_version": (body.target_version if body else None) or "v1.34"}
    job = await _create_analysis_job(
        conn, user, db, analysis_type="upgrade", request_payload=payload,
    )

    await AuditLogger.log(
        actor_id=str(user.id),
        action="kubernetes.upgrade_analysis.started",
        resource_type="kubernetes_connection",
        resource_id=str(conn.id),
        details={"job_id": str(job.id), "target_version": payload["target_version"]},
        db=db,
    )

    return ClusterAIJobInfo(
        id=str(job.id),
        connection_id=str(job.connection_id),
        status=job.status,
        analysis_type=job.analysis_type,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


@router.get("/connections/{connection_id}/upgrade-analysis/{job_id}", response_model=ClusterAIJobInfo)
async def get_upgrade_analysis_job(
    connection_id: str,
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_ai_analysis_job(connection_id, job_id, user, db)


@router.post("/connections/{connection_id}/ai-analysis", response_model=ClusterAIJobInfo)
async def start_ai_analysis(
    connection_id: str,
    body: AIAnalysisRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conn = await _owned_connection(connection_id, user, db)
    if not conn.is_active:
        raise HTTPException(status_code=400, detail="Connection is not active")

    analysis_type = "troubleshoot" if (body and body.question) else (
        (body.analysis_type if body and body.analysis_type else "copilot")
    )
    request_payload = {}
    if body and body.question:
        request_payload["question"] = body.question

    job = await _create_analysis_job(
        conn, user, db, analysis_type=analysis_type, request_payload=request_payload,
    )

    await AuditLogger.log(
        actor_id=str(user.id),
        action="kubernetes.ai_analysis.started",
        resource_type="kubernetes_connection",
        resource_id=str(conn.id),
        details={"job_id": str(job.id), "analysis_type": analysis_type},
        db=db,
    )

    return ClusterAIJobInfo(
        id=str(job.id),
        connection_id=str(job.connection_id),
        status=job.status,
        analysis_type=job.analysis_type,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


@router.get("/connections/{connection_id}/ai-analysis/latest", response_model=ClusterAIJobInfo | None)
async def get_latest_ai_analysis(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_connection(connection_id, user, db)
    result = await db.execute(
        select(ClusterAIJob)
        .where(ClusterAIJob.connection_id == connection_id, ClusterAIJob.user_id == user.id)
        .order_by(ClusterAIJob.created_at.desc())
        .limit(1)
    )
    job = result.scalars().first()
    if not job:
        return None
    return ClusterAIJobInfo(
        id=str(job.id),
        connection_id=str(job.connection_id),
        status=job.status,
        analysis_type=job.analysis_type,
        result=job.result,
        error_message=job.error_message,
        finding_count=job.finding_count,
        recommendation_count=job.recommendation_count,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


@router.get("/connections/{connection_id}/ai-analysis/{job_id}", response_model=ClusterAIJobInfo)
async def get_ai_analysis_job(
    connection_id: str,
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_connection(connection_id, user, db)
    result = await db.execute(
        select(ClusterAIJob).where(
            ClusterAIJob.id == job_id,
            ClusterAIJob.connection_id == connection_id,
            ClusterAIJob.user_id == user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="AI analysis job not found")

    if job.status == ClusterAIJobStatus.COMPLETED.value:
        await AuditLogger.log(
            actor_id=str(user.id),
            action="kubernetes.ai_analysis.completed",
            resource_type="kubernetes_connection",
            resource_id=connection_id,
            details={"job_id": job_id},
            db=db,
        )

    return ClusterAIJobInfo(
        id=str(job.id),
        connection_id=str(job.connection_id),
        status=job.status,
        analysis_type=job.analysis_type,
        result=job.result,
        error_message=job.error_message,
        finding_count=job.finding_count,
        recommendation_count=job.recommendation_count,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


# ── EKS ──


@router.get("/eks/aws-available", response_model=dict[str, Any])
async def eks_aws_available(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
        cluster_name=payload.cluster_name,
        is_active=True,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    validation = await validate_connection(conn, db, actor_id=str(user.id))
    await db.refresh(conn)

    if validation.status in (ConnectionStatus.UNREACHABLE, ConnectionStatus.AUTH_FAILED, ConnectionStatus.ERROR):
        conn.is_active = False
        await db.commit()
        raise HTTPException(
            status_code=400,
            detail={
                "message": validation.error_message or "EKS connection validation failed",
                "status": validation.status.value,
            },
        )

    await AuditLogger.log(
        actor_id=str(user.id),
        action="kubernetes.connection.created",
        resource_type="kubernetes_connection",
        resource_id=str(conn.id),
        details={"provider": "aws", "kind": "eks", "cluster": payload.cluster_name},
        db=db,
    )

    logger.info("eks_connected", user_id=str(user.id), cluster=payload.cluster_name)
    return _to_info(conn)
