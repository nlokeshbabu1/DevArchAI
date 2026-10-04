"""CRD compatibility analysis for Kubernetes upgrades."""

from __future__ import annotations

from typing import Any

from app.kubernetes.api_compatibility import _parse_minor


def _crd_risk_level(
    *,
    served_versions: list[str],
    storage_version: str | None,
    conversion_strategy: str | None,
    instance_count: int,
    target_version: str,
) -> tuple[str, str]:
    """Return (risk_level, reason)."""
    target = _parse_minor(target_version)
    if not target:
        return "warning", "Unable to parse target Kubernetes version"

    # Beta/alpha API versions in CRDs are higher risk
    beta_versions = [v for v in served_versions if "beta" in v or "alpha" in v]
    if beta_versions:
        return (
            "high",
            f"CRD serves beta/alpha versions: {', '.join(beta_versions)}",
        )

    if conversion_strategy == "None" and len(served_versions) > 1:
        return (
            "warning",
            "Multiple served versions without conversion webhook",
        )

    if instance_count > 0 and storage_version and "v1beta" in storage_version:
        return (
            "high",
            f"Storage version {storage_version} may require migration before {target_version}",
        )

    if instance_count == 0:
        return "compatible", "No instances detected"

    return "compatible", "CRD appears compatible with target version"


def analyze_crds(
    crds: list[dict[str, Any]],
    *,
    target_version: str,
    instance_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Analyze CRD compatibility for upgrade."""
    counts = instance_counts or {}
    analyzed: list[dict[str, Any]] = []
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for crd in crds:
        name = crd.get("name", "")
        group = crd.get("group", "")
        served = crd.get("served_versions") or []
        storage = crd.get("storage_version")
        conversion = crd.get("conversion_strategy")
        instances = counts.get(name, crd.get("instance_count", 0))

        risk, reason = _crd_risk_level(
            served_versions=served,
            storage_version=storage,
            conversion_strategy=conversion,
            instance_count=instances,
            target_version=target_version,
        )

        entry = {
            "name": name,
            "group": group,
            "versions": crd.get("versions", []),
            "served_versions": served,
            "storage_version": storage,
            "conversion_strategy": conversion,
            "instance_count": instances,
            "controller": crd.get("controller"),
            "risk": risk,
            "reason": reason,
            "recommended_action": (
                "Update CRD and operator before upgrade"
                if risk in ("high", "blocking")
                else "Review during upgrade validation"
            ),
        }
        analyzed.append(entry)

        if risk == "blocking":
            blocking.append(entry)
        elif risk in ("high", "warning"):
            warnings.append(entry)

    return {
        "crds": analyzed,
        "total": len(analyzed),
        "blocking": blocking,
        "warnings": warnings,
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "high_risk_count": sum(1 for c in analyzed if c["risk"] == "high"),
    }
