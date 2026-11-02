"""Remediation patch metadata schema and safe merge into finding processing_metadata."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.services.finding_normalizer import parse_processing_metadata


class PatchGenerationStatus(str, Enum):
    NOT_EVALUATED = "not_evaluated"
    PENDING = "pending"
    PATCH_GENERATED = "patch_generated"
    PATCH_REJECTED = "patch_rejected"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    MANUAL_REQUIRED = "manual_required"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    STALE_PATCH = "stale_patch"


PROMPT_VERSION_REMEDIATION = "remediation-patch/v1"


def remediation_idempotency_key(
    *,
    finding_id: str,
    commit_sha: str | None,
    file_path: str | None,
    rule_id: str | None,
    line_number: int | None,
) -> str:
    return "|".join(
        [
            str(finding_id or ""),
            str(commit_sha or ""),
            str(file_path or ""),
            str(rule_id or ""),
            str(line_number if line_number is not None else ""),
        ]
    )


def get_remediation_block(meta: dict[str, Any]) -> dict[str, Any]:
    block = meta.get("remediation")
    return block if isinstance(block, dict) else {}


def merge_remediation_metadata(
    existing_raw: str | None,
    remediation_update: dict[str, Any],
) -> str:
    """Merge remediation fields without removing unrelated processing_metadata keys."""
    meta = parse_processing_metadata(existing_raw)
    current = get_remediation_block(meta)
    merged = {**current, **remediation_update}
    meta["remediation"] = merged
    return json.dumps(meta, ensure_ascii=False)


def patch_is_reusable(
    remediation: dict[str, Any],
    *,
    commit_sha: str | None,
    file_content_hash: str | None,
) -> bool:
    if remediation.get("patch_status") not in {
        PatchGenerationStatus.PATCH_GENERATED.value,
        PatchGenerationStatus.VALIDATION_PASSED.value,
    }:
        return False
    if not remediation.get("unified_diff"):
        return False
    if commit_sha and remediation.get("commit_sha") and remediation["commit_sha"] != commit_sha:
        return False
    if file_content_hash and remediation.get("original_content_sha256"):
        if remediation["original_content_sha256"] != file_content_hash:
            return False
    return True


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
