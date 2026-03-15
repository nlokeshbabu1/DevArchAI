"""Findings deduplication engine."""

from collections import defaultdict

import structlog

from app.rule_engine.base import RuleFinding

logger = structlog.get_logger(__name__)


class FindingsDeduplicator:
    """Deduplicate findings by rule_id, file, and resource."""

    def __init__(self):
        self._dedup_key_fields = ["rule_id", "file_path", "resource_name"]

    def _create_dedup_key(self, finding: RuleFinding) -> str:
        """Create a deduplication key from finding attributes."""
        parts = []
        for field in self._dedup_key_fields:
            value = getattr(finding, field, None) or ""
            parts.append(str(value))
        return "|".join(parts)

    def deduplicate(self, findings: list[RuleFinding]) -> list[RuleFinding]:
        """
        Deduplicate findings by grouping on rule_id, file_path, and resource_name.

        When duplicates are found:
        - Keep the first finding
        - Aggregate metadata (count of occurrences, all affected files)
        - Enhance description with occurrence count

        Args:
            findings: List of findings that may contain duplicates

        Returns:
            Deduplicated list of findings with aggregated metadata
        """
        if not findings:
            return []

        # Group findings by dedup key
        grouped: dict[str, list[RuleFinding]] = defaultdict(list)

        for finding in findings:
            key = self._create_dedup_key(finding)
            grouped[key].append(finding)

        deduplicated = []

        for key, group in grouped.items():
            if len(group) == 1:
                # No duplicates, keep as-is
                deduplicated.append(group[0])
            else:
                # Duplicates found - merge them
                merged = self._merge_findings(group)
                deduplicated.append(merged)

        logger.info(
            "Findings deduplicated",
            original_count=len(findings),
            deduplicated_count=len(deduplicated),
            removed_count=len(findings) - len(deduplicated),
        )

        return deduplicated

    def _merge_findings(self, findings: list[RuleFinding]) -> RuleFinding:
        """
        Merge multiple duplicate findings into one.

        Args:
            findings: List of duplicate findings

        Returns:
            Single merged finding with aggregated metadata
        """
        primary = findings[0]

        # Collect all affected files/resources
        all_files = set()
        all_resources = set()
        for f in findings:
            if f.file_path:
                all_files.add(f.file_path)
            if f.resource_name:
                all_resources.add(f.resource_name)

        # Build aggregated description
        occurrence_count = len(findings)
        if occurrence_count > 1:
            # Enhance description with count
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
        merged_metadata = {
            **primary.metadata,
            "occurrence_count": occurrence_count,
            "affected_files": list(all_files),
            "affected_resources": list(all_resources),
        }

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
            confidence=primary.confidence,
            metadata=merged_metadata,
            ai_explanation=primary.ai_explanation,
            impact_analysis=primary.impact_analysis,
            risk=primary.risk,
            impact=primary.impact,
            fix_example=primary.fix_example,
        )


def deduplicate_findings(findings: list[RuleFinding]) -> list[RuleFinding]:
    """Convenience function to deduplicate findings."""
    deduplicator = FindingsDeduplicator()
    return deduplicator.deduplicate(findings)
