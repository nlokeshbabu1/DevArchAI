"""
Live-context unified diff generation for remediation (repository-agnostic).
"""

from __future__ import annotations

import inspect
import json
import re
from typing import Any

import structlog

from app.ai.context_engine import is_llm_rate_limited, mark_llm_rate_limited, _extract_json_payload
from app.ai.engine import get_llm_provider
from app.config import settings
from app.services.remediation_patch import PatchValidationError, apply_unified_diff, build_unified_diff

logger = structlog.get_logger(__name__)

PROMPT_VERSION = "remediation-patch/v1"
MAX_FILE_CHARS = 48_000


def _looks_like_unified_diff(text: str) -> bool:
    t = (text or "").lstrip()
    return t.startswith("---") or t.startswith("diff ") or "@@" in t[:400]


def _parse_patch_response(raw: str) -> dict[str, Any]:
    payload = json.loads(_extract_json_payload(raw))
    if not isinstance(payload, dict):
        raise ValueError("Patch response must be a JSON object")
    return payload


def _build_patch_prompt(
    *,
    finding: dict[str, Any],
    rel_path: str,
    file_content: str,
    discovery_summary: dict[str, Any],
    related_paths: list[str],
) -> str:
    line_no = finding.get("line_number")
    snippet = file_content
    if line_no and isinstance(line_no, int):
        lines = file_content.splitlines()
        start = max(0, line_no - 15)
        end = min(len(lines), line_no + 15)
        snippet = "\n".join(lines[start:end])

    finding_payload = {
        "finding_id": finding.get("finding_id"),
        "rule_id": finding.get("rule_id"),
        "rule_name": finding.get("rule_name"),
        "severity": finding.get("severity"),
        "description": finding.get("description"),
        "recommendation": finding.get("recommendation"),
        "file_path": rel_path,
        "line_number": line_no,
        "evidence": finding.get("evidence"),
    }

    return (
        "You are DevArchAI generating a SAFE, MINIMAL unified diff patch for a repository file.\n"
        "Return ONLY valid JSON with fields:\n"
        "  unified_diff (string, required if remediable),\n"
        "  explanation (string),\n"
        "  assumptions (array of strings),\n"
        "  breaking_changes (array of strings),\n"
        "  confidence (float 0-1),\n"
        "  manual_remediation (boolean),\n"
        "  manual_guidance (string, when manual_remediation is true).\n"
        "Rules:\n"
        "- Patch MUST be a unified diff against the ACTUAL file content provided.\n"
        "- Preserve unrelated lines, technology stack, build stages, entrypoints, and resource names.\n"
        "- Do NOT replace the entire file unless absolutely required; prefer minimal hunks.\n"
        "- Do NOT invent a different language, base image family, or workload architecture.\n"
        "- If you cannot produce a safe diff, set manual_remediation=true and leave unified_diff empty.\n"
        f"- PROMPT_VERSION={PROMPT_VERSION}\n"
        f"Repository context (discovered): {json.dumps(discovery_summary, ensure_ascii=True)[:4000]}\n"
        f"Related paths (advisory): {json.dumps(related_paths[:8], ensure_ascii=True)}\n"
        f"Finding: {json.dumps(finding_payload, ensure_ascii=True)[:6000]}\n"
        f"ACTUAL file path: {rel_path}\n"
        f"ACTUAL file content (may be truncated):\n```\n{file_content[:MAX_FILE_CHARS]}\n```\n"
        f"Focus region around reported line:\n```\n{snippet[:8000]}\n```\n"
    )


async def _call_llm(prompt: str) -> str:
    provider = get_llm_provider()
    result = provider.generate(prompt)
    if inspect.isawaitable(result):
        result = await result
    return str(result)


