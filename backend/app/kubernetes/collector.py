"""Collect cluster state in a single normalized pass."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from app.kubernetes.cache import get_cluster_cache
from app.kubernetes.connectors.base import ClusterConnector
from app.kubernetes.health_score import compute_health_score
from app.kubernetes.security_analyzer import analyze_cluster_security
from app.kubernetes.types import ClusterOverview, ClusterSnapshot
from app.kubernetes.version_advisor import build_version_advisor
from app.models.kubernetes import KubernetesConnection

logger = structlog.get_logger(__name__)

PRIORITY_EVENT_REASONS = {
    "FailedScheduling",
    "FailedMount",
    "BackOff",
    "Unhealthy",
    "Killing",
    "Pulling",
    "Pulled",
    "Failed",
    "NodeNotReady",
    "OOMKilled",
}


def _node_status(node: Any) -> str:
    for condition in node.status.conditions or []:
        if condition.type == "Ready":
            return "Ready" if condition.status == "True" else "NotReady"
    return "Unknown"


def _pod_phase_counts(pods: list[Any]) -> dict[str, int]:
    counts = {
        "running": 0,
        "pending": 0,
        "failed": 0,
        "succeeded": 0,
        "crash_loop": 0,
        "image_pull": 0,
    }
    for pod in pods:
        phase = (pod.status.phase or "").lower()
        if phase == "running":
            counts["running"] += 1
        elif phase == "pending":
            counts["pending"] += 1
        elif phase == "failed":
            counts["failed"] += 1
        elif phase == "succeeded":
            counts["succeeded"] += 1

        for cs in pod.status.container_statuses or []:
            waiting = cs.state.waiting
            if waiting:
                if waiting.reason == "CrashLoopBackOff":
                    counts["crash_loop"] += 1
                elif waiting.reason in ("ImagePullBackOff", "ErrImagePull"):
                    counts["image_pull"] += 1
    return counts


def _serialize_node(node: Any) -> dict[str, Any]:
    conditions = []
    for c in node.status.conditions or []:
        conditions.append(
            {
                "type": c.type,
                "status": c.status,
                "reason": c.reason,
                "message": c.message,
            }
        )
    allocatable = node.status.allocatable or {}
    capacity = node.status.capacity or {}
    return {
        "name": node.metadata.name,
        "status": _node_status(node),
        "version": node.status.node_info.kubelet_version if node.status.node_info else None,
        "cpu_capacity": capacity.get("cpu"),
        "memory_capacity": capacity.get("memory"),
        "cpu_allocatable": allocatable.get("cpu"),
        "memory_allocatable": allocatable.get("memory"),
        "conditions": conditions,
    }


def _serialize_pod(pod: Any) -> dict[str, Any]:
    restart_count = sum((cs.restart_count or 0) for cs in (pod.status.container_statuses or []))
    status_reason = pod.status.reason
    for cs in pod.status.container_statuses or []:
        if cs.state.waiting:
            status_reason = cs.state.waiting.reason or status_reason
        elif cs.state.terminated:
            status_reason = cs.state.terminated.reason or status_reason

    containers = []
    for cs in pod.status.container_statuses or []:
        spec_container = next(
            (c for c in (pod.spec.containers or []) if c.name == cs.name),
            None,
        )
        containers.append(
            {
                "name": cs.name,
                "ready": cs.ready,
                "restart_count": cs.restart_count,
                "image": cs.image,
                "requests": (
                    dict(spec_container.resources.requests)
                    if spec_container and spec_container.resources and spec_container.resources.requests
                    else None
                ),
                "limits": (
                    dict(spec_container.resources.limits)
                    if spec_container and spec_container.resources and spec_container.resources.limits
                    else None
                ),
            }
        )

    return {
        "namespace": pod.metadata.namespace,
        "name": pod.metadata.name,
        "status": pod.status.phase,
        "status_reason": status_reason,
        "node": pod.spec.node_name,
        "restart_count": restart_count,
        "age": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
        "containers": containers,
    }


def _serialize_namespace(ns: Any) -> dict[str, Any]:
    return {
        "name": ns.metadata.name,
        "status": ns.status.phase if ns.status else "Active",
        "labels": dict(ns.metadata.labels or {}),
    }


def _serialize_deployment(dep: Any) -> dict[str, Any]:
    desired = dep.spec.replicas or 0
    ready = dep.status.ready_replicas or 0
    available = dep.status.available_replicas or 0
    unavailable = dep.status.unavailable_replicas or 0
    healthy = ready >= desired and desired > 0
    return {
        "namespace": dep.metadata.namespace,
        "name": dep.metadata.name,
        "desired_replicas": desired,
        "ready_replicas": ready,
        "available_replicas": available,
        "unavailable_replicas": unavailable,
        "status": "Healthy" if healthy else "Degraded",
    }


def _serialize_service(svc: Any) -> dict[str, Any]:
    return {
        "namespace": svc.metadata.namespace,
        "name": svc.metadata.name,
        "type": svc.spec.type,
        "cluster_ip": svc.spec.cluster_ip,
        "ports": [
            {"port": p.port, "protocol": p.protocol, "name": p.name}
            for p in (svc.spec.ports or [])
        ],
    }


def _serialize_ingress(ing: Any) -> dict[str, Any]:
    hosts = [r.host for r in (ing.spec.rules or []) if r.host]
    tls = bool(ing.spec.tls)
    return {
        "namespace": ing.metadata.namespace,
        "name": ing.metadata.name,
        "hosts": hosts,
        "ingress_class": ing.spec.ingress_class_name,
        "tls_enabled": tls,
        "load_balancer": (
            ing.status.load_balancer.ingress[0].hostname
            if ing.status and ing.status.load_balancer and ing.status.load_balancer.ingress
            else None
        ),
    }


def _serialize_event(event: Any) -> dict[str, Any]:
    return {
        "timestamp": event.last_timestamp.isoformat() if event.last_timestamp else (
            event.event_time.isoformat() if event.event_time else None
        ),
        "namespace": event.metadata.namespace,
        "resource": f"{event.involved_object.kind}/{event.involved_object.name}" if event.involved_object else None,
        "reason": event.reason,
        "message": event.message,
        "severity": event.type or "Normal",
        "priority": event.reason in PRIORITY_EVENT_REASONS,
    }


async def collect_cluster_snapshot(
    connection: KubernetesConnection,
    connector: ClusterConnector,
) -> ClusterSnapshot:
    """Single collection pass → normalized cluster context."""
    api = connector.get_api_client()
    core = api.CoreV1Api()
    apps = api.AppsV1Api()
    networking = api.NetworkingV1Api()
    rbac = api.RbacAuthorizationV1Api()

    nodes = core.list_node(_request_timeout=30).items
    pods = core.list_pod_for_all_namespaces(_request_timeout=30).items
    deployments = apps.list_deployment_for_all_namespaces(_request_timeout=30).items
    services = core.list_service_for_all_namespaces(_request_timeout=30).items
    ingresses = networking.list_ingress_for_all_namespaces(_request_timeout=30).items
    namespaces = core.list_namespace(_request_timeout=30).items
    events = core.list_event_for_all_namespaces(_request_timeout=30).items

    node_ready = sum(1 for n in nodes if _node_status(n) == "Ready")
    pod_counts = _pod_phase_counts(pods)

    dep_healthy = 0
    dep_degraded = 0
    for dep in deployments:
        desired = dep.spec.replicas or 0
        ready = dep.status.ready_replicas or 0
        if ready >= desired and desired > 0:
            dep_healthy += 1
        elif desired > 0:
            dep_degraded += 1

    priority_events = [e for e in events if e.reason in PRIORITY_EVENT_REASONS]
    serialized_events = sorted(
        [_serialize_event(e) for e in priority_events[:100]],
        key=lambda x: x.get("timestamp") or "",
        reverse=True,
    )

    overview = ClusterOverview(
        nodes_total=len(nodes),
        nodes_ready=node_ready,
        nodes_not_ready=len(nodes) - node_ready,
        pods_total=len(pods),
        pods_running=pod_counts["running"],
        pods_pending=pod_counts["pending"],
        pods_failed=pod_counts["failed"],
        pods_succeeded=pod_counts["succeeded"],
        pods_crash_loop=pod_counts["crash_loop"],
        pods_image_pull=pod_counts["image_pull"],
        deployments_total=len(deployments),
        deployments_healthy=dep_healthy,
        deployments_degraded=dep_degraded,
        services_total=len(services),
        ingress_total=len(ingresses),
        namespaces_total=len(namespaces),
        warnings_total=len(priority_events),
    )

    version_api = api.VersionApi()
    try:
        version_info = version_api.get_code()
        k8s_version = f"v{version_info.git_version.lstrip('v')}" if version_info.git_version else connection.kubernetes_version
    except Exception:
        k8s_version = connection.kubernetes_version or "unknown"

    cache = get_cluster_cache()
    version_advisor = await cache.get_version_advisor(str(connection.id), k8s_version or "unknown")
    if not version_advisor:
        version_advisor = build_version_advisor(
            k8s_version or "unknown",
            provider=connection.provider,
            kind=connection.kind,
            region=connection.aws_region,
        )
        await cache.set_version_advisor(str(connection.id), k8s_version or "unknown", version_advisor)

    security_findings = analyze_cluster_security(
        pods,
        deployments,
        services=services,
        ingresses=ingresses,
        rbac_api=rbac,
    )
    health_score = compute_health_score(
        overview=overview,
        security_findings=security_findings,
        version_advisor=version_advisor,
        connection_status=connection.status,
    )

    return ClusterSnapshot(
        connection_id=str(connection.id),
        cluster_name=connection.cluster_name or connection.name,
        provider=connection.provider,
        kind=connection.kind,
        kubernetes_version=k8s_version or "unknown",
        region=connection.aws_region,
        status=connection.status,
        collected_at=datetime.now(UTC).isoformat(),
        overview=overview,
        nodes=[_serialize_node(n) for n in nodes],
        pods=[_serialize_pod(p) for p in pods[:500]],
        namespaces=[_serialize_namespace(n) for n in namespaces],
        deployments=[_serialize_deployment(d) for d in deployments[:200]],
        services=[_serialize_service(s) for s in services[:200]],
        ingresses=[_serialize_ingress(i) for i in ingresses[:100]],
        events=serialized_events,
        security_findings=security_findings,
        health_score=health_score,
        version_advisor=version_advisor,
    )
