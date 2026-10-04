"""Kubernetes version advisor."""

from __future__ import annotations

from typing import Any

# Supported upstream Kubernetes versions (minor releases).
SUPPORTED_VERSIONS = ["1.29", "1.30", "1.31", "1.32", "1.33", "1.34"]
LATEST_SUPPORTED = "1.34"

DEPRECATED_APIS: dict[str, dict[str, Any]] = {
    "batch/v1beta1/CronJob": {
        "removed_in": "1.25",
        "replacement": "batch/v1/CronJob",
        "impact": "medium",
    },
    "policy/v1beta1/PodDisruptionBudget": {
        "removed_in": "1.25",
        "replacement": "policy/v1/PodDisruptionBudget",
        "impact": "medium",
    },
    "networking.k8s.io/v1beta1/Ingress": {
        "removed_in": "1.22",
        "replacement": "networking.k8s.io/v1/Ingress",
        "impact": "low",
    },
}


def _parse_minor(version: str) -> tuple[int, int] | None:
    cleaned = version.lstrip("v").strip()
    parts = cleaned.split(".")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def build_version_advisor(
    current_version: str,
    *,
    provider: str,
    kind: str,
    region: str | None = None,
) -> dict[str, Any]:
    """Build version upgrade guidance with evidence."""
    minor = _parse_minor(current_version)
    latest = _parse_minor(LATEST_SUPPORTED)

    if not minor or not latest:
        return {
            "current_version": current_version,
            "latest_supported": f"v{LATEST_SUPPORTED}",
            "upgrade_status": "unknown",
            "upgrade_available": "NO",
            "recommended_version": f"v{LATEST_SUPPORTED}",
            "impact_summary": "Unable to determine version",
            "deprecated_apis": [],
            "upgrade_path": [],
            "provider_notes": [],
        }

    current_str = f"{minor[0]}.{minor[1]}"
    behind = minor[1] < latest[1] or minor[0] < latest[0]
    steps_behind = max(0, latest[1] - minor[1]) if behind else 0

    deprecated = []
    for api, info in DEPRECATED_APIS.items():
        removed = _parse_minor(info["removed_in"])
        if removed and (minor[0], minor[1]) <= removed:
            deprecated.append({"api": api, **info})

    if behind:
        upgrade_status = "upgrade_recommended"
        upgrade_available = "YES"
        impact_parts = []
        if deprecated:
            impact_parts.append(f"MEDIUM - {len(deprecated)} deprecated APIs")
        if steps_behind >= 2:
            impact_parts.insert(0, f"HIGH - {steps_behind} minor versions behind")
        impact_summary = "; ".join(impact_parts) if impact_parts else "Upgrade recommended"
    elif current_str in SUPPORTED_VERSIONS:
        upgrade_status = "supported"
        upgrade_available = "NO"
        impact_summary = "Cluster version is within supported range"
    else:
        upgrade_status = "end_of_life"
        upgrade_available = "YES"
        impact_summary = "Version may be end-of-life"

    upgrade_path = []
    if behind:
        for v in SUPPORTED_VERSIONS:
            v_minor = _parse_minor(v)
            if v_minor and v_minor > minor:
                upgrade_path.append(f"v{v}")

    provider_notes = []
    if kind == "eks":
        provider_notes.append(
            f"For EKS in {region or 'your region'}, verify cluster upgrade order via AWS EKS console."
        )

    readiness_score = 100
    if behind:
        readiness_score -= min(30, steps_behind * 6) if steps_behind >= 2 else 10
    readiness_score -= len(deprecated) * 8
    readiness_score = max(0, min(100, readiness_score))

    risk = "low"
    if deprecated and behind:
        risk = "high" if steps_behind >= 2 else "medium"
    elif behind:
        risk = "medium"

    return {
        "current_version": f"v{current_str}",
        "latest_supported": f"v{LATEST_SUPPORTED}",
        "recommended_version": f"v{LATEST_SUPPORTED}",
        "upgrade_status": upgrade_status,
        "upgrade_available": upgrade_available,
        "impact_summary": impact_summary,
        "readiness_score": readiness_score,
        "risk": risk,
        "blocking_issues": [],
        "warnings": deprecated,
        "deprecated_apis": deprecated,
        "crd_issues": None,
        "workload_issues": [],
        "what_changes": [
            "Security patches and CVE fixes",
            "API deprecations and removals",
            "Admission and networking behavior updates",
        ],
        "why_upgrade": [
            "Stay within vendor support windows",
            "Receive security patches",
            "Avoid deprecated API breakage",
        ],
        "what_could_break": [d["api"] for d in deprecated],
        "what_to_test": [
            "Critical workloads after control plane upgrade",
            "Ingress and networking policies",
            "Batch jobs and CronJobs",
            "Custom resource definitions using deprecated APIs",
        ],
        "recommended_sequence": upgrade_path[:5],
        "upgrade_path_versions": upgrade_path[:5],
        "provider_notes": provider_notes,
        "analysis_required": True,
    }
