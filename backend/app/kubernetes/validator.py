"""Kubernetes connection validation — live API checks."""

from __future__ import annotations

from typing import Any

import structlog

from app.kubernetes.types import (
    ConnectionStatus,
    PermissionCheck,
    READ_ONLY_RESOURCES,
    ValidationResult,
)

logger = structlog.get_logger(__name__)

# Map resource names to API list calls used for RBAC probing.
_RESOURCE_PROBES: dict[str, str] = {
    "nodes": "_probe_nodes",
    "pods": "_probe_pods",
    "namespaces": "_probe_namespaces",
    "deployments": "_probe_deployments",
    "services": "_probe_services",
    "ingresses": "_probe_ingresses",
    "events": "_probe_events",
}


def _classify_api_error(exc: Exception) -> tuple[ConnectionStatus, str, str]:
    msg = str(exc).lower()
    exc_type = type(exc).__name__

    if "401" in msg or "unauthorized" in msg or exc_type == "Unauthorized":
        return ConnectionStatus.AUTH_FAILED, "Authentication failed", "auth_failed"
    if "403" in msg or "forbidden" in msg or exc_type == "Forbidden":
        return ConnectionStatus.PERMISSION_DENIED, "Permission denied", "permission_denied"
    if "expired" in msg or "token" in msg and "invalid" in msg:
        return ConnectionStatus.EXPIRED, "Credentials expired", "credential_expired"
    if "connection" in msg or "timeout" in msg or "refused" in msg or "unreachable" in msg:
        return ConnectionStatus.UNREACHABLE, "Cluster unreachable", "unreachable"
    return ConnectionStatus.ERROR, "Kubernetes API error", "api_error"


def validate_api_client(
    api: Any,
    *,
    cluster_name: str | None,
    cluster_endpoint: str | None,
    region: str | None,
) -> ValidationResult:
    """Validate API connectivity and read-only permissions."""
    version_api = api.VersionApi()
    core_api = api.CoreV1Api()
    apps_api = api.AppsV1Api()
    networking_api = api.NetworkingV1Api()

    try:
        version_info = version_api.get_code()
        k8s_version = f"v{version_info.git_version.lstrip('v')}" if version_info.git_version else None
    except Exception as exc:  # noqa: BLE001
        status, message, code = _classify_api_error(exc)
        logger.warning("k8s_version_check_failed", error_type=type(exc).__name__)
        return ValidationResult(
            status=status,
            cluster_name=cluster_name,
            cluster_endpoint=cluster_endpoint,
            region=region,
            error_message=message,
            error_code=code,
        )

    permissions: list[PermissionCheck] = []

    def _check(resource: str, fn: Any) -> None:
        try:
            fn()
            permissions.append(PermissionCheck(resource=resource, granted=True))
        except Exception as exc:  # noqa: BLE001
            status, _, _ = _classify_api_error(exc)
            granted = status != ConnectionStatus.PERMISSION_DENIED
            permissions.append(
                PermissionCheck(
                    resource=resource,
                    granted=granted,
                    error=str(exc)[:200] if not granted else None,
                )
            )

    _check("nodes", lambda: core_api.list_node(limit=1, _request_timeout=10))
    _check("pods", lambda: core_api.list_pod_for_all_namespaces(limit=1, _request_timeout=10))
    _check("namespaces", lambda: core_api.list_namespace(limit=1, _request_timeout=10))
    _check("deployments", lambda: apps_api.list_deployment_for_all_namespaces(limit=1, _request_timeout=10))
    _check("services", lambda: core_api.list_service_for_all_namespaces(limit=1, _request_timeout=10))
    _check("ingresses", lambda: networking_api.list_ingress_for_all_namespaces(limit=1, _request_timeout=10))
    _check("events", lambda: core_api.list_event_for_all_namespaces(limit=1, _request_timeout=10))

    missing = [p.resource for p in permissions if not p.granted]
    critical_missing = [r for r in missing if r in ("nodes", "pods", "namespaces")]

    if critical_missing:
        status = ConnectionStatus.PERMISSION_DENIED
        error_message = (
            f"DevArchAI can connect to the Kubernetes API but lacks permission to list "
            f"{', '.join(critical_missing)}."
        )
        error_code = "permission_denied"
    elif missing:
        status = ConnectionStatus.DEGRADED
        error_message = f"Partial access — missing permissions for: {', '.join(missing)}"
        error_code = "partial_permissions"
    else:
        status = ConnectionStatus.CONNECTED
        error_message = None
        error_code = None

    return ValidationResult(
        status=status,
        kubernetes_version=k8s_version,
        cluster_name=cluster_name,
        cluster_endpoint=cluster_endpoint,
        region=region,
        permissions=permissions,
        error_message=error_message,
        error_code=error_code,
        metadata={"read_only_resources": list(READ_ONLY_RESOURCES)},
    )
