"""Extended cluster discovery for upgrade readiness analysis."""

from __future__ import annotations

from typing import Any

import structlog

from app.kubernetes.connectors.base import ClusterConnector

logger = structlog.get_logger(__name__)


def _safe_list(callable_fn: Any, label: str) -> list[Any]:
    try:
        return callable_fn().items
    except Exception as exc:
        logger.debug("upgrade_collect_skip", resource=label, error=str(exc))
        return []


def _serialize_crd(crd: Any) -> dict[str, Any]:
    versions = []
    served = []
    storage = None
    for v in crd.spec.versions or []:
        versions.append(v.name)
        if v.served:
            served.append(v.name)
        if v.storage:
            storage = v.name
    conversion = None
    if crd.spec.conversion:
        conversion = crd.spec.conversion.strategy
    return {
        "name": crd.metadata.name,
        "group": crd.spec.group,
        "scope": crd.spec.scope,
        "versions": versions,
        "served_versions": served,
        "storage_version": storage,
        "conversion_strategy": conversion,
        "instance_count": 0,
        "controller": None,
    }


def _serialize_workload(obj: Any, kind: str, api_version: str) -> dict[str, Any]:
    return {
        "api_version": api_version,
        "kind": kind,
        "namespace": getattr(obj.metadata, "namespace", None),
        "name": obj.metadata.name,
    }


def _serialize_webhook(wh: Any, webhook_type: str) -> dict[str, Any]:
    client_cfg = wh.client_config
    return {
        "type": webhook_type,
        "name": wh.name if hasattr(wh, "name") else wh.metadata.name,
        "api_version": "admissionregistration.k8s.io/v1",
        "kind": f"{webhook_type}WebhookConfiguration",
        "failure_policy": getattr(wh, "failure_policy", None),
        "rules": [
            {
                "api_groups": list(r.api_groups or []),
                "api_versions": list(r.api_versions or []),
                "operations": list(r.operations or []),
                "resources": list(r.resources or []),
            }
            for r in (getattr(wh, "rules", None) or [])
        ],
        "service": (
            {
                "namespace": client_cfg.service.namespace,
                "name": client_cfg.service.name,
            }
            if client_cfg and client_cfg.service
            else None
        ),
    }


def _serialize_pdb(pdb: Any) -> dict[str, Any]:
    return {
        "api_version": "policy/v1",
        "kind": "PodDisruptionBudget",
        "namespace": pdb.metadata.namespace,
        "name": pdb.metadata.name,
        "min_available": pdb.spec.min_available if pdb.spec else None,
        "max_unavailable": pdb.spec.max_unavailable if pdb.spec else None,
    }


def _serialize_storage_class(sc: Any) -> dict[str, Any]:
    return {
        "name": sc.metadata.name,
        "provisioner": sc.provisioner,
        "reclaim_policy": sc.reclaim_policy,
        "volume_binding_mode": sc.volume_binding_mode,
    }


def _serialize_pv(pv: Any) -> dict[str, Any]:
    return {
        "name": pv.metadata.name,
        "capacity": dict(pv.spec.capacity or {}) if pv.spec else {},
        "storage_class": pv.spec.storage_class_name if pv.spec else None,
        "status": pv.status.phase if pv.status else None,
    }


def _serialize_pvc(pvc: Any) -> dict[str, Any]:
    return {
        "namespace": pvc.metadata.namespace,
        "name": pvc.metadata.name,
        "storage_class": pvc.spec.storage_class_name if pvc.spec else None,
        "status": pvc.status.phase if pvc.status else None,
    }


def _serialize_network_policy(np: Any) -> dict[str, Any]:
    return {
        "namespace": np.metadata.namespace,
        "name": np.metadata.name,
        "policy_types": list(np.spec.policy_types or []) if np.spec else [],
    }


def _serialize_configmap(cm: Any) -> dict[str, Any]:
    return {
        "namespace": cm.metadata.namespace,
        "name": cm.metadata.name,
        "keys_count": len(cm.data or {}),
    }


def _serialize_secret_meta(secret: Any) -> dict[str, Any]:
    return {
        "namespace": secret.metadata.namespace,
        "name": secret.metadata.name,
        "type": secret.type,
        "keys_count": len(secret.data or {}),
    }


