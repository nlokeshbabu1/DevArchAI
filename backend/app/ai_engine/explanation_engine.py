"""Explanation engine for AI-powered analysis."""

from typing import Any

from app.ai_engine.llm_client import AIExplanation, BaseLLMProvider, get_llm_provider
from app.core.logging import get_logger
from app.rule_engine.base import RuleFinding

logger = get_logger(__name__)


class ExplanationEngine:
    """Engine for generating AI explanations for findings."""

    def __init__(self, llm_provider: BaseLLMProvider | None = None):
        self.llm_provider = llm_provider or get_llm_provider()
        self._explanation_cache: dict[str, AIExplanation] = {}

    async def explain_finding(
        self,
        finding: RuleFinding,
        use_cache: bool = True,
    ) -> RuleFinding:
        """
        Add AI explanation to a finding.

        Args:
            finding: The rule finding to explain
            use_cache: Whether to use cached explanations

        Returns:
            Finding with AI explanations added
        """
        # Check cache first
        cache_key = f"{finding.rule_id}:{finding.description}"
        if use_cache and cache_key in self._explanation_cache:
            explanation = self._explanation_cache[cache_key]
            finding.ai_explanation = explanation.explanation
            finding.impact_analysis = explanation.impact_analysis
            finding.recommendation = "; ".join(explanation.remediation_steps) or finding.recommendation
            return finding

        # Generate new explanation
        try:
            context = {
                "rule_id": finding.rule_id,
                "category": finding.category.value,
                "severity": finding.severity.value,
                "file_path": finding.file_path,
                "resource_name": finding.resource_name,
            }

            explanation = await self.llm_provider.generate_explanation(
                finding.description,
                context,
            )

            # Cache the explanation
            if use_cache:
                self._explanation_cache[cache_key] = explanation

            # Apply to finding
            finding.ai_explanation = explanation.explanation
            finding.impact_analysis = explanation.impact_analysis
            if explanation.remediation_steps:
                finding.recommendation = "; ".join(explanation.remediation_steps)

            logger.debug(
                "Generated AI explanation",
                rule_id=finding.rule_id,
                confidence=explanation.confidence,
            )

        except Exception as e:
            logger.warning(
                "Failed to generate AI explanation",
                rule_id=finding.rule_id,
                error=str(e),
            )

        return finding

    async def explain_findings_batch(
        self,
        findings: list[RuleFinding],
        max_findings: int = 20,
        use_cache: bool = True,
    ) -> list[RuleFinding]:
        """
        Add AI explanations to multiple findings.

        Args:
            findings: List of findings to explain
            max_findings: Maximum number of findings to process
            use_cache: Whether to use cached explanations

        Returns:
            List of findings with AI explanations
        """
        # Sort by severity (critical first)
        severity_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "info": 4,
        }
        sorted_findings = sorted(
            findings,
            key=lambda f: severity_order.get(f.severity.value, 5),
        )

        # Process top findings
        findings_to_process = sorted_findings[:max_findings]

        logger.info(
            "Generating AI explanations",
            total_findings=len(findings),
            processing_count=len(findings_to_process),
        )

        explained_findings = []
        for finding in findings_to_process:
            explained = await self.explain_finding(finding, use_cache)
            explained_findings.append(explained)

        # Add remaining findings without explanations
        explained_findings.extend(sorted_findings[max_findings:])

        logger.info(
            "AI explanation complete",
            explained_count=len(findings_to_process),
        )

        return explained_findings

    async def generate_report_summary(
        self,
        findings: list[RuleFinding],
        scores: dict[str, float],
    ) -> dict[str, Any]:
        """
        Generate AI summary for a complete report.

        Args:
            findings: List of all findings
            scores: Category scores

        Returns:
            Dictionary with executive_summary, risk_analysis, prioritized_recommendations
        """
        # Convert findings to dict format
        findings_dict = [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity.value,
                "category": f.category.value,
                "description": f.description,
                "recommendation": f.recommendation,
                "file_path": f.file_path,
            }
            for f in findings
        ]

        # Generate components in parallel
        executive_summary_task = self.llm_provider.generate_executive_summary(
            findings_dict, scores
        )
        risk_analysis_task = self.llm_provider.generate_risk_analysis(findings_dict)
        recommendations_task = self.llm_provider.generate_prioritized_recommendations(
            findings_dict
        )

        executive_summary, risk_analysis, prioritized_recommendations = await asyncio.gather(
            executive_summary_task,
            risk_analysis_task,
            recommendations_task,
            return_exceptions=True,
        )

        # Handle exceptions
        if isinstance(executive_summary, Exception):
            executive_summary = f"Overall Score: {sum(scores.values()) / len(scores) if scores else 0:.1f}/100"
        if isinstance(risk_analysis, Exception):
            risk_analysis = "Risk analysis unavailable."
        if isinstance(prioritized_recommendations, Exception):
            prioritized_recommendations = [f.recommendation for f in findings[:5]]

        return {
            "executive_summary": executive_summary,
            "risk_analysis": risk_analysis,
            "prioritized_recommendations": prioritized_recommendations,
        }

    def clear_cache(self) -> None:
        """Clear the explanation cache."""
        self._explanation_cache.clear()
        logger.info("Explanation cache cleared")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "cached_explanations": len(self._explanation_cache),
        }


# Import asyncio for batch operations
import asyncio
