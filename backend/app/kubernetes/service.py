"""Kubernetes platform service helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.kubernetes.cache import get_cluster_cache
from app.kubernetes.collector import collect_cluster_snapshot
from app.kubernetes.connectors.factory import build_connector
from app.kubernetes.connectors.generic import GenericConnector
from app.kubernetes.types import ConnectionStatus, ValidationResult
from app.models.kubernetes import KubernetesConnection
from app.services.audit_logger import AuditLogger

logger = structlog.get_logger(__name__)


def apply_validation_result(
    connection: KubernetesConnection,
    result: ValidationResult,
    *,
    permissions: list[dict[str, Any]] | None = None,
) -> None:
    """Persist validation outcome on the connection record."""
    connection.status = result.status.value
    connection.health_status = result.status.value
    connection.kubernetes_version = result.kubernetes_version
    connection.cluster_name = result.cluster_name or connection.cluster_name or connection.name
    connection.cluster_endpoint = result.cluster_endpoint or connection.cluster_endpoint
    connection.error_message = result.error_message
    connection.last_verified_at = datetime.now(UTC)
    if permissions is not None:
        meta = dict(connection.metadata_ or {})
        meta["permissions"] = permissions
        connection.metadata_ = meta


async def validate_connection(
    connection: KubernetesConnection,
    db: AsyncSession,
    *,
    kubeconfig_override: str | None = None,
    actor_id: str | None = None,
) -> ValidationResult:
    """Validate a stored connection against the live cluster."""
    try:
        connector = await build_connector(connection, db, kubeconfig_override=kubeconfig_override)
        result = await connector.validate()
    except ValueError as exc:
        result = ValidationResult(
            status=ConnectionStatus.ERROR,
            error_message=str(exc),
            error_code="configuration_error",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("k8s_validation_failed", error_type=type(exc).__name__)
        result = ValidationResult(
            status=ConnectionStatus.UNREACHABLE,
            error_message="Unable to validate cluster connection",
            error_code="validation_failed",
        )

    permissions = [
        {"resource": p.resource, "granted": p.granted, "error": p.error}
        for p in result.permissions
    ]
    apply_validation_result(connection, result, permissions=permissions)
    await db.commit()
    await db.refresh(connection)

    if actor_id:
        await AuditLogger.log(
            actor_id=actor_id,
            action="kubernetes.connection.validated",
            resource_type="kubernetes_connection",
            resource_id=str(connection.id),
            details={
                "status": result.status.value,
                "cluster_name": result.cluster_name,
                "missing_permissions": result.missing_permissions,
            },
            db=db,
        )

    return result


async def validate_kubeconfig_text(
    kubeconfig_text: str,
    context_name: str | None = None,
) -> ValidationResult:
    """Validate kubeconfig without persisting."""
    connector = GenericConnector(kubeconfig_text, context_name=context_name)
    return await connector.validate()


async def get_or_collect_snapshot(
    connection: KubernetesConnection,
    db: AsyncSession,
    *,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Return cached snapshot or collect fresh cluster state."""
    cache = get_cluster_cache()
    connection_id = str(connection.id)

    if not force_refresh:
        cached = await cache.get_snapshot(connection_id)
        if cached:
            return cached

    connector = await build_connector(connection, db)
    snapshot = await collect_cluster_snapshot(connection, connector)
    snapshot_dict = snapshot.to_dict()

    connection.node_count = snapshot.overview.nodes_total
    connection.pod_count = snapshot.overview.pods_total
    connection.service_count = snapshot.overview.services_total
    connection.namespace_count = snapshot.overview.namespaces_total
    connection.deployment_count = snapshot.overview.deployments_total
    connection.ingress_count = snapshot.overview.ingress_total
    connection.kubernetes_version = snapshot.kubernetes_version
    await db.commit()

    await cache.set_snapshot(connection_id, snapshot_dict)
    return snapshot_dict
