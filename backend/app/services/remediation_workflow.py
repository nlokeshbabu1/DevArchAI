"""
Universal remediation workflow — single pipeline for discovery, patches, validation, and PR prep.

Reuses remediation_patch reconciliation and GitHubPRService for Git operations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from git import Repo

from app.services.github_pr import (
    FixApplicationError,
    normalize_path,
    resolve_file_path,
)
from app.services.remediation_discovery import (
    discover_repository,
    read_repo_file,
    related_files_for_path,
)
from app.services.remediation_patch import (
    PatchValidationError,
    file_content_hash,
    reconcile_file_patches,
)
from app.services.remediation_patch_generator import (
    generate_unified_diff_patch,
    resolve_existing_patch_payload,
)
from app.services.remediation_validators import run_validators

logger = structlog.get_logger(__name__)


class RemediationAtomicFailure(FixApplicationError):
    """Raised when atomic remediation cannot apply all selected findings safely."""


@dataclass
class FindingOutcome:
    finding_id: str
    rule_id: str | None
    file_path: str | None
    status: str  # ready | rejected | manual_required | skipped
    reason: str = ""
    unified_diff: str | None = None
    validation: list[dict[str, Any]] = field(default_factory=list)
    manual_guidance: str = ""
    assumptions: list[str] = field(default_factory=list)
    breaking_changes: list[str] = field(default_factory=list)
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "file_path": self.file_path,
            "status": self.status,
            "reason": self.reason,
            "manual_guidance": self.manual_guidance,
            "validation": self.validation,
            "assumptions": self.assumptions,
            "breaking_changes": self.breaking_changes,
            "confidence": self.confidence,
            "has_unified_diff": bool(self.unified_diff),
        }


@dataclass
class RemediationPlan:
    base_commit_sha: str
    branch: str
    discovery: dict[str, Any]
    fixes: list[dict[str, Any]]
    outcomes: list[FindingOutcome]
    file_changes: dict[str, dict[str, Any]]
    atomic_ok: bool
    atomic_mode: bool
    selected_finding_ids: list[str]

    def to_report(self) -> dict[str, Any]:
        return {
            "base_commit_sha": self.base_commit_sha,
            "branch": self.branch,
            "atomic_mode": self.atomic_mode,
            "atomic_ok": self.atomic_ok,
            "discovery": self.discovery,
            "selected_finding_ids": self.selected_finding_ids,
            "outcomes": [o.to_dict() for o in self.outcomes],
            "files_modified": sorted(self.file_changes.keys()),
            "file_changes": self.file_changes,
        }


def _finding_to_dict(finding: Any) -> dict[str, Any]:
    meta = getattr(finding, "processing_metadata", None)
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            meta = {}
    return {
        "finding_id": str(getattr(finding, "id", "")),
        "rule_id": getattr(finding, "rule_id", None),
        "rule_name": getattr(finding, "rule_name", None),
        "severity": getattr(getattr(finding, "severity", None), "value", getattr(finding, "severity", None)),
        "description": getattr(finding, "description", None),
        "recommendation": getattr(finding, "recommendation", None),
        "file_path": getattr(finding, "file_path", None),
        "line_number": getattr(finding, "line_number", None),
        "evidence": getattr(finding, "evidence", None),
        "fix_code": getattr(finding, "fix_code", None),
        "fix_example": getattr(finding, "fix_example", None),
        "processing_metadata": meta,
    }


class RemediationWorkflow:
    """Builds an validated remediation plan from a cloned repository."""

    async def build_plan_from_clone(
        self,
        repo_root: str,
        repo_name: str,
        findings: list[Any],
        *,
        branch: str,
        scan_commit_hash: str | None = None,
        scan_detected_stack: dict[str, Any] | None = None,
        atomic_mode: bool = True,
        generate_missing_patches: bool = False,
    ) -> RemediationPlan:
        repo = Path(repo_root)
        head_sha = scan_commit_hash or "unknown"
        git_meta = repo / ".git"
        if git_meta.exists():
            head_sha = Repo(repo_root).head.commit.hexsha
        elif not scan_commit_hash:
            head_sha = "unknown"
        base_commit_sha = scan_commit_hash or head_sha
        if scan_commit_hash and git_meta.exists() and scan_commit_hash != head_sha:
            logger.warning(
                "Scan commit differs from clone HEAD; using clone HEAD for remediation",
                scan_commit=scan_commit_hash,
                clone_head=head_sha,
            )
            base_commit_sha = head_sha

        discovery_obj = discover_repository(
            repo_root,
            commit_sha=base_commit_sha,
            branch=branch,
            scan_detected_stack=scan_detected_stack,
        )
        discovery = discovery_obj.to_dict()

        finding_dicts: list[dict[str, Any]] = []
        for f in findings:
            fd = _finding_to_dict(f)
            fd["scan_commit_sha"] = base_commit_sha
            finding_dicts.append(fd)
        selected_ids = [fd["finding_id"] for fd in finding_dicts if fd.get("finding_id")]

        patch_fixes: list[dict[str, Any]] = []
        outcomes: list[FindingOutcome] = []

        for fd in finding_dicts:
            finding_id = fd["finding_id"]
            file_path = fd.get("file_path")
            if not file_path:
                outcomes.append(
                    FindingOutcome(
                        finding_id=finding_id,
                        rule_id=fd.get("rule_id"),
                        file_path=None,
                        status="skipped",
                        reason="Finding has no file path",
                    )
                )
                continue

            full_path, _ = resolve_file_path(repo_root, str(file_path), repo_name)
            if not full_path:
                outcomes.append(
                    FindingOutcome(
                        finding_id=finding_id,
                        rule_id=fd.get("rule_id"),
                        file_path=str(file_path),
                        status="manual_required",
                        reason="File not found in repository at base commit",
                        manual_guidance=fd.get("recommendation") or "",
                    )
                )
                continue

            rel_path = normalize_path(str(full_path), repo_root)
            content = read_repo_file(repo_root, rel_path)
            if content is None:
                outcomes.append(
                    FindingOutcome(
                        finding_id=finding_id,
                        rule_id=fd.get("rule_id"),
                        file_path=rel_path,
                        status="manual_required",
                        reason="Unable to read file content safely",
                    )
                )
                continue

            content_hash = file_content_hash(content)
            related = related_files_for_path(discovery_obj, rel_path)

            resolved = resolve_existing_patch_payload(fd, rel_path, content, content_hash)
            patch_meta: dict[str, Any] | None = resolved

            if not patch_meta and generate_missing_patches:
                patch_meta = await generate_unified_diff_patch(
                    finding=fd,
                    rel_path=rel_path,
                    file_content=content,
                    discovery_summary=discovery,
                    related_paths=related,
                )

            if not patch_meta:
                outcomes.append(
                    FindingOutcome(
                        finding_id=finding_id,
                        rule_id=fd.get("rule_id"),
                        file_path=rel_path,
                        status="manual_required",
                        reason="No applicable unified diff; full-file templates are not auto-applied",
                        manual_guidance=fd.get("recommendation") or "",
                    )
                )
                continue

            status = patch_meta.get("status", "manual_required")
            if status != "ready":
                outcomes.append(
                    FindingOutcome(
                        finding_id=finding_id,
                        rule_id=fd.get("rule_id"),
                        file_path=rel_path,
                        status=status if status in {"manual_required", "rejected"} else "manual_required",
                        reason=patch_meta.get("reason") or patch_meta.get("explanation") or status,
                        manual_guidance=patch_meta.get("manual_guidance") or "",
                        assumptions=list(patch_meta.get("assumptions") or []),
                        breaking_changes=list(patch_meta.get("breaking_changes") or []),
                        confidence=patch_meta.get("confidence"),
                    )
                )
                continue

            patch_fixes.append(
                {
                    "file_path": rel_path,
                    "finding_id": finding_id,
                    "rule_id": fd.get("rule_id"),
                    "unified_diff": patch_meta["unified_diff"],
                    "original_sha256": content_hash,
                    "explanation": patch_meta.get("explanation"),
                }
            )
            outcomes.append(
                FindingOutcome(
                    finding_id=finding_id,
                    rule_id=fd.get("rule_id"),
                    file_path=rel_path,
                    status="ready",
                    reason="Patch generated and applicable",
                    unified_diff=patch_meta.get("unified_diff"),
                    assumptions=list(patch_meta.get("assumptions") or []),
                    breaking_changes=list(patch_meta.get("breaking_changes") or []),
                    confidence=patch_meta.get("confidence"),
                )
            )

        # Group and dry-run reconcile + validate per file
        grouped: dict[str, list[dict[str, Any]]] = {}
        for fix in patch_fixes:
            grouped.setdefault(fix["file_path"], []).append(fix)

        file_changes: dict[str, dict[str, Any]] = {}
        ready_ids = {o.finding_id for o in outcomes if o.status == "ready"}

        for rel_path, file_fixes in grouped.items():
            full_path, _ = resolve_file_path(repo_root, rel_path, repo_name)
            if not full_path:
                continue
            original = read_repo_file(repo_root, rel_path) or ""
            try:
                updated, _meta = reconcile_file_patches(rel_path, original, file_fixes)
            except PatchValidationError as exc:
                for fix in file_fixes:
                    fid = fix.get("finding_id")
                    for outcome in outcomes:
                        if outcome.finding_id == fid:
                            outcome.status = "rejected"
                            outcome.reason = str(exc)
                    ready_ids.discard(str(fid))
                continue

            if updated == original:
                continue

            ok, validation_results = run_validators(rel_path, original, updated, discovery_obj)
            file_changes[rel_path] = {
                "original_sha256": file_content_hash(original),
                "updated_sha256": file_content_hash(updated),
                "finding_ids": [fx.get("finding_id") for fx in file_fixes],
                "validation": validation_results,
                "validation_passed": ok,
            }

            for outcome in outcomes:
                if outcome.finding_id in file_changes[rel_path]["finding_ids"]:
                    outcome.validation = validation_results
                    if not ok:
                        outcome.status = "rejected"
                        outcome.reason = "Validator failed for reconciled file content"
                        ready_ids.discard(outcome.finding_id)

        # Filter fixes to only those still ready after validation
        final_fixes = [fx for fx in patch_fixes if fx.get("finding_id") in ready_ids]

        atomic_ok = True
        if atomic_mode:
            for fd in finding_dicts:
                fid = fd["finding_id"]
                if fid not in ready_ids:
                    atomic_ok = False
                    break

        return RemediationPlan(
            base_commit_sha=base_commit_sha,
            branch=branch,
            discovery=discovery,
            fixes=final_fixes,
            outcomes=outcomes,
            file_changes=file_changes,
            atomic_ok=atomic_ok,
            atomic_mode=atomic_mode,
            selected_finding_ids=selected_ids,
        )
