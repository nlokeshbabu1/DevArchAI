"""Kubernetes Upgrade Readiness & Impact Analyzer — deterministic engine."""

from __future__ import annotations

from typing import Any

from app.kubernetes.api_compatibility import analyze_api_compatibility, scan_resource_api_versions
from app.kubernetes.crd_analyzer import analyze_crds
from app.kubernetes.version_advisor import LATEST_SUPPORTED, SUPPORTED_VERSIONS, _parse_minor, build_version_advisor


def _minor_versions_between(current: str, target: str) -> list[str]:
    cur = _parse_minor(current)
    tgt = _parse_minor(target)
    if not cur or not tgt:
        return []
    path = []
    for v in SUPPORTED_VERSIONS:
        minor = _parse_minor(v)
        if minor and cur < minor <= tgt:
            path.append(f"v{v}")
    return path


def _compute_readiness_score(
    *,
    blocking_count: int,
    warning_count: int,
    deprecated_count: int,
    crd_high_risk: int,
    versions_behind: int,
) -> int:
    score = 100
    score -= blocking_count * 25
    score -= warning_count * 8
    score -= deprecated_count * 5
    score -= crd_high_risk * 10
    score -= versions_behind * 3
    return max(0, min(100, score))


def _risk_level(score: int, blocking_count: int) -> str:
    if blocking_count > 0:
        return "blocking"
    if score < 50:
        return "high"
    if score < 75:
        return "medium"
    return "low"