async def generate_unified_diff_patch(
    *,
    finding: dict[str, Any],
    rel_path: str,
    file_content: str,
    discovery_summary: dict[str, Any],
    related_paths: list[str],
) -> dict[str, Any]:
    """
    Generate a verified unified diff against ``file_content``.

    Returns metadata dict with keys: status, unified_diff, explanation, ...
    """
    if is_llm_rate_limited():
        return {
            "status": "manual_required",
            "reason": "LLM temporarily unavailable (rate limit)",
            "manual_guidance": finding.get("recommendation") or "Apply fix manually per finding recommendation.",
        }

    prompt = _build_patch_prompt(
        finding=finding,
        rel_path=rel_path,
        file_content=file_content,
        discovery_summary=discovery_summary,
        related_paths=related_paths,
    )

    try:
        raw = await _call_llm(prompt)
        payload = _parse_patch_response(raw)
    except Exception as exc:
        err = str(exc)
        if "rate" in err.lower() or "429" in err:
            mark_llm_rate_limited(60.0)
        logger.warning("Patch LLM generation failed", error=err, finding_id=finding.get("finding_id"))
        return {
            "status": "manual_required",
            "reason": f"Patch generation failed: {err[:200]}",
            "manual_guidance": finding.get("recommendation") or "",
        }

    if payload.get("manual_remediation"):
        return {
            "status": "manual_required",
            "reason": payload.get("explanation") or "Manual remediation recommended by model",
            "manual_guidance": payload.get("manual_guidance") or finding.get("recommendation") or "",
            "assumptions": payload.get("assumptions") or [],
            "confidence": payload.get("confidence"),
        }

    diff_text = str(payload.get("unified_diff") or "").strip()
    if not diff_text:
        return {
            "status": "manual_required",
            "reason": "No unified diff produced",
            "manual_guidance": payload.get("manual_guidance") or "",
        }

    try:
        updated = apply_unified_diff(file_content, diff_text)
        if updated == file_content:
            return {
                "status": "manual_required",
                "reason": "Generated diff made no changes",
                "manual_guidance": payload.get("manual_guidance") or "",
            }
        # Normalize diff from actual apply result
        normalized_diff = build_unified_diff(rel_path, file_content, updated)
        apply_unified_diff(file_content, normalized_diff)
    except PatchValidationError as exc:
        return {
            "status": "rejected",
            "reason": f"Generated diff failed applicability check: {exc}",
            "manual_guidance": finding.get("recommendation") or "",
        }

    return {
        "status": "ready",
        "unified_diff": normalized_diff,
        "explanation": payload.get("explanation") or "",
        "assumptions": payload.get("assumptions") or [],
        "breaking_changes": payload.get("breaking_changes") or [],
        "confidence": payload.get("confidence"),
        "required_validations": ["preservation"],
    }


def resolve_existing_patch_payload(
    finding: dict[str, Any],
    rel_path: str,
    file_content: str,
    original_sha256: str,
) -> dict[str, Any] | None:
    """
    Use stored unified diff or diff-shaped fix_code without calling the LLM.
    """
    meta = finding.get("processing_metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            meta = {}

    stored = meta.get("remediation") if isinstance(meta, dict) else None
    if isinstance(stored, dict) and stored.get("unified_diff"):
        if finding.get("scan_commit_sha") and stored.get("commit_sha"):
            if stored["commit_sha"] != finding["scan_commit_sha"]:
                return None
        diff_text = str(stored["unified_diff"])
        try:
            apply_unified_diff(file_content, diff_text)
            return {
                "status": "ready",
                "unified_diff": diff_text,
                "source": "processing_metadata",
                "original_sha256": stored.get("original_content_sha256") or original_sha256,
            }
        except PatchValidationError:
            return None

    fix_code = finding.get("fix_code") or finding.get("fix_example") or ""
    if _looks_like_unified_diff(fix_code):
        try:
            apply_unified_diff(file_content, fix_code)
            return {
                "status": "ready",
                "unified_diff": fix_code,
                "source": "fix_code_diff",
                "original_sha256": original_sha256,
            }
        except PatchValidationError:
            return None

    return None
