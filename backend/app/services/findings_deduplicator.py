"""
Findings Deduplicator Service.

Detects and merges duplicate findings based on rule_id + file_path + line_number.
Prefers AI-enriched findings over static-only findings when merging.
Provides deduplication statistics for monitoring and logging.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import structlog

from app.rule_engine.base import RuleFinding

logger = structlog.get_logger(__name__)


@dataclass
class DeduplicationStats:
    """Statistics about the deduplication process."""

    original_count: int = 0
    deduplicated_count: int = 0
    duplicates_removed: int = 0
    ai_preferred_count: int = 0
    static_fallback_count: int = 0
    groups_with_duplicates: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "original_count": self.original_count,
            "deduplicated_count": self.deduplicated_count,
            "duplicates_removed": self.duplicates_removed,
            "ai_preferred_count": self.ai_preferred_count,
            "static_fallback_count": self.static_fallback_count,
            "groups_with_duplicates": self.groups_with_duplicates,
            "dedup_ratio": (
                round(
                    (self.original_count - self.deduplicated_count)
                    / max(self.original_count, 1)
                    * 100,
                    1,
                )
            ),
        }


class FindingsDeduplicator:
    """
    Deduplicate findings by rule_id, file_path, and line_number.

    When duplicates are detected, the service merges them by keeping the
    best available version -- preferring AI-enriched findings over static-only
    findings.  All duplicate metadata is aggregated into the merged result.
    """

    # Fields that form the unique deduplication key (include resource + scanner)
    _DEDUP_KEY_FIELDS: list[str] = [
        "rule_id",
        "file_path",
        "line_number",
        "resource_name",
        "scanner_name",
    ]

    def __init__(self) -> None:
        self.stats = DeduplicationStats()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def deduplicate(
        self,
        findings: list[RuleFinding],
    ) -> tuple[list[RuleFinding], DeduplicationStats]:
        """
        Deduplicate a list of findings and return the cleaned list with stats.

        Args:
            findings: List of findings that may contain duplicates.

        Returns:
            A tuple of (deduplicated findings list, deduplication stats).
        """
        self.stats = DeduplicationStats(original_count=len(findings))

        if not findings:
            return [], self.stats

        # Group findings by dedup key
        grouped: dict[str, list[RuleFinding]] = defaultdict(list)
        for finding in findings:
            key = self._create_dedup_key(finding)
            grouped[key].append(finding)

        deduplicated: list[RuleFinding] = []

        for _key, group in grouped.items():
            if len(group) == 1:
                # No duplicates -- keep as-is
                deduplicated.append(group[0])
            else:
                # Duplicates found -- merge, preferring AI-enriched version
                self.stats.groups_with_duplicates += 1
                merged = self._merge_findings(group)
                deduplicated.append(merged)

        # Finalise stats
        self.stats.deduplicated_count = len(deduplicated)
        self.stats.duplicates_removed = (
            self.stats.original_count - self.stats.deduplicated_count
        )

        logger.info(
            "Findings deduplication complete",
            original_count=self.stats.original_count,
            deduplicated_count=self.stats.deduplicated_count,
            duplicates_removed=self.stats.duplicates_removed,
            ai_preferred=self.stats.ai_preferred_count,
            static_fallback=self.stats.static_fallback_count,
            groups_with_duplicates=self.stats.groups_with_duplicates,
        )

        return deduplicated, self.stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_dedup_key(self, finding: RuleFinding) -> str:
        """
        Create a deterministic deduplication key from finding attributes.

        The key is composed of rule_id, file_path, and line_number joined
        by a pipe character.  Missing values default to empty strings so
        that two findings with None for the same field still collide.
        """
        parts: list[str] = []
        for field_name in self._DEDUP_KEY_FIELDS:
            value = getattr(finding, field_name, None)
            if field_name == "scanner_name":
                parts.append(str(value).strip() if value else "DevArchAI")
            else:
                parts.append(str(value) if value is not None else "")
        return "|".join(parts)

    def _is_ai_enriched(self, finding: RuleFinding) -> bool:
        """
        Determine whether a finding has been enriched by AI.

        A finding is considered AI-enriched if it has AI-generated content
        such as ai_explanation, summary, risk, impact, or fix_code.
        """
        return bool(
            finding.ai_explanation
            or finding.summary
            or finding.risk
            or finding.impact
            or finding.fix_code
            or finding.ai_generated
        )

    def _score_finding(self, finding: RuleFinding) -> int:
        """
        Score a finding to determine which version is 'best'.

        Higher score means more complete / higher quality finding.
        AI-enriched findings score higher than static-only ones.
        """
        score = 0

        # AI-enriched findings get a large bonus
        if self._is_ai_enriched(finding):
            score += 100

        # Bonus for each populated field
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
        if finding.full_example:
            score += 10
        if finding.best_practices:
            score += 5
        if finding.documentation_url:
            score += 5
        if finding.ai_explanation:
            score += 10
        if finding.impact_analysis:
            score += 10

        return score

    def _merge_findings(self, findings: list[RuleFinding]) -> RuleFinding:
        """
        Merge multiple duplicate findings into a single best version.

        Strategy:
        1. Select the finding with the highest quality score as the base.
        2. For any empty fields on the base, backfill from other duplicates.
        3. Aggregate metadata (occurrence count, affected files, etc.).

        Args:
            findings: List of duplicate findings.

        Returns:
            A single merged finding with the best available data.
        """
        # Sort by score descending -- best finding first
        sorted_findings = sorted(findings, key=self._score_finding, reverse=True)
        primary = sorted_findings[0]

        # Track which source won for logging
        if self._is_ai_enriched(primary):
            self.stats.ai_preferred_count += 1
        else:
            self.stats.static_fallback_count += 1

        # Collect aggregate information
        all_files: set[str] = set()
        all_resources: set[str] = set()
        all_line_numbers: set[int] = set()
        for f in findings:
            if f.file_path:
                all_files.add(f.file_path)
            if f.resource_name:
                all_resources.add(f.resource_name)
            if f.line_number is not None:
                all_line_numbers.add(f.line_number)

        occurrence_count = len(findings)

        # Build aggregated description
        if occurrence_count > 1:
            if len(all_files) > 1:
                aggregated_desc = (
                    f"{primary.description} "
                    f"(found in {occurrence_count} locations across {len(all_files)} files)"
                )
            else:
                aggregated_desc = (
                    f"{primary.description} "
                    f"(found {occurrence_count} times)"
                )
        else:
            aggregated_desc = primary.description

        # Build aggregated recommendation
        if occurrence_count > 1:
            aggregated_rec = (
                f"{primary.recommendation} "
                f"Apply this fix to all {occurrence_count} affected locations."
            )
        else:
            aggregated_rec = primary.recommendation

        # Merge metadata
        merged_metadata: dict[str, Any] = {
            **primary.metadata,
            "occurrence_count": occurrence_count,
            "affected_files": sorted(all_files),
            "affected_resources": sorted(all_resources),
            "affected_line_numbers": sorted(all_line_numbers),
            "deduplicated": True,
        }

        # Backfill empty fields from other duplicates
        best_summary = primary.summary
        best_risk = primary.risk
        best_impact = primary.impact
        best_fix_code = primary.fix_code
        best_fix_example = primary.fix_example
        best_full_example = primary.full_example
        best_best_practices = primary.best_practices or []
        best_documentation_url = primary.documentation_url
        best_ai_explanation = primary.ai_explanation
        best_impact_analysis = primary.impact_analysis

        for f in sorted_findings[1:]:
            if not best_summary and f.summary:
                best_summary = f.summary
            if not best_risk and f.risk:
                best_risk = f.risk
            if not best_impact and f.impact:
                best_impact = f.impact
            if not best_fix_code and f.fix_code:
                best_fix_code = f.fix_code
            if not best_fix_example and f.fix_example:
                best_fix_example = f.fix_example
            if not best_full_example and f.full_example:
                best_full_example = f.full_example
            if not best_best_practices and f.best_practices:
                best_best_practices = f.best_practices
            if not best_documentation_url and f.documentation_url:
                best_documentation_url = f.documentation_url
            if not best_ai_explanation and f.ai_explanation:
                best_ai_explanation = f.ai_explanation
            if not best_impact_analysis and f.impact_analysis:
                best_impact_analysis = f.impact_analysis

        # Merge best_practices lists (deduplicated)
        all_best_practices: list[str] = list(best_best_practices)
        for f in sorted_findings:
            if f.best_practices:
                for bp in f.best_practices:
                    if bp not in all_best_practices:
                        all_best_practices.append(bp)

        return RuleFinding(
            rule_id=primary.rule_id,
            rule_name=primary.rule_name,
            severity=primary.severity,
            category=primary.category,
            description=aggregated_desc,
            recommendation=aggregated_rec,
            file_path=primary.file_path,
            line_number=primary.line_number,
            resource_name=primary.resource_name,
            confidence=max(f.confidence for f in findings),
            metadata=merged_metadata,
            ai_explanation=best_ai_explanation,
            impact_analysis=best_impact_analysis,
            summary=best_summary,
            risk=best_risk,
            impact=best_impact,
            fix_code=best_fix_code,
            fix_example=best_fix_example,
            full_example=best_full_example,
            best_practices=all_best_practices,
            documentation_url=best_documentation_url,
            ai_generated=any(f.ai_generated for f in findings),
        )


# ------------------------------------------------------------------
# Module-level convenience function
# ------------------------------------------------------------------

def deduplicate_findings(
    findings: list[RuleFinding],
) -> tuple[list[RuleFinding], DeduplicationStats]:
    """
    Convenience function to deduplicate findings and return stats.

    Args:
        findings: List of findings that may contain duplicates.

    Returns:
        A tuple of (deduplicated findings list, deduplication stats).
    """
    deduplicator = FindingsDeduplicator()
    return deduplicator.deduplicate(findings)
