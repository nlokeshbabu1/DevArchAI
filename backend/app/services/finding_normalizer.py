"""
Universal finding normalization for DevArchAI scan pipeline.

Scanner-independent: preserves original evidence, normalizes severity with
transparent fallbacks, classifies detection source and remediation capability.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from app.rule_engine.base import Category, RuleFinding, Severity
from app.scanners.normalizer import detect_category, map_severity

logger = structlog.get_logger(__name__)

# Conservative default when scanner severity is missing or unmapped (not INFO).
UNKNOWN_SEVERITY_FALLBACK = Severity.MEDIUM


class DetectionSource(str, Enum):
    """Authoritative detection producer (not LLM enrichment)."""

    RULE_ENGINE = "rule_engine"
    EXTERNAL_SCANNER = "external_scanner"
    DEVARCHAI_SCANNER = "devarchai_scanner"  # Azure/Helm/repo-level scanners


class RemediationStatus(str, Enum):
    """How remediation can be applied for this finding."""

    FIX_AVAILABLE = "FIX_AVAILABLE"  # Validated/automated fix path exists
    AI_SUGGESTED = "AI_SUGGESTED"  # LLM or static guidance only
    MANUAL_REMEDIATION = "MANUAL_REMEDIATION"  # Human must apply change
    NOT_SUPPORTED = "NOT_SUPPORTED"  # No remediation path known


@dataclass
class NormalizationStats:
    processed: int = 0
    severity_fallbacks: int = 0
    unknown_severity_labels: int = 0


def _infer_detection_source(finding: RuleFinding) -> DetectionSource:
    scanner = (getattr(finding, "scanner_name", None) or "").strip()
    if not scanner or scanner.lower() in {"devarchai", "devarchai-rules"}:
        return DetectionSource.RULE_ENGINE
    if scanner.lower() in {"azure_scanner", "helm_scanner", "repository_rules"}:
        return DetectionSource.DEVARCHAI_SCANNER
    return DetectionSource.EXTERNAL_SCANNER


def _original_severity_label(finding: RuleFinding) -> str | None:
    meta = finding.metadata or {}
    if meta.get("original_severity"):
        return str(meta["original_severity"])
    if meta.get("scanner_severity"):
        return str(meta["scanner_severity"])
    if hasattr(finding, "severity") and finding.severity:
        return finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)
    return None


def normalize_severity_for_finding(
    finding: RuleFinding,
    *,
    external_severity: str | None = None,
    stats: NormalizationStats | None = None,
) -> None:
    """Set normalized severity and preserve original label in metadata."""
    meta = finding.metadata or {}
    raw = external_severity or meta.get("scanner_severity") or meta.get("original_severity")
    if raw is not None:
        meta["original_severity"] = str(raw).strip().lower()
    elif "original_severity" not in meta and finding.severity:
        meta["original_severity"] = (
            finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)
        )

    if external_severity is not None or meta.get("scanner_severity"):
        label = (external_severity or meta.get("scanner_severity") or "").strip().lower()
        if label:
            meta["original_severity"] = label
        from app.scanners.normalizer import SEVERITY_MAP

        if label and label not in SEVERITY_MAP:
            if stats:
                stats.unknown_severity_labels += 1
            finding.severity = UNKNOWN_SEVERITY_FALLBACK
            meta["severity_normalized_from"] = label
            meta["severity_fallback"] = UNKNOWN_SEVERITY_FALLBACK.value
            if stats:
                stats.severity_fallbacks += 1
        else:
            finding.severity = map_severity(label or None)
    elif stats and not finding.severity:
        finding.severity = UNKNOWN_SEVERITY_FALLBACK
        stats.severity_fallbacks += 1

    finding.metadata = meta


def compute_remediation_status(finding: RuleFinding) -> RemediationStatus:
    """
    Remediation capability — not equivalent to having text in fix_code.

    FIX_AVAILABLE only when metadata marks a supported automated fix path
    or DevArchAI rule engine emitted a structured fix with high confidence.
    """
    meta = finding.metadata or {}

    if meta.get("automated_fix_validated") is True:
        return RemediationStatus.FIX_AVAILABLE

    if meta.get("automated_fix_supported") is True and finding.fix_code:
        return RemediationStatus.FIX_AVAILABLE

    if finding.ai_generated and (finding.fix_code or finding.fix_example):
        return RemediationStatus.AI_SUGGESTED

    if finding.fix_code or finding.fix_example or finding.recommendation:
        if getattr(finding, "fixed_version", None) or meta.get("upgrade_path"):
            return RemediationStatus.MANUAL_REMEDIATION
        return RemediationStatus.AI_SUGGESTED

    if finding.recommendation and len(finding.recommendation.strip()) > 20:
        return RemediationStatus.MANUAL_REMEDIATION

    return RemediationStatus.NOT_SUPPORTED


def normalize_finding(finding: RuleFinding, stats: NormalizationStats | None = None) -> RuleFinding:
    """Apply universal normalization to a single RuleFinding (in place)."""
    if stats:
        stats.processed += 1

    meta = dict(finding.metadata or {})

    if not finding.description:
        finding.description = finding.rule_name or finding.rule_id or "Security finding"
    if not finding.recommendation:
        finding.recommendation = "Review the affected resource and apply security best practices."

    source = _infer_detection_source(finding)
    meta["detection_source"] = source.value

    if not finding.category:
        finding.category = detect_category(finding.description, finding.rule_id)

    normalize_severity_for_finding(finding, stats=stats)
    meta = {**meta, **(finding.metadata or {})}

    meta["remediation_status"] = compute_remediation_status(finding).value
    meta.setdefault("provenance", "scanner_or_rule_engine")
    if finding.ai_generated:
        meta["ai_enriched"] = True
        meta["provenance"] = "ai_enriched_existing_finding"

    finding.metadata = meta
    return finding


def normalize_findings(findings: list[RuleFinding]) -> tuple[list[RuleFinding], NormalizationStats]:
    stats = NormalizationStats()
    for f in findings:
        normalize_finding(f, stats)
    logger.info(
        "findings_normalized",
        count=stats.processed,
        severity_fallbacks=stats.severity_fallbacks,
        unknown_severity_labels=stats.unknown_severity_labels,
    )
    return findings, stats


def processing_metadata_dict(finding: RuleFinding) -> dict[str, Any]:
    """Extract pipeline metadata for persistence/API (no scanner evidence)."""
    meta = finding.metadata or {}
    return {
        "detection_source": meta.get("detection_source"),
        "original_severity": meta.get("original_severity"),
        "severity_normalized_from": meta.get("severity_normalized_from"),
        "severity_fallback": meta.get("severity_fallback"),
        "remediation_status": meta.get("remediation_status"),
        "provenance": meta.get("provenance"),
        "deduplicated": meta.get("deduplicated"),
        "merged": meta.get("merged"),
        "scanners": meta.get("scanners"),
        "occurrence_count": meta.get("occurrence_count"),
    }
    if isinstance(meta.get("remediation"), dict):
        payload["remediation"] = meta["remediation"]
    return payload


def serialize_processing_metadata(finding: RuleFinding) -> str | None:
    payload = processing_metadata_dict(finding)
    if not any(v is not None for v in payload.values()):
        return None
    return json.dumps(payload)


def parse_processing_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def enrich_finding_api_payload(finding: Any, base: dict[str, Any]) -> dict[str, Any]:
    """Merge processing metadata into API dict (Finding ORM or similar)."""
    raw = getattr(finding, "processing_metadata", None)
    meta = parse_processing_metadata(raw)
    if not meta.get("remediation_status"):
        meta["remediation_status"] = RemediationStatus.MANUAL_REMEDIATION.value
    if not meta.get("detection_source"):
        sn = getattr(finding, "scanner_name", None)
        meta["detection_source"] = (
            DetectionSource.EXTERNAL_SCANNER.value
            if sn and sn.lower() not in {"devarchai", ""}
            else DetectionSource.RULE_ENGINE.value
        )
    base["processing_metadata"] = meta
    base["detection_source"] = meta.get("detection_source")
    base["original_severity"] = meta.get("original_severity") or base.get("severity")
    base["remediation_status"] = meta.get("remediation_status")
    remediation = meta.get("remediation") if isinstance(meta.get("remediation"), dict) else {}
    if remediation:
        base["patch_status"] = remediation.get("patch_status")
        base["patch_explanation"] = remediation.get("explanation")
        base["patch_skip_reason"] = remediation.get("skip_reason") or remediation.get("manual_guidance")
        base["has_stored_patch"] = bool(remediation.get("unified_diff")) and remediation.get("patch_status") in {
            "patch_generated",
            "validation_passed",
        }
    return base
