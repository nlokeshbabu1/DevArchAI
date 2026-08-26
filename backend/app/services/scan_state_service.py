"""Build authoritative scan state snapshots from PostgreSQL."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.scan import Scan, ScanStatus
from app.services.scan_lifecycle import format_technology_label, lifecycle_stage_for_internal
from app.services.technology_classifier import classify_technology

SEVERITY_BUCKETS = ("critical", "high", "medium", "low", "info")


def _severity_key(finding: Finding) -> str:
    sev = finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)
    return (sev or "info").lower()


def _detect_finding_technology(finding: Finding) -> str:
    return classify_technology(finding.file_path, getattr(finding, "scanner_name", None))


def _technology_icon(tech_id: str) -> str:
    return tech_id.replace("_", "-")


def _technologies_from_stack(scan: Scan) -> list[str]:
    detected: list[str] = []
    stack = scan.detected_stack
    if not stack:
        return detected
    if isinstance(stack, dict):
        if stack.get("detected_stack"):
            return list(stack.get("detected_stack") or [])
        from app.workers.tasks.scan_repository import DetectedTechnologyStack

        obj = DetectedTechnologyStack()
        for key, value in stack.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        return obj.get_detected_technologies()
    if isinstance(stack, list):
        return stack
    return detected


def _map_public_stage(scan: Scan) -> str | None:
    if scan.current_stage:
        lifecycle = lifecycle_stage_for_internal(scan.current_stage)
        if lifecycle:
            return lifecycle.value
        return scan.current_stage.value
    if scan.status == ScanStatus.COMPLETED:
        return "scan_completed"
    if scan.status == ScanStatus.FAILED:
        return "failed"
    if scan.status == ScanStatus.CANCELLED:
        return "cancelled"
    if scan.status == ScanStatus.QUEUED:
        return "queued"
    return None


def _aggregate_findings(findings: list[Finding]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    severity_counts = {bucket: 0 for bucket in SEVERITY_BUCKETS}
    tech_map: dict[str, dict[str, Any]] = {}

    for finding in findings:
        sev = _severity_key(finding)
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        tech = _detect_finding_technology(finding)
        if tech in ("code", "secrets", "dependencies"):
            continue
        if tech not in tech_map:
            tech_map[tech] = {
                "id": tech,
                "name": format_technology_label(tech),
                "icon": _technology_icon(tech),
                "status": "detected",
                "findings": 0,
                "severity_counts": {k: 0 for k in SEVERITY_BUCKETS},
            }
        tech_map[tech]["findings"] += 1
        tech_map[tech]["severity_counts"][sev] = tech_map[tech]["severity_counts"].get(sev, 0) + 1

    return severity_counts, list(tech_map.values())


def build_scan_state_snapshot_sync(scan: Scan, findings: list[Finding] | None = None) -> dict[str, Any]:
    """Build scan state dict from ORM objects (sync session)."""
    findings = findings or []
    severity_counts, technology_results = _aggregate_findings(findings)

    # During in-flight scans, include detected technologies even before findings exist
    for tech_id in _technologies_from_stack(scan):
        if not any(t["id"] == tech_id for t in technology_results):
            technology_results.append(
                {
                    "id": tech_id,
                    "name": format_technology_label(tech_id),
                    "icon": _technology_icon(tech_id),
                    "status": "detected",
                    "findings": 0,
                    "severity_counts": {k: 0 for k in SEVERITY_BUCKETS},
                }
            )

    is_terminal = scan.status in (ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED)
    stage = _map_public_stage(scan)
    if is_terminal and scan.status == ScanStatus.COMPLETED:
        progress = 100
    elif scan.progress is not None:
        progress = scan.progress
    else:
        progress = None

    return {
        "event": "scan_state",
        "scan_id": str(scan.id),
        "status": scan.status.value,
        "stage": stage,
        "progress": progress,
        "message": scan.error_message or (f"Scan {scan.status.value}" if is_terminal else stage or "running"),
        "current_operation": stage,
        "is_terminal": is_terminal,
        "error_message": scan.error_message,
        "repository_url": scan.repository_url,
        "branch": scan.branch,
        "detected_stack": [t["id"] for t in technology_results],
        "technologies": technology_results,
        "technology_results": technology_results,
        "severity_counts": severity_counts,
        "findings_count": sum(severity_counts.values()),
        "technologies_count": len(technology_results),
        "ai_status": scan.ai_status,
        "ai_error_message": scan.ai_error_message,
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "ai_completed_at": scan.ai_completed_at.isoformat() if scan.ai_completed_at else None,
        "overall_score": scan.overall_score,
        "created_at": scan.created_at.isoformat(),
    }


async def build_scan_state_snapshot_async(db: AsyncSession, scan_id: str) -> dict[str, Any] | None:
    """Load scan + findings from DB and return authoritative state."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        return None

    findings_result = await db.execute(select(Finding).where(Finding.scan_id == scan_id))
    findings = findings_result.scalars().all()
    return build_scan_state_snapshot_sync(scan, list(findings))
