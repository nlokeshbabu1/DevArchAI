"""
Scan-time remediation patch generation (second LLM call in AI pipeline).

Runs after the first recommendation LLM call; persists unified diffs to
finding.processing_metadata.remediation for PR reuse.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog

from app.config import settings
from app.services.finding_normalizer import parse_processing_metadata
from app.services.remediation_discovery import discover_repository, related_files_for_path
from app.services.remediation_metadata import (
    PROMPT_VERSION_REMEDIATION,
    PatchGenerationStatus,
    merge_remediation_metadata,
    patch_is_reusable,
    remediation_idempotency_key,
    utc_now_iso,
)
from app.services.remediation_patch import PatchValidationError, file_content_hash
from app.services.remediation_patch_generator import generate_unified_diff_patch
from app.services.remediation_validators import run_validators

logger = structlog.get_logger(__name__)

MAX_PATCH_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2.0
MAX_FULL_FILE_CHARS = 48_000


def _is_rate_limit_error(message: str) -> bool:
    lower = message.lower()
    return "429" in lower or "rate" in lower or "quota" in lower


async def generate_scan_time_patch_for_finding(
    *,
    scan: Any,
    finding: Any,
    file_loader: Any | None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate and validate a unified diff for one finding. Never raises.

    Returns remediation metadata block (without wrapping in processing_metadata).
    """
    finding_id = str(getattr(finding, "id", "") or "")
    file_path = str(getattr(finding, "file_path", "") or "")
    rule_id = str(getattr(finding, "rule_id", "") or "")
    line_number = getattr(finding, "line_number", None)
    commit_sha = getattr(scan, "commit_hash", None) or None
    repo_url = getattr(scan, "repository_url", "") or ""

    existing = parse_processing_metadata(getattr(finding, "processing_metadata", None))
    prior = existing.get("remediation") if isinstance(existing.get("remediation"), dict) else {}
    idem_key = remediation_idempotency_key(
        finding_id=finding_id,
        commit_sha=commit_sha,
        file_path=file_path,
        rule_id=rule_id,
        line_number=line_number,
    )

    if prior.get("idempotency_key") == idem_key:
        terminal = {
            PatchGenerationStatus.PATCH_GENERATED.value,
            PatchGenerationStatus.VALIDATION_PASSED.value,
            PatchGenerationStatus.VALIDATION_FAILED.value,
            PatchGenerationStatus.MANUAL_REQUIRED.value,
            PatchGenerationStatus.PATCH_REJECTED.value,
            PatchGenerationStatus.PROVIDER_UNAVAILABLE.value,
        }
        if prior.get("patch_status") in terminal:
            return prior

    base_block: dict[str, Any] = {
        "patch_status": PatchGenerationStatus.PENDING.value,
        "idempotency_key": idem_key,
        "finding_id": finding_id,
        "file_path": file_path,
        "commit_sha": commit_sha,
        "repository_url": repo_url,
        "job_id": job_id,
        "prompt_version": PROMPT_VERSION_REMEDIATION,
    }

    if not file_path:
        return {
            **base_block,
            "patch_status": PatchGenerationStatus.MANUAL_REQUIRED.value,
            "safely_remediable": False,
            "skip_reason": "Finding has no file path",
            "generated_at": utc_now_iso(),
        }

    content, rel_path = _load_file_content(scan, finding, file_loader)
    if not content or not rel_path:
        return {
            **base_block,
            "patch_status": PatchGenerationStatus.MANUAL_REQUIRED.value,
            "safely_remediable": False,
            "skip_reason": "Source file unavailable from scan clone",
            "generated_at": utc_now_iso(),
        }

    content_hash = file_content_hash(content)
    if patch_is_reusable(prior, commit_sha=commit_sha, file_content_hash=content_hash):
        return prior

    discovery_summary: dict[str, Any] = {}
    related: list[str] = []
    if file_loader and getattr(file_loader, "_repo_root", None):
        try:
            disc = discover_repository(
                str(file_loader._repo_root),
                commit_sha=commit_sha or "unknown",
                branch=getattr(scan, "branch", None),
                scan_detected_stack=getattr(scan, "detected_stack", None)
                if isinstance(getattr(scan, "detected_stack", None), dict)
                else None,
            )
            discovery_summary = disc.to_dict()
            related = related_files_for_path(disc, rel_path)
        except Exception as exc:
            logger.debug("SCAN_PATCH_DISCOVERY_SKIP", error=str(exc))

    finding_payload = {
        "finding_id": finding_id,
        "rule_id": rule_id,
        "rule_name": getattr(finding, "rule_name", None),
        "severity": getattr(getattr(finding, "severity", None), "value", getattr(finding, "severity", None)),
        "description": getattr(finding, "description", None),
        "recommendation": getattr(finding, "recommendation", None),
        "file_path": rel_path,
        "line_number": line_number,
        "evidence": getattr(finding, "evidence", None),
    }

    last_error = ""
    for attempt in range(MAX_PATCH_RETRIES + 1):
        try:
            result = await generate_unified_diff_patch(
                finding=finding_payload,
                rel_path=rel_path,
                file_content=content,
                discovery_summary=discovery_summary,
                related_paths=related,
            )
            status = result.get("status", "manual_required")
            if status == "ready":
                diff_text = result.get("unified_diff") or ""
                ok, validation_results = run_validators(rel_path, content, _apply_diff(content, diff_text, rel_path), None)
                patch_status = (
                    PatchGenerationStatus.VALIDATION_PASSED.value
                    if ok
                    else PatchGenerationStatus.VALIDATION_FAILED.value
                )
                return {
                    **base_block,
                    "patch_status": patch_status,
                    "unified_diff": diff_text,
                    "original_content_sha256": content_hash,
                    "explanation": result.get("explanation") or "",
                    "assumptions": result.get("assumptions") or [],
                    "breaking_changes": result.get("breaking_changes") or [],
                    "required_validations": result.get("required_validations") or ["preservation"],
                    "confidence": result.get("confidence"),
                    "safely_remediable": ok,
                    "validation_status": "passed" if ok else "failed",
                    "validation_results": validation_results,
                    "provider": str(getattr(settings, "LLM_PROVIDER", "unknown")),
                    "generated_at": utc_now_iso(),
                    "llm_call": "scan_time_patch",
                }

            reason = result.get("reason") or status
            patch_status = PatchGenerationStatus.MANUAL_REQUIRED.value
            if status == "rejected":
                patch_status = PatchGenerationStatus.PATCH_REJECTED.value
            if "rate limit" in reason.lower() or "unavailable" in reason.lower():
                patch_status = PatchGenerationStatus.PROVIDER_UNAVAILABLE.value

            return {
                **base_block,
                "patch_status": patch_status,
                "original_content_sha256": content_hash,
                "safely_remediable": False,
                "skip_reason": reason,
                "manual_guidance": result.get("manual_guidance") or "",
                "generated_at": utc_now_iso(),
                "llm_call": "scan_time_patch",
            }
        except Exception as exc:
            last_error = str(exc)
            if _is_rate_limit_error(last_error) and attempt < MAX_PATCH_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            logger.warning(
                "SCAN_PATCH_GENERATION_FAILED",
                finding_id=finding_id,
                attempt=attempt,
                error=last_error[:300],
            )
            break

    patch_status = PatchGenerationStatus.PROVIDER_UNAVAILABLE.value
    if last_error and not _is_rate_limit_error(last_error):
        patch_status = PatchGenerationStatus.PATCH_REJECTED.value

    return {
        **base_block,
        "patch_status": patch_status,
        "original_content_sha256": content_hash,
        "safely_remediable": False,
        "skip_reason": last_error or "Patch generation failed",
        "generated_at": utc_now_iso(),
    }


