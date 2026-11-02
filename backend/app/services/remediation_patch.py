"""
Safe, repository-agnostic remediation patch model and validation.

Default: minimal modifications preserving original application behaviour.
Full-file replacement is rejected unless it passes strict preservation checks.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PatchType(str, Enum):
    UNIFIED_DIFF = "unified_diff"
    TARGETED_CONTENT = "targeted_content"
    FULL_FILE = "full_file"


class PatchValidationError(Exception):
    """Patch failed safety validation."""


@dataclass
class RemediationPatch:
    file_path: str
    finding_id: str | None
    rule_id: str | None = None
    patch_type: PatchType = PatchType.TARGETED_CONTENT
    original_sha256: str | None = None
    proposed_content: str = ""
    unified_diff: str | None = None
    validation_notes: list[str] = field(default_factory=list)


def file_content_hash(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()


def build_unified_diff(path: str, original: str, updated: str) -> str:
    orig_lines = original.splitlines(keepends=False)
    upd_lines = updated.splitlines(keepends=False)
    lines = difflib.unified_diff(
        orig_lines,
        upd_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    )
    return "\n".join(lines) + ("\n" if lines else "")


def apply_unified_diff(original: str, diff_text: str) -> str:
    """Apply unified diff; raises PatchValidationError if it does not apply cleanly."""
    if not diff_text.strip():
        raise PatchValidationError("Empty unified diff")
    original_lines = original.splitlines(keepends=False)
    result_lines = _apply_unified_diff_lines(original_lines, diff_text)
    trailing_newline = original.endswith("\n")
    joined = "\n".join(result_lines)
    return joined + ("\n" if trailing_newline else "")


def _parse_unified_diff_hunks(diff_text: str) -> list[tuple[int, list[tuple[str, str]]]]:
    """Parse unified diff into (1-based start line, [(op, text), ...]) hunks."""
    hunks: list[tuple[int, list[tuple[str, str]]]] = []
    current_start = 0
    current_ops: list[tuple[str, str]] = []

    for raw in diff_text.splitlines():
        if raw.startswith("@@"):
            if current_ops:
                hunks.append((current_start, current_ops))
                current_ops = []
            m = re.match(r"@@\s+-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@", raw)
            if not m:
                raise PatchValidationError(f"Invalid hunk header: {raw}")
            current_start = int(m.group(1))
            continue
        if raw.startswith("---") or raw.startswith("+++"):
            continue
        if not raw and current_start == 0 and not current_ops:
            continue
        if raw[:1] in {" ", "+", "-"}:
            current_ops.append((raw[0], raw[1:]))
        elif raw.startswith("\\"):
            continue
        else:
            raise PatchValidationError(f"Invalid diff line: {raw[:40]}")

    if current_ops:
        hunks.append((current_start, current_ops))
    return hunks


def _apply_unified_diff_lines(original_lines: list[str], diff_text: str) -> list[str]:
    """Apply unified diff hunks to original lines (no trailing newline on each line)."""
    hunks = _parse_unified_diff_hunks(diff_text)
    if not hunks:
        raise PatchValidationError("No hunks found in unified diff")

    result: list[str] = []
    line_idx = 0

    for hunk_start, ops in hunks:
        target_idx = max(hunk_start - 1, 0)
        while line_idx < target_idx:
            if line_idx >= len(original_lines):
                raise PatchValidationError("Diff hunk starts beyond end of file")
            result.append(original_lines[line_idx])
            line_idx += 1

        for op, text in ops:
            if op == " ":
                if line_idx >= len(original_lines) or original_lines[line_idx] != text:
                    raise PatchValidationError("Diff context mismatch")
                result.append(original_lines[line_idx])
                line_idx += 1
            elif op == "-":
                if line_idx >= len(original_lines) or original_lines[line_idx] != text:
                    raise PatchValidationError("Diff removal mismatch")
                line_idx += 1
            elif op == "+":
                result.append(text)

    while line_idx < len(original_lines):
        result.append(original_lines[line_idx])
        line_idx += 1

    return result


def _dockerfile_signals(content: str) -> set[str]:
    text = content.lower()
    signals: set[str] = set()
    for key in ("golang", "go ", "node", "npm", "python", "pip ", "distroless", "alpine"):
        if key in text:
            signals.add(key.split()[0] if " " in key else key)
    return signals


def _k8s_kinds(content: str) -> set[str]:
    """Return resource kinds from each YAML document (ignores nested kind: references)."""
    kinds: set[str] = set()
    docs = re.split(r"^\s*---\s*$", content, flags=re.MULTILINE)
    if len(docs) == 1 and "---" not in content:
        docs = [content]
    for doc in docs:
        if not doc.strip():
            continue
        m = re.search(r"^\s*kind:\s*(\S+)\s*$", doc, flags=re.MULTILINE | re.IGNORECASE)
        if m:
            kinds.add(m.group(1))
    return kinds


def validate_preservation(original: str, updated: str, rel_path: str) -> dict[str, Any]:
    """Reject destructive rewrites and technology stack swaps."""
    notes: list[str] = []
    orig_len = len(original or "")
    upd_len = len(updated or "")
    if orig_len == 0:
        raise PatchValidationError("Original file is empty")

    if upd_len == 0:
        raise PatchValidationError("Patch would empty the file")

    ratio = upd_len / orig_len if orig_len else 1.0
    notes.append(f"size_ratio={ratio:.3f}")

    path_lower = rel_path.lower()
    if path_lower.endswith("dockerfile") or "dockerfile" in path_lower:
        orig_sig = _dockerfile_signals(original)
        upd_sig = _dockerfile_signals(updated)
        if orig_sig and upd_sig and orig_sig.isdisjoint(upd_sig):
            raise PatchValidationError(
                f"Dockerfile technology stack change detected ({orig_sig} -> {upd_sig})"
            )
        orig_from = re.findall(r"^\s*from\s+(\S+)", original, flags=re.MULTILINE | re.IGNORECASE)
        upd_from = re.findall(r"^\s*from\s+(\S+)", updated, flags=re.MULTILINE | re.IGNORECASE)
        if orig_from and upd_from and orig_from[0].split(":")[0] != upd_from[0].split(":")[0]:
            if "distroless" in orig_from[0].lower() and "node" in upd_from[0].lower():
                raise PatchValidationError("Dockerfile base image family changed (e.g. Go/distroless -> Node)")

    if any(
        path_lower.endswith(ext)
        for ext in (".yaml", ".yml")
    ) or "/templates/" in path_lower or "/kubernetes/" in path_lower:
        orig_kinds = _k8s_kinds(original)
        upd_kinds = _k8s_kinds(updated)
        workload_kinds = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "ReplicaSet"}
        orig_workloads = orig_kinds & workload_kinds
        if orig_workloads and not (orig_workloads & upd_kinds):
            raise PatchValidationError(
                f"Kubernetes workload removed from file (had {orig_workloads}, now {upd_kinds})"
            )

    # Large unrelated rewrite: more than 55% of original lines removed
    orig_lines = [ln for ln in original.splitlines() if ln.strip()]
    upd_set = set(updated.splitlines())
    removed = sum(1 for ln in orig_lines if ln not in upd_set)
    if orig_lines and removed / len(orig_lines) > 0.55:
        raise PatchValidationError(
            f"Patch removes too much unrelated content ({removed}/{len(orig_lines)} significant lines)"
        )

    return {"valid": True, "notes": notes, "size_ratio": ratio}


def resolve_proposed_content(
    original: str,
    fix: dict[str, Any],
    *,
    rel_path: str,
) -> str:
    """
    Choose safe proposed content from fix payload.

    Does NOT prefer full-file LLM examples. Uses unified diff when present,
    otherwise targeted fix_code with preservation validation.
    """
    if fix.get("unified_diff"):
        return apply_unified_diff(original, str(fix["unified_diff"]))

    fix_text = fix.get("fix_code") or fix.get("after_code") or ""
    if not fix_text.strip():
        raise PatchValidationError("No fix content provided")

    # Explicit full-file only when flagged and passes preservation
    if fix.get("patch_type") == PatchType.FULL_FILE.value or fix.get("allow_full_file"):
        validate_preservation(original, fix_text, rel_path)
        return fix_text

    ratio = len(fix_text) / max(len(original), 1)
    if ratio >= 0.85:
        validate_preservation(original, fix_text, rel_path)
        return fix_text

    raise PatchValidationError(
        "Fix content is not a safe full-file replacement and no unified diff was provided. "
        "Use a targeted unified diff or manual remediation."
    )


def reconcile_file_patches(
    rel_path: str,
    original_content: str,
    fixes: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """
    Apply multiple finding fixes to one file from a single base version.
    """
    base_hash = file_content_hash(original_content)
    current = original_content
    applied: list[dict[str, Any]] = []

    for fix in fixes:
        if fix.get("original_sha256") and fix["original_sha256"] != base_hash:
            raise PatchValidationError(
                f"Stale patch for {rel_path}: file changed since patch generation"
            )
        proposed = resolve_proposed_content(current, fix, rel_path=rel_path)
        validate_preservation(current, proposed, rel_path)
        diff_text = build_unified_diff(rel_path, current, proposed)
        applied.append(
            {
                "finding_id": fix.get("finding_id"),
                "rule_id": fix.get("rule_id"),
                "diff": diff_text,
                "original_sha256": base_hash,
            }
        )
        current = proposed

    return current, applied
