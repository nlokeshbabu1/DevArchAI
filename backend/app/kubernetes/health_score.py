"""Evidence-based cluster health scoring."""

from __future__ import annotations

from typing import Any

from app.kubernetes.types import ClusterOverview


def compute_health_score(
    *,
    overview: ClusterOverview,
    security_findings: list[dict[str, Any]],
    version_advisor: dict[str, Any],
    connection_status: str,
) -> dict[str, Any]:
    """Compute transparent sub-scores with evidence — no arbitrary numbers."""
    evidence: dict[str, list[str]] = {
        "availability": [],
        "security": [],
        "reliability": [],
        "resources": [],
        "configuration": [],
        "version": [],
    }

    # Availability
    if overview.nodes_total == 0:
        avail = 0
        evidence["availability"].append("No nodes detected")
    else:
        ready_ratio = overview.nodes_ready / overview.nodes_total
        avail = round(ready_ratio * 100)
        if overview.nodes_not_ready:
            evidence["availability"].append(f"{overview.nodes_not_ready} node(s) NotReady")

    # Security
    high = sum(1 for f in security_findings if f.get("severity") == "high")
    medium = sum(1 for f in security_findings if f.get("severity") == "medium")
    security_penalty = min(high * 8 + medium * 3, 60)
    security = max(100 - security_penalty, 0)
    if high:
        evidence["security"].append(f"{high} high-severity finding(s)")
    if medium:
        evidence["security"].append(f"{medium} medium-severity finding(s)")

    # Reliability
    rel_penalty = 0
    if overview.pods_failed:
        rel_penalty += min(overview.pods_failed * 5, 30)
        evidence["reliability"].append(f"{overview.pods_failed} failed pod(s)")
    if overview.pods_crash_loop:
        rel_penalty += min(overview.pods_crash_loop * 8, 40)
        evidence["reliability"].append(f"{overview.pods_crash_loop} CrashLoopBackOff pod(s)")
    if overview.deployments_degraded:
        rel_penalty += min(overview.deployments_degraded * 5, 25)
        evidence["reliability"].append(f"{overview.deployments_degraded} degraded deployment(s)")
    reliability = max(100 - rel_penalty, 0)

    # Resources
    missing_limits = sum(1 for f in security_findings if f.get("rule_id") == "K8S-SCALE-002")
    resource_penalty = min(missing_limits * 2, 40)
    resources = max(100 - resource_penalty, 0)
    if missing_limits:
        evidence["resources"].append(f"{missing_limits} container(s) missing limits")

    # Configuration
    missing_probes = sum(1 for f in security_findings if f.get("rule_id") == "K8S-REL-001")
    config_penalty = min(missing_probes * 3, 35)
    configuration = max(100 - config_penalty, 0)
    if missing_probes:
        evidence["configuration"].append(f"{missing_probes} container(s) missing probes")

    # Version
    upgrade_status = version_advisor.get("upgrade_status", "unknown")
    if upgrade_status == "upgrade_recommended":
        version_score = 72
        evidence["version"].append(version_advisor.get("impact_summary", "Upgrade recommended"))
    elif upgrade_status == "supported":
        version_score = 95
    elif upgrade_status == "end_of_life":
        version_score = 40
        evidence["version"].append("Version is end-of-life")
    else:
        version_score = 80

    if connection_status in ("degraded", "permission_denied"):
        avail = min(avail, 70)
        evidence["availability"].append(f"Connection status: {connection_status}")

    sub_scores = {
        "availability": avail,
        "security": security,
        "reliability": reliability,
        "resources": resources,
        "configuration": configuration,
        "version": version_score,
    }
    overall = round(sum(sub_scores.values()) / len(sub_scores))

    return {
        "overall": overall,
        "sub_scores": sub_scores,
        "evidence": evidence,
    }
