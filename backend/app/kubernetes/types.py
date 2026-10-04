"""Shared Kubernetes platform types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConnectionStatus(str, Enum):
    """Live connection health — not set on credential save alone."""

    CONNECTED = "connected"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    AUTH_FAILED = "auth_failed"
    PERMISSION_DENIED = "permission_denied"
    EXPIRED = "expired"
    ERROR = "error"
    DISCONNECTED = "disconnected"


READ_ONLY_RESOURCES = (
    "nodes",
    "pods",
    "namespaces",
    "deployments",
    "replicasets",
    "statefulsets",
    "daemonsets",
    "jobs",
    "cronjobs",
    "services",
    "ingresses",
    "events",
    "configmaps",
    "horizontalpodautoscalers",
    "poddisruptionbudgets",
    "networkpolicies",
    "resourcequotas",
    "limitranges",
)


@dataclass
class PermissionCheck:
    resource: str
    granted: bool
    required_verbs: tuple[str, ...] = ("get", "list", "watch")
    error: str | None = None


@dataclass
class ValidationResult:
    status: ConnectionStatus
    kubernetes_version: str | None = None
    cluster_name: str | None = None
    cluster_endpoint: str | None = None
    region: str | None = None
    permissions: list[PermissionCheck] = field(default_factory=list)
    error_message: str | None = None
    error_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def missing_permissions(self) -> list[str]:
        return [p.resource for p in self.permissions if not p.granted]


@dataclass
class ClusterOverview:
    nodes_total: int = 0
    nodes_ready: int = 0
    nodes_not_ready: int = 0
    pods_total: int = 0
    pods_running: int = 0
    pods_pending: int = 0
    pods_failed: int = 0
    pods_succeeded: int = 0
    pods_crash_loop: int = 0
    pods_image_pull: int = 0
    deployments_total: int = 0
    deployments_healthy: int = 0
    deployments_degraded: int = 0
    services_total: int = 0
    ingress_total: int = 0
    namespaces_total: int = 0
    warnings_total: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {
                "total": self.nodes_total,
                "ready": self.nodes_ready,
                "not_ready": self.nodes_not_ready,
            },
            "pods": {
                "total": self.pods_total,
                "running": self.pods_running,
                "pending": self.pods_pending,
                "failed": self.pods_failed,
                "crash_loop_back_off": self.pods_crash_loop,
                "succeeded": self.pods_succeeded,
                "image_pull_backoff": self.pods_image_pull,
            },
            "deployments": {
                "total": self.deployments_total,
                "healthy": self.deployments_healthy,
                "degraded": self.deployments_degraded,
            },
            "services": {"total": self.services_total},
            "ingress": {"total": self.ingress_total},
            "namespaces": {"total": self.namespaces_total},
            "warnings": {"total": self.warnings_total},
        }


@dataclass
class ClusterSnapshot:
    connection_id: str
    cluster_name: str
    provider: str
    kind: str
    kubernetes_version: str
    region: str | None
    status: str
    collected_at: str
    overview: ClusterOverview
    nodes: list[dict[str, Any]] = field(default_factory=list)
    pods: list[dict[str, Any]] = field(default_factory=list)
    namespaces: list[dict[str, Any]] = field(default_factory=list)
    deployments: list[dict[str, Any]] = field(default_factory=list)
    services: list[dict[str, Any]] = field(default_factory=list)
    ingresses: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    security_findings: list[dict[str, Any]] = field(default_factory=list)
    health_score: dict[str, Any] | None = None
    version_advisor: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "cluster_name": self.cluster_name,
            "provider": self.provider,
            "kind": self.kind,
            "kubernetes_version": self.kubernetes_version,
            "region": self.region,
            "status": self.status,
            "collected_at": self.collected_at,
            "overview": self.overview.to_dict(),
            "nodes": self.nodes,
            "pods": self.pods,
            "namespaces": self.namespaces,
            "deployments": self.deployments,
            "services": self.services,
            "ingresses": self.ingresses,
            "events": self.events,
            "security_findings": self.security_findings,
            "health_score": self.health_score,
            "version_advisor": self.version_advisor,
        }
