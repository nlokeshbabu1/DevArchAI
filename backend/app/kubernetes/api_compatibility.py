"""Kubernetes API compatibility engine — deterministic deprecated/removed API detection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

# apiVersion/kind -> removal info keyed by minor version when removed
API_REGISTRY: dict[str, dict[str, Any]] = {
    "extensions/v1beta1/Ingress": {
        "removed_in": "1.22",
        "replacement": "networking.k8s.io/v1/Ingress",
        "severity": "high",
        "migration": "Update Ingress manifests to networking.k8s.io/v1",
    },
    "networking.k8s.io/v1beta1/Ingress": {
        "removed_in": "1.22",
        "replacement": "networking.k8s.io/v1/Ingress",
        "severity": "high",
        "migration": "Update Ingress to networking.k8s.io/v1",
    },
    "batch/v1beta1/CronJob": {
        "removed_in": "1.25",
        "replacement": "batch/v1/CronJob",
        "severity": "medium",
        "migration": "Update CronJob to batch/v1",
    },
    "policy/v1beta1/PodDisruptionBudget": {
        "removed_in": "1.25",
        "replacement": "policy/v1/PodDisruptionBudget",
        "severity": "medium",
        "migration": "Update PDB to policy/v1",
    },
    "policy/v1beta1/PodSecurityPolicy": {
        "removed_in": "1.25",
        "replacement": "Pod Security Admission / PSA labels",
        "severity": "high",
        "migration": "Migrate to Pod Security Standards",
    },
    "apps/v1beta1/Deployment": {
        "removed_in": "1.16",
        "replacement": "apps/v1/Deployment",
        "severity": "high",
        "migration": "Update to apps/v1",
    },
    "apps/v1beta2/Deployment": {
        "removed_in": "1.16",
        "replacement": "apps/v1/Deployment",
        "severity": "high",
        "migration": "Update to apps/v1",
    },
    "apps/v1beta1/StatefulSet": {
        "removed_in": "1.16",
        "replacement": "apps/v1/StatefulSet",
        "severity": "high",
        "migration": "Update to apps/v1",
    },
    "apps/v1beta1/DaemonSet": {
        "removed_in": "1.16",
        "replacement": "apps/v1/DaemonSet",
        "severity": "high",
        "migration": "Update to apps/v1",
    },
    "autoscaling/v2beta1/HorizontalPodAutoscaler": {
        "removed_in": "1.25",
        "replacement": "autoscaling/v2/HorizontalPodAutoscaler",
        "severity": "medium",
        "migration": "Update HPA to autoscaling/v2",
    },
    "autoscaling/v2beta2/HorizontalPodAutoscaler": {
        "removed_in": "1.26",
        "replacement": "autoscaling/v2/HorizontalPodAutoscaler",
        "severity": "medium",
        "migration": "Update HPA to autoscaling/v2",
    },
    "discovery.k8s.io/v1beta1/EndpointSlice": {
        "removed_in": "1.21",
        "replacement": "discovery.k8s.io/v1/EndpointSlice",
        "severity": "low",
        "migration": "Update EndpointSlice to v1",
    },
    "node.k8s.io/v1beta1/RuntimeClass": {
        "removed_in": "1.25",
        "replacement": "node.k8s.io/v1/RuntimeClass",
        "severity": "low",
        "migration": "Update RuntimeClass to v1",
    },
    "flowcontrol.apiserver.k8s.io/v1beta1/FlowSchema": {
        "removed_in": "1.29",
        "replacement": "flowcontrol.apiserver.k8s.io/v1/FlowSchema",
        "severity": "low",
        "migration": "Update FlowSchema to v1",
    },
    "flowcontrol.apiserver.k8s.io/v1beta2/FlowSchema": {
        "removed_in": "1.29",
        "replacement": "flowcontrol.apiserver.k8s.io/v1/FlowSchema",
        "severity": "low",
        "migration": "Update FlowSchema to v1",
    },
    "flowcontrol.apiserver.k8s.io/v1beta3/FlowSchema": {
        "removed_in": "1.32",
        "replacement": "flowcontrol.apiserver.k8s.io/v1/FlowSchema",
        "severity": "low",
        "migration": "Update FlowSchema to v1",
    },
}


def _parse_minor(version: str) -> tuple[int, int] | None:
    cleaned = str(version).lstrip("v").strip()
    parts = cleaned.split(".")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _api_key(api_version: str, kind: str) -> str:
    return f"{api_version}/{kind}"


def scan_resource_api_versions(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Scan serialized resources for apiVersion/kind usage."""
    counts: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "resources": []})
    for res in resources:
        api_version = res.get("api_version") or res.get("apiVersion")
        kind = res.get("kind")
        if not api_version or not kind:
            continue
        key = _api_key(api_version, kind)
        counts[key]["count"] += 1
        if len(counts[key]["resources"]) < 10:
            counts[key]["resources"].append({
                "namespace": res.get("namespace"),
                "name": res.get("name"),
            })
    findings = []
    for key, data in counts.items():
        info = API_REGISTRY.get(key, {})
        findings.append({
            "api": key,
            "api_version": key.split("/")[0],
            "kind": key.split("/")[1] if "/" in key else "",
            "affected_count": data["count"],
            "affected_resources": data["resources"],
            "deprecated": bool(info),
            "removed_in": info.get("removed_in"),
            "replacement": info.get("replacement"),
            "severity": info.get("severity", "informational"),
            "migration": info.get("migration"),
        })
    return sorted(findings, key=lambda x: -x["affected_count"])


def analyze_api_compatibility(
    *,
    current_version: str,
    target_version: str,
    discovered_apis: list[dict[str, Any]],
) -> dict[str, Any]:
    """Determine API compatibility for upgrade from current to target."""
    current = _parse_minor(current_version)
    target = _parse_minor(target_version)
    if not current or not target:
        return {"compatible": False, "blocking": [], "warnings": [], "apis": discovered_apis}

    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    compatible_count = 0

    for api in discovered_apis:
        key = api.get("api", "")
        info = API_REGISTRY.get(key, {})
        if not info:
            compatible_count += 1
            api["compatibility"] = "compatible"
            api["target_compatibility"] = "compatible"
            continue

        removed = _parse_minor(info["removed_in"])
        api["replacement"] = info.get("replacement")
        api["migration"] = info.get("migration")

        if removed and target >= removed:
            api["compatibility"] = "removed"
            api["target_compatibility"] = "blocking"
            entry = {**api, "reason": f"Removed in Kubernetes {info['removed_in']}"}
            if api.get("affected_count", 0) > 0:
                blocking.append(entry)
            else:
                warnings.append({**entry, "reason": "API deprecated but no in-cluster instances detected"})
        elif removed and current < removed <= target:
            api["compatibility"] = "deprecated"
            api["target_compatibility"] = "warning"
            warnings.append({
                **api,
                "reason": f"Deprecated; removed in {info['removed_in']}",
            })
        else:
            api["compatibility"] = "compatible"
            api["target_compatibility"] = "compatible"
            compatible_count += 1

    return {
        "compatible": len(blocking) == 0,
        "blocking": blocking,
        "warnings": warnings,
        "apis": discovered_apis,
        "compatible_api_count": compatible_count,
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
    }