def _analyze_step(
    from_version: str,
    to_version: str,
    api_resources: list[dict[str, Any]],
    crds: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyze a single upgrade step."""
    api_scan = scan_resource_api_versions(api_resources)
    api_compat = analyze_api_compatibility(
        current_version=from_version,
        target_version=to_version,
        discovered_apis=api_scan,
    )
    crd_analysis = analyze_crds(crds, target_version=to_version)

    blocking = api_compat["blocking"] + crd_analysis["blocking"]
    warnings = api_compat["warnings"] + crd_analysis["warnings"]

    if blocking:
        status = "blocking"
    elif warnings:
        status = "warning"
    else:
        status = "compatible"

    return {
        "from_version": from_version,
        "to_version": to_version,
        "status": status,
        "api_changes": {
            "deprecated": [a for a in api_compat["apis"] if a.get("compatibility") == "deprecated"],
            "removed": api_compat["blocking"],
            "compatible_count": api_compat.get("compatible_api_count", 0),
        },
        "deprecated_apis": api_compat["warnings"],
        "removed_apis": api_compat["blocking"],
        "crd_impact": crd_analysis,
        "workload_impact": {
            "affected_api_count": api_compat["blocking_count"] + api_compat["warning_count"],
        },
        "breaking_changes": [
            b.get("reason", b.get("migration", ""))
            for b in api_compat["blocking"]
        ],
        "recommended_remediation": [
            b.get("migration") for b in api_compat["blocking"] if b.get("migration")
        ] + [
            c.get("recommended_action") for c in crd_analysis["warnings"][:5]
        ],
    }


def build_what_could_break(
    *,
    api_compat: dict[str, Any],
    crd_analysis: dict[str, Any],
    discovery: dict[str, Any],
) -> dict[str, Any]:
    """Build 'What Could Break?' view."""
    categories = []

    if api_compat["blocking"]:
        categories.append({
            "category": "apis",
            "severity": "high",
            "affected_count": sum(a.get("affected_count", 0) for a in api_compat["blocking"]),
            "items": api_compat["blocking"][:20],
            "explanation": "Deprecated APIs removed in target version will break workloads",
            "recommended_action": "Migrate to supported API versions before upgrading",
        })

    if api_compat["warnings"]:
        categories.append({
            "category": "apis",
            "severity": "medium",
            "affected_count": sum(a.get("affected_count", 0) for a in api_compat["warnings"]),
            "items": api_compat["warnings"][:20],
            "explanation": "Deprecated APIs should be migrated during upgrade window",
            "recommended_action": "Plan API migrations for next maintenance window",
        })

    high_crds = [c for c in crd_analysis.get("crds", []) if c.get("risk") in ("high", "blocking")]
    if high_crds:
        categories.append({
            "category": "crds",
            "severity": "high",
            "affected_count": sum(c.get("instance_count", 0) for c in high_crds),
            "items": high_crds[:20],
            "explanation": "Custom resources may break if CRD versions are incompatible",
            "recommended_action": "Update CRDs and operators before control plane upgrade",
        })

    webhooks = discovery.get("webhooks", [])
    if webhooks:
        categories.append({
            "category": "webhooks",
            "severity": "medium",
            "affected_count": len(webhooks),
            "items": webhooks[:10],
            "explanation": "Admission webhooks must remain compatible with new API versions",
            "recommended_action": "Validate webhook configurations against target version",
        })

    workloads = discovery.get("workloads", {})
    degraded = workloads.get("deployments", 0)
    if degraded:
        categories.append({
            "category": "workloads",
            "severity": "medium",
            "affected_count": degraded,
            "items": [],
            "explanation": "Existing workload issues may worsen during upgrade",
            "recommended_action": "Resolve degraded workloads before upgrading",
        })

    ingress_count = discovery.get("ingress_count", 0)
    if ingress_count and api_compat["blocking"]:
        ingress_blocking = [
            a for a in api_compat["blocking"]
            if "Ingress" in a.get("kind", "")
        ]
        if ingress_blocking:
            categories.append({
                "category": "ingress",
                "severity": "high",
                "affected_count": sum(a.get("affected_count", 0) for a in ingress_blocking),
                "items": ingress_blocking,
                "explanation": "Ingress API changes can break external traffic routing",
                "recommended_action": "Migrate Ingress resources to networking.k8s.io/v1",
            })

    storage = discovery.get("persistent_volume_claims", [])
    if storage:
        categories.append({
            "category": "storage",
            "severity": "informational",
            "affected_count": len(storage),
            "items": storage[:10],
            "explanation": "Persistent volumes should be validated post-upgrade",
            "recommended_action": "Snapshot critical PVCs before upgrade",
        })

    netpols = discovery.get("network_policies", [])
    if netpols:
        categories.append({
            "category": "networking",
            "severity": "informational",
            "affected_count": len(netpols),
            "items": netpols[:10],
            "explanation": "Network policies should be re-validated after CNI upgrades",
            "recommended_action": "Test service connectivity after upgrade",
        })

    return {"categories": categories, "total_categories": len(categories)}


def build_upgrade_plan(
    *,
    blocking_apis: list[dict[str, Any]],
    crd_warnings: list[dict[str, Any]],
    upgrade_path: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate phased upgrade plan with checklist."""
    phases = []

    if blocking_apis:
        phases.append({
            "phase": 1,
            "title": "Fix deprecated APIs",
            "description": "Migrate resources using removed API versions",
            "checklist": [
                f"Migrate {a.get('api', 'API')} ({a.get('affected_count', 0)} resources)"
                for a in blocking_apis[:10]
            ],
            "blocking": True,
        })

    if crd_warnings:
        phases.append({
            "phase": len(phases) + 1,
            "title": "Update CRDs/operators",
            "description": "Ensure custom resources are compatible with target version",
            "checklist": [
                f"Update {c.get('name')} — {c.get('reason', '')}"
                for c in crd_warnings[:10]
            ],
            "blocking": any(c.get("risk") == "blocking" for c in crd_warnings),
        })

    phases.append({
        "phase": len(phases) + 1,
        "title": "Validate workloads",
        "description": "Confirm critical workloads are healthy pre-upgrade",
        "checklist": [
            "Verify all deployments are ready",
            "Check pod disruption budgets",
            "Review pending/failed pods",
            "Validate ingress and service endpoints",
        ],
        "blocking": False,
    })

    upgrade_steps = [
        f"Upgrade control plane to {step['to_version']}"
        for step in upgrade_path
        if step.get("status") != "compatible" or True
    ]
    phases.append({
        "phase": len(phases) + 1,
        "title": "Upgrade Kubernetes",
        "description": "Perform sequential minor version upgrades",
        "checklist": upgrade_steps or [f"Upgrade to v{LATEST_SUPPORTED}"],
        "blocking": False,
    })

    phases.append({
        "phase": len(phases) + 1,
        "title": "Post-upgrade validation",
        "description": "Verify cluster health after upgrade",
        "checklist": [
            "Confirm all nodes are Ready",
            "Validate critical workloads",
            "Check admission webhooks",
            "Re-run upgrade readiness analysis",
            "Monitor events for 24 hours",
        ],
        "blocking": False,
    })

    return {"phases": phases, "total_phases": len(phases)}


def analyze_upgrade_readiness(
    *,
    current_version: str,
    target_version: str | None = None,
    discovery: dict[str, Any],
    provider: str = "generic",
    kind: str = "generic",
    region: str | None = None,
) -> dict[str, Any]:
    """Full deterministic upgrade readiness analysis."""
    target = target_version or f"v{LATEST_SUPPORTED}"
    base_advisor = build_version_advisor(
        current_version,
        provider=provider,
        kind=kind,
        region=region,
    )

    api_resources = discovery.get("api_resources", [])
    crds = discovery.get("crds", [])

    api_scan = scan_resource_api_versions(api_resources)
    api_compat = analyze_api_compatibility(
        current_version=current_version,
        target_version=target,
        discovered_apis=api_scan,
    )
    crd_analysis = analyze_crds(crds, target_version=target)

    path_versions = _minor_versions_between(current_version, target)
    if not path_versions:
        path_versions = base_advisor.get("recommended_sequence", [target])

    upgrade_path = []
    prev = current_version
    for step_ver in path_versions:
        step = _analyze_step(prev, step_ver, api_resources, crds)
        upgrade_path.append(step)
        prev = step_ver

    cur = _parse_minor(current_version)
    tgt = _parse_minor(target)
    versions_behind = (tgt[1] - cur[1]) if cur and tgt and tgt > cur else 0

    readiness_score = _compute_readiness_score(
        blocking_count=api_compat["blocking_count"] + crd_analysis["blocking_count"],
        warning_count=api_compat["warning_count"] + crd_analysis["warning_count"],
        deprecated_count=len(api_compat["warnings"]),
        crd_high_risk=crd_analysis["high_risk_count"],
        versions_behind=versions_behind,
    )

    risk = _risk_level(readiness_score, api_compat["blocking_count"] + crd_analysis["blocking_count"])
    what_could_break = build_what_could_break(
        api_compat=api_compat,
        crd_analysis=crd_analysis,
        discovery=discovery,
    )
    upgrade_plan = build_upgrade_plan(
        blocking_apis=api_compat["blocking"],
        crd_warnings=crd_analysis["warnings"] + crd_analysis["blocking"],
        upgrade_path=upgrade_path,
    )

    workload_issues = []
    for api in api_compat["blocking"] + api_compat["warnings"]:
        if api.get("affected_count", 0) > 0:
            workload_issues.append({
                "api": api.get("api"),
                "count": api.get("affected_count"),
                "severity": api.get("severity", "medium"),
                "resources": api.get("affected_resources", [])[:5],
            })

    return {
        "current_version": base_advisor["current_version"],
        "recommended_version": target if target.startswith("v") else f"v{target}",
        "readiness_score": readiness_score,
        "risk": risk,
        "upgrade_status": base_advisor["upgrade_status"],
        "impact_summary": base_advisor["impact_summary"],
        "blocking_issues": api_compat["blocking"] + crd_analysis["blocking"],
        "warnings": api_compat["warnings"] + crd_analysis["warnings"],
        "deprecated_apis": api_compat["warnings"],
        "crd_issues": crd_analysis,
        "workload_issues": workload_issues,
        "api_compatibility": api_compat,
        "upgrade_path": upgrade_path,
        "upgrade_path_versions": path_versions,
        "what_could_break": what_could_break,
        "upgrade_plan": upgrade_plan,
        "discovery_summary": {
            "crds": len(crds),
            "webhooks": len(discovery.get("webhooks", [])),
            "workloads": discovery.get("workloads", {}),
            "api_resources_scanned": len(api_resources),
        },
        "provider_notes": base_advisor.get("provider_notes", []),
        "analyzed_at": None,
    }


def explain_version_risk(
    upgrade_result: dict[str, Any],
    target_version: str,
) -> dict[str, Any]:
    """Explain risk for a specific target version in the upgrade path."""
    for step in upgrade_result.get("upgrade_path", []):
        if step.get("to_version") == target_version or step.get("to_version") == f"v{target_version.lstrip('v')}":
            return {
                "target_version": target_version,
                "status": step.get("status"),
                "risk": step.get("status"),
                "affected_resources": step.get("removed_apis", []) + step.get("deprecated_apis", []),
                "api_changes": step.get("api_changes"),
                "crd_impact": step.get("crd_impact"),
                "workload_impact": step.get("workload_impact"),
                "breaking_changes": step.get("breaking_changes", []),
                "recommended_remediation": step.get("recommended_remediation", []),
                "evidence": {
                    "deprecated_apis": len(step.get("deprecated_apis", [])),
                    "removed_apis": len(step.get("removed_apis", [])),
                    "crd_warnings": step.get("crd_impact", {}).get("warning_count", 0),
                },
            }
    return {"target_version": target_version, "status": "unknown", "evidence": {}}
