"""
Cross-scanner finding deduplication.

Deduplicates findings across both DevArchAI rules and external scanners.
When the same issue is found by multiple scanners, evidence from all scanners
is merged while keeping the best description and recommendation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import structlog

from app.rule_engine.base import RuleFinding, Severity

logger = structlog.get_logger(__name__)


@dataclass
class DedupStats:
    """Deduplication statistics."""
    original_count: int = 0
    deduplicated_count: int = 0
    merges: int = 0


def _normalize_path(path: str | None) -> str:
    """Normalize a file path for comparison."""
    if not path:
        return ""
    return path.strip().lstrip("/").lstrip("\\").lower()


def _create_scanner_aware_key(finding: RuleFinding) -> tuple:
    """Create a deduplication key that groups related findings.

    Priority order for grouping:
    1. CVE match (highest confidence)
    2. Rule ID cluster (same rule from different scanners)
    3. Package name + description similarity
    4. File path + line number
    """
    scanner_id = getattr(finding, "scanner_name", "") or "DevArchAI"
    rule_id = getattr(finding, "scanner_rule_id", "") or finding.rule_id
    cve = getattr(finding, "cve", "") or ""
    package = getattr(finding, "package", "") or ""
    file_path = _normalize_path(finding.file_path)
    line = finding.line_number or 0

    # CVE-based grouping is strongest
    if cve:
        return ("cve", cve, "")

    # SCA findings group by package + rule_id
    if package:
        base_rule = rule_id.split("/")[-1] if "/" in rule_id else rule_id
        return ("package", package, base_rule)

    # File + line for location-based findings
    if file_path and line:
        base_rule = rule_id.split("/")[-1] if "/" in rule_id else rule_id
        return ("location", file_path, str(line))

    # Fallback: rule ID cluster
    base_rule = rule_id.split("/")[-1] if "/" in rule_id else rule_id
    return ("rule", base_rule, scanner_id)


def deduplicate_across_scanners(
    findings: list[RuleFinding],
) -> tuple[list[RuleFinding], DedupStats]:
    """Deduplicate findings across all scanners.

    Groups findings by CVE, package, file+line, or rule ID.
    Merges evidence from duplicates while keeping the best version.

    Args:
        findings: All findings from DevArchAI rules and external scanners.

    Returns:
        Tuple of (deduplicated findings list, statistics).
    """
    stats = DedupStats(original_count=len(findings))

    if not findings:
        return [], stats

    groups: dict[tuple, list[RuleFinding]] = defaultdict(list)
    for finding in findings:
        key = _create_scanner_aware_key(finding)
        groups[key].append(finding)

    deduplicated: list[RuleFinding] = []
    total_merged = 0

    for key, group in groups.items():
        if len(group) == 1:
            deduplicated.append(group[0])
        else:
            merged = _merge_finding_group(group, key)
            deduplicated.append(merged)
            total_merged += len(group) - 1

    stats.deduplicated_count = len(deduplicated)
    stats.merges = total_merged

    logger.info(
        "Cross-scanner deduplication complete",
        original=stats.original_count,
        deduplicated=stats.deduplicated_count,
        merges=stats.merges,
    )

    return deduplicated, stats


def _score_finding(finding: RuleFinding) -> int:
    """Score a finding to determine the best version to keep."""
    score = 0
    if finding.ai_generated or finding.ai_explanation:
        score += 100
    if finding.summary:
        score += 10
    if finding.risk:
        score += 10
    if finding.impact:
        score += 10
    if finding.fix_code:
        score += 15
    if finding.fix_example:
        score += 10
    if finding.recommendation:
        score += 5
    if getattr(finding, "evidence", None):
        score += 5
    if getattr(finding, "references", None):
        score += 3
    if finding.confidence:
        score += int(finding.confidence * 10)
    return score


def _gather_evidence(group: list[RuleFinding]) -> str:
    """Gather evidence strings from all findings in the group."""
    evidence_parts: list[str] = []
    seen_evidence: set[str] = set()

    for f in group:
        ev = getattr(f, "evidence", None)
        if ev and ev not in seen_evidence:
            evidence_parts.append(f"[{getattr(f, 'scanner_name', 'Unknown')}]: {ev}")
            seen_evidence.add(ev)

    return "\n".join(evidence_parts)


def _gather_references(group: list[RuleFinding]) -> list[str]:
    """Gather unique references from all findings."""
    all_refs: list[str] = []
    seen_refs: set[str] = set()

    for f in group:
        refs = getattr(f, "references", None)
        if refs:
            for r in refs:
                if r and r not in seen_refs:
                    all_refs.append(r)
                    seen_refs.add(r)

    return all_refs


def _merge_finding_group(group: list[RuleFinding], key: tuple) -> RuleFinding:
    """Merge a group of duplicate findings, keeping the best one."""
    sorted_group = sorted(group, key=_score_finding, reverse=True)
    primary = sorted_group[0]

    evidence = _gather_evidence(sorted_group)
    references = _gather_references(sorted_group)

    # Collect all scanner names
    scanner_names: list[str] = []
    seen_names: set[str] = set()
    for f in sorted_group:
        name = getattr(f, "scanner_name", None) or "DevArchAI"
        if name not in seen_names:
            scanner_names.append(name)
            seen_names.add(name)

    # Collect all scanner rule IDs
    rule_ids: list[str] = []
    for f in sorted_group:
        rid = getattr(f, "scanner_rule_id", None) or f.rule_id
        if rid not in rule_ids:
            rule_ids.append(rid)

    # Collect all CVEs
    cves: list[str] = []
    for f in sorted_group:
        c = getattr(f, "cve", None)
        if c and c not in cves:
            cves.append(c)

    # Choose best severity (highest wins)
    severity_order = [
        Severity.CRITICAL, Severity.HIGH,
        Severity.MEDIUM, Severity.LOW, Severity.INFO,
    ]
    best_severity = primary.severity
    for f in sorted_group:
        if severity_order.index(f.severity) < severity_order.index(best_severity):
            best_severity = f.severity

    # Build merged description
    source_list = ", ".join(scanner_names)
    if key[0] == "cve":
        cve_id = key[1]
        description = f"{primary.description} (CVE: {cve_id}, detected by {source_list})"
    elif key[0] == "package":
        description = f"{primary.description} (detected by {source_list})"
    else:
        description = f"{primary.description} (detected by {source_list})"

    # Build merged recommendation with scanner context
    recommendation_parts: list[str] = [primary.recommendation] if primary.recommendation else []
    for f in sorted_group[1:]:
        if f.recommendation and f.recommendation != primary.recommendation:
            recommendation_parts.append(f"({getattr(f, 'scanner_name', 'Unknown')}: {f.recommendation})")
    recommendation = " ".join(recommendation_parts) if recommendation_parts else ""

    # Merge metadata
    merged_metadata: dict[str, Any] = {
        **(primary.metadata or {}),
        "scanners": scanner_names,
        "scanner_rule_ids": rule_ids,
        "cves": cves,
        "merged": True,
    }

    # Backfill empty fields
    backfill_fields = [
        "summary", "risk", "impact", "fix_code", "fix_example",
        "full_example", "documentation_url", "ai_explanation", "impact_analysis",
    ]

    for field in backfill_fields:
        if getattr(primary, field, None) is None:
            for f in sorted_group[1:]:
                val = getattr(f, field, None)
                if val is not None:
                    setattr(primary, field, val)
                    break

    # Merge best_practices
    all_best_practices: list[str] = list(primary.best_practices or [])
    for f in sorted_group[1:]:
        if f.best_practices:
            for bp in f.best_practices:
                if bp not in all_best_practices:
                    all_best_practices.append(bp)

    merged_finding = RuleFinding(
        rule_id=primary.rule_id,
        rule_name=primary.rule_name,
        severity=best_severity,
        category=primary.category,
        description=description,
        recommendation=recommendation or primary.recommendation or "",
        file_path=primary.file_path,
        line_number=primary.line_number,
        resource_name=primary.resource_name,
        confidence=primary.confidence,
        metadata=merged_metadata,
        ai_explanation=primary.ai_explanation,
        impact_analysis=primary.impact_analysis,
        summary=primary.summary,
        risk=primary.risk,
        impact=primary.impact,
        fix_code=primary.fix_code,
        fix_example=primary.fix_example,
        full_example=primary.full_example,
        best_practices=all_best_practices,
        documentation_url=primary.documentation_url,
        ai_generated=any(f.ai_generated for f in sorted_group),
    )

    # Set scanner-specific fields on the merged finding
    merged_finding.scanner_name = ", ".join(scanner_names)
    merged_finding.scanner_rule_id = ", ".join(rule_ids)
    merged_finding.evidence = evidence or None
    merged_finding.references = references or None

    if cves:
        merged_finding.cve = cves[0]
    merged_finding.package = primary.package
    merged_finding.installed_version = primary.installed_version
    merged_finding.fixed_version = primary.fixed_version

    return merged_finding
