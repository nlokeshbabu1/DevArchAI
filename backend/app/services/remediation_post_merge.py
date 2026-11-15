"""
Post-merge remediation verification (compare scans / finding resolution).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.pull_request import PRStatus, PullRequest
from app.models.scan import Scan

logger = structlog.get_logger(__name__)


async def verify_post_merge_remediation(
    db: AsyncSession,
    *,
    pr_id: UUID,
    user_id: UUID,
    rescan_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Compare original scan findings to a post-merge scan (when provided).

    Does not claim issues are fixed without scanner evidence.
    """
    pr_result = await db.execute(
        select(PullRequest).where(PullRequest.id == pr_id, PullRequest.user_id == user_id)
    )
    pr = pr_result.scalar_one_or_none()
    if not pr:
        return {"success": False, "error": "Pull request not found or access denied"}

    scan_result = await db.execute(select(Scan).where(Scan.id == pr.scan_id))
    original_scan = scan_result.scalar_one_or_none()
    if not original_scan:
        return {"success": False, "error": "Original scan not found"}

    fixed_ids = set(pr.findings_fixed or [])
    original_findings: dict[str, Finding] = {}
    if fixed_ids:
        original_findings_result = await db.execute(
            select(Finding).where(Finding.scan_id == pr.scan_id, Finding.id.in_(fixed_ids))
        )
        original_findings = {str(f.id): f for f in original_findings_result.scalars().all()}

    report: dict[str, Any] = {
        "success": True,
        "pr_id": str(pr.id),
        "pr_status": pr.status.value if hasattr(pr.status, "value") else str(pr.status),
        "original_scan_id": str(pr.scan_id),
        "findings_targeted": list(fixed_ids),
        "verification_scan_id": str(rescan_id) if rescan_id else None,
        "resolved_finding_ids": [],
        "still_open_finding_ids": [],
        "new_finding_ids": [],
        "note": (
            "Patch application is not proof of resolution. "
            "Provide rescan_id after merge for evidence-based comparison."
        ),
    }

    if pr.status != PRStatus.MERGED:
        report["note"] = "PR is not merged yet; schedule a rescan after merge for verification."
        return report

    if not rescan_id:
        return report

    rescan_result = await db.execute(
        select(Scan).where(Scan.id == rescan_id, Scan.user_id == user_id)
    )
    rescan = rescan_result.scalar_one_or_none()
    if not rescan:
        report["success"] = False
        report["error"] = "Verification scan not found"
        return report

    new_findings_result = await db.execute(select(Finding).where(Finding.scan_id == rescan_id))
    new_findings = list(new_findings_result.scalars().all())

    def fingerprint(f: Finding) -> str:
        return "|".join(
            [
                str(f.rule_id or ""),
                str(f.file_path or ""),
                str(f.line_number or ""),
                str(f.resource or ""),
            ]
        )

    new_fps = {fingerprint(f): str(f.id) for f in new_findings}

    for fid in fixed_ids:
        orig = original_findings.get(fid)
        if not orig:
            continue
        fp = fingerprint(orig)
        if fp not in new_fps:
            report["resolved_finding_ids"].append(fid)
        else:
            report["still_open_finding_ids"].append(fid)

    targeted_fps = {fingerprint(original_findings[fid]) for fid in fixed_ids if fid in original_findings}
    for fp, new_id in new_fps.items():
        if fp not in targeted_fps:
            continue
        if new_id not in report["still_open_finding_ids"]:
            report["new_finding_ids"].append(new_id)

    report["note"] = "Comparison uses rule_id, file_path, line_number, and resource fingerprints."
    return report