async def collect_upgrade_discovery(
    connector: ClusterConnector,
) -> dict[str, Any]:
    """Discover cluster resources needed for upgrade analysis — metadata only."""
    api = connector.get_api_client()
    core = api.CoreV1Api()
    apps = api.AppsV1Api()
    batch = api.BatchV1Api()
    networking = api.NetworkingV1Api()
    policy = api.PolicyV1Api()
    storage = api.StorageV1Api()
    admission = api.AdmissionregistrationV1Api()
    apiext = api.ApiextensionsV1Api()
    rbac = api.RbacAuthorizationV1Api()
    scheduling = api.SchedulingV1Api()

    crds = _safe_list(lambda: apiext.list_custom_resource_definition(), "crds")
    validating_wh = _safe_list(
        lambda: admission.list_validating_webhook_configuration(), "validating_webhooks"
    )
    mutating_wh = _safe_list(
        lambda: admission.list_mutating_webhook_configuration(), "mutating_webhooks"
    )

    statefulsets = _safe_list(
        lambda: apps.list_stateful_set_for_all_namespaces(), "statefulsets"
    )
    daemonsets = _safe_list(
        lambda: apps.list_daemon_set_for_all_namespaces(), "daemonsets"
    )
    jobs = _safe_list(lambda: batch.list_job_for_all_namespaces(), "jobs")
    cronjobs = _safe_list(lambda: batch.list_cron_job_for_all_namespaces(), "cronjobs")
    pdbs = _safe_list(
        lambda: policy.list_pod_disruption_budget_for_all_namespaces(), "pdbs"
    )
    storage_classes = _safe_list(lambda: storage.list_storage_class(), "storage_classes")
    pvs = _safe_list(lambda: core.list_persistent_volume(), "pvs")
    pvcs = _safe_list(
        lambda: core.list_persistent_volume_claim_for_all_namespaces(), "pvcs"
    )
    netpols = _safe_list(
        lambda: networking.list_network_policy_for_all_namespaces(), "network_policies"
    )
    priority_classes = _safe_list(
        lambda: scheduling.list_priority_class(), "priority_classes"
    )
    configmaps = _safe_list(
        lambda: core.list_config_map_for_all_namespaces(), "configmaps"
    )
    secrets = _safe_list(lambda: core.list_secret_for_all_namespaces(), "secrets")
    deployments = _safe_list(
        lambda: apps.list_deployment_for_all_namespaces(), "deployments"
    )
    ingresses = _safe_list(
        lambda: networking.list_ingress_for_all_namespaces(), "ingresses"
    )
    services = _safe_list(
        lambda: core.list_service_for_all_namespaces(), "services"
    )

    # Count CRD instances (best-effort, capped)
    crd_data = [_serialize_crd(c) for c in crds]
    custom = api.CustomObjectsApi()
    for crd in crd_data[:50]:
        group = crd["group"]
        version = crd["storage_version"] or (crd["served_versions"][0] if crd["served_versions"] else None)
        plural = crd["name"]
        if not version:
            continue
        try:
            if crd.get("scope") == "Cluster":
                resp = custom.list_cluster_custom_object(group, version, plural, _request_timeout=10)
            else:
                resp = custom.list_cluster_custom_object(group, version, plural, _request_timeout=10)
            crd["instance_count"] = len(resp.get("items", []))
        except Exception:
            crd["instance_count"] = 0

    api_resources: list[dict[str, Any]] = []
    api_resources.extend(
        _serialize_workload(d, "Deployment", "apps/v1") for d in deployments
    )
    api_resources.extend(
        _serialize_workload(s, "StatefulSet", "apps/v1") for s in statefulsets
    )
    api_resources.extend(
        _serialize_workload(d, "DaemonSet", "apps/v1") for d in daemonsets
    )
    api_resources.extend(
        _serialize_workload(j, "Job", "batch/v1") for j in jobs
    )
    api_resources.extend(
        _serialize_workload(c, "CronJob", "batch/v1") for c in cronjobs
    )
    for ing in ingresses:
        api_resources.append({
            "api_version": ing.api_version or "networking.k8s.io/v1",
            "kind": "Ingress",
            "namespace": ing.metadata.namespace,
            "name": ing.metadata.name,
        })
    for pdb in pdbs:
        api_resources.append(_serialize_pdb(pdb))

    webhooks = []
    for wh in validating_wh:
        for hook in wh.webhooks or []:
            webhooks.append(_serialize_webhook(hook, "Validating"))
    for wh in mutating_wh:
        for hook in wh.webhooks or []:
            webhooks.append(_serialize_webhook(hook, "Mutating"))

    # RBAC summary (counts only)
    try:
        roles = rbac.list_role_for_all_namespaces(_request_timeout=15).items
        cluster_roles = rbac.list_cluster_role(_request_timeout=15).items
        role_bindings = rbac.list_role_binding_for_all_namespaces(_request_timeout=15).items
        cluster_role_bindings = rbac.list_cluster_role_binding(_request_timeout=15).items
        rbac_summary = {
            "roles": len(roles),
            "cluster_roles": len(cluster_roles),
            "role_bindings": len(role_bindings),
            "cluster_role_bindings": len(cluster_role_bindings),
        }
    except Exception:
        rbac_summary = {"roles": 0, "cluster_roles": 0, "role_bindings": 0, "cluster_role_bindings": 0}

    return {
        "crds": crd_data,
        "webhooks": webhooks,
        "workloads": {
            "deployments": len(deployments),
            "statefulsets": len(statefulsets),
            "daemonsets": len(daemonsets),
            "jobs": len(jobs),
            "cronjobs": len(cronjobs),
        },
        "api_resources": api_resources,
        "pdbs": [_serialize_pdb(p) for p in pdbs],
        "storage_classes": [_serialize_storage_class(s) for s in storage_classes],
        "persistent_volumes": [_serialize_pv(p) for p in pvs[:100]],
        "persistent_volume_claims": [_serialize_pvc(p) for p in pvcs[:200]],
        "network_policies": [_serialize_network_policy(n) for n in netpols],
        "priority_classes": [pc.metadata.name for pc in priority_classes],
        "configmaps_metadata": [_serialize_configmap(c) for c in configmaps[:200]],
        "secrets_metadata": [_serialize_secret_meta(s) for s in secrets[:200]],
        "services_count": len(services),
        "ingress_count": len(ingresses),
        "rbac": rbac_summary,
    }