def _apply_diff(original: str, diff_text: str, rel_path: str) -> str:
    from app.services.remediation_patch import apply_unified_diff

    try:
        return apply_unified_diff(original, diff_text)
    except PatchValidationError:
        return original


def _load_file_content(
    scan: Any,
    finding: Any,
    file_loader: Any | None,
) -> tuple[str | None, str | None]:
    file_path = str(getattr(finding, "file_path", "") or "")
    if not file_path:
        return None, None

    if file_loader is not None and hasattr(file_loader, "read_full_file"):
        return file_loader.read_full_file(scan, finding, max_chars=MAX_FULL_FILE_CHARS)

    if file_loader is not None and hasattr(file_loader, "_ensure_repo"):
        root = file_loader._ensure_repo(scan)
        if root is not None:
            from app.services.github_pr import resolve_file_path
            from app.services.remediation_discovery import read_repo_file

            full, rel = resolve_file_path(str(root), file_path, None)
            if full and rel:
                content = read_repo_file(str(root), rel, max_bytes=MAX_FULL_FILE_CHARS)
                return content, rel
    return None, None


async def persist_remediation_on_finding(session: Any, finding: Any, remediation_block: dict[str, Any]) -> None:
    """Write remediation block onto Finding.processing_metadata."""
    from app.services.finding_normalizer import RemediationStatus

    finding.processing_metadata = merge_remediation_metadata(
        getattr(finding, "processing_metadata", None),
        remediation_block,
    )
    meta = parse_processing_metadata(finding.processing_metadata)
    status = remediation_block.get("patch_status")
    if status in {PatchGenerationStatus.VALIDATION_PASSED.value, PatchGenerationStatus.PATCH_GENERATED.value}:
        meta["remediation_status"] = RemediationStatus.FIX_AVAILABLE.value
    elif status in {
        PatchGenerationStatus.MANUAL_REQUIRED.value,
        PatchGenerationStatus.PATCH_REJECTED.value,
        PatchGenerationStatus.VALIDATION_FAILED.value,
    }:
        meta["remediation_status"] = RemediationStatus.MANUAL_REMEDIATION.value
    elif status == PatchGenerationStatus.PROVIDER_UNAVAILABLE.value:
        meta["remediation_status"] = RemediationStatus.AI_SUGGESTED.value
    finding.processing_metadata = json.dumps(meta, ensure_ascii=False)
    session.add(finding)
