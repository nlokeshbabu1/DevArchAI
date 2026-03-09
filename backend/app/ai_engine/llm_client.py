"""LLM Client for AI-powered explanations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import structlog

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AIExplanation:
    """AI-generated explanation for a finding."""

    finding_id: str
    explanation: str
    impact_analysis: str
    remediation_steps: List[str]
    confidence: float = 0.9


@dataclass
class AISummary:
    """AI-generated summary."""

    executive_summary: str
    risk_analysis: str
    prioritized_recommendations: List[str]


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_explanation(
        self,
        finding_description: str,
        context: Dict[str, Any],
    ) -> AIExplanation:
        """Generate AI explanation for a finding."""
        pass

    @abstractmethod
    async def generate_executive_summary(
        self,
        findings: List[Dict[str, Any]],
        scores: Dict[str, float],
    ) -> str:
        """Generate executive summary for the report."""
        pass

    @abstractmethod
    async def generate_risk_analysis(
        self,
        findings: List[Dict[str, Any]],
    ) -> str:
        """Generate risk analysis for the findings."""
        pass

    @abstractmethod
    async def generate_prioritized_recommendations(
        self,
        findings: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate prioritized list of recommendations."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate_explanation(
        self,
        finding_description: str,
        context: Dict[str, Any],
    ) -> AIExplanation:
        """Generate detailed explanation for a finding."""
        prompt = f"""You are a DevOps expert analyzing infrastructure issues.

Finding: {finding_description}
Context: {context}

Provide a detailed explanation including:
1. What this issue means in practical terms
2. The potential impact on security, reliability, or cost
3. Specific steps to remediate this issue

Format your response as JSON with keys: explanation, impact_analysis, remediation_steps"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a DevOps infrastructure expert. Provide clear, actionable explanations.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            import json
            content = response.choices[0].message.content
            data = json.loads(content)

            return AIExplanation(
                finding_id=context.get("rule_id", ""),
                explanation=data.get("explanation", ""),
                impact_analysis=data.get("impact_analysis", ""),
                remediation_steps=data.get("remediation_steps", []),
                confidence=0.9,
            )
        except Exception as e:
            logger.warning("OpenAI explanation generation failed", error=str(e))
            return self._fallback_explanation(context)

    async def generate_executive_summary(
        self,
        findings: List[Dict[str, Any]],
        scores: Dict[str, float],
    ) -> str:
        """Generate executive summary."""
        prompt = f"""You are a DevOps consultant providing an executive summary.

Overall Scores:
{scores}

Critical Findings:
{self._format_findings(findings, "critical")}

High Severity Findings:
{self._format_findings(findings, "high")}

Write a concise executive summary (3-4 paragraphs) covering:
1. Overall production readiness assessment
2. Key risk areas
3. Priority recommendations"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a DevOps consultant. Write clear executive summaries.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=800,
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.warning("Executive summary generation failed", error=str(e))
            return self._fallback_summary(scores)

    async def generate_risk_analysis(
        self,
        findings: List[Dict[str, Any]],
    ) -> str:
        """Generate risk analysis."""
        prompt = f"""Analyze the following infrastructure findings and provide a risk assessment:

{self._format_all_findings(findings)}

Provide risk analysis covering:
1. Immediate risks (require urgent attention)
2. Medium-term risks (should be addressed in next sprint)
3. Long-term considerations (technical debt)"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a risk assessment expert."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.warning("Risk analysis generation failed", error=str(e))
            return "Risk analysis unavailable."

    async def generate_prioritized_recommendations(
        self,
        findings: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate prioritized recommendations."""
        prompt = f"""Based on these findings, provide the top 5 prioritized recommendations:

{self._format_all_findings(findings)}

List recommendations in order of priority (most critical first)."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a DevOps prioritization expert.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            content = response.choices[0].message.content
            # Parse numbered list
            recommendations = []
            for line in content.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    recommendations.append(line.lstrip("0123456789.- ").strip())

            return recommendations[:5]
        except Exception as e:
            logger.warning("Recommendations generation failed", error=str(e))
            return self._fallback_recommendations(findings)

    def _format_findings(self, findings: List[Dict], severity: str) -> str:
        """Format findings by severity."""
        filtered = [f for f in findings if f.get("severity") == severity]
        if not filtered:
            return "None"

        return "\n".join([
            f"- {f.get('rule_name')}: {f.get('description')}"
            for f in filtered[:10]
        ])

    def _format_all_findings(self, findings: List[Dict]) -> str:
        """Format all findings."""
        return "\n".join([
            f"[{f.get('severity').upper()}] {f.get('rule_name')}: {f.get('description')}"
            for f in findings[:20]
        ])

    def _fallback_explanation(self, context: Dict) -> AIExplanation:
        """Fallback explanation when LLM fails."""
        return AIExplanation(
            finding_id=context.get("rule_id", ""),
            explanation=context.get("description", "No detailed explanation available."),
            impact_analysis="This issue may affect system reliability, security, or cost.",
            remediation_steps=["Review the recommendation", "Consult documentation", "Test changes in staging"],
            confidence=0.5,
        )

    def _fallback_summary(self, scores: Dict) -> str:
        """Fallback summary when LLM fails."""
        overall = sum(scores.values()) / len(scores) if scores else 0
        return f"""Production Readiness Assessment

Overall Score: {overall:.1f}/100

Category Scores:
{chr(10).join(f'- {k}: {v:.1f}' for k, v in scores.items())}

Please review individual findings for specific recommendations."""

    def _fallback_recommendations(self, findings: List[Dict]) -> List[str]:
        """Fallback recommendations when LLM fails."""
        critical = [f for f in findings if f.get("severity") == "critical"]
        high = [f for f in findings if f.get("severity") == "high"]

        recommendations = []
        for f in critical[:3]:
            recommendations.append(f"CRITICAL: {f.get('recommendation')}")
        for f in high[:2]:
            recommendations.append(f"HIGH: {f.get('recommendation')}")

        return recommendations


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider."""

    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load Anthropic client."""
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate_explanation(
        self,
        finding_description: str,
        context: Dict[str, Any],
    ) -> AIExplanation:
        """Generate explanation using Claude."""
        prompt = f"""You are a DevOps expert. Analyze this finding:

Finding: {finding_description}
Context: {context}

Provide JSON response with: explanation, impact_analysis, remediation_steps (array)"""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )

            import json
            content = response.content[0].text
            data = json.loads(content)

            return AIExplanation(
                finding_id=context.get("rule_id", ""),
                explanation=data.get("explanation", ""),
                impact_analysis=data.get("impact_analysis", ""),
                remediation_steps=data.get("remediation_steps", []),
                confidence=0.9,
            )
        except Exception as e:
            logger.warning("Anthropic explanation generation failed", error=str(e))
            return AIExplanation(
                finding_id=context.get("rule_id", ""),
                explanation=finding_description,
                impact_analysis="Impact analysis unavailable.",
                remediation_steps=["Review recommendation"],
                confidence=0.5,
            )

    async def generate_executive_summary(
        self,
        findings: List[Dict[str, Any]],
        scores: Dict[str, float],
    ) -> str:
        """Generate executive summary using Claude."""
        prompt = f"""Scores: {scores}
Findings: {findings[:10]}

Write a 3-paragraph executive summary."""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.warning("Summary generation failed", error=str(e))
            return f"Overall Score: {sum(scores.values()) / len(scores) if scores else 0:.1f}/100"

    async def generate_risk_analysis(self, findings: List[Dict[str, Any]]) -> str:
        """Generate risk analysis using Claude."""
        prompt = f"Analyze risks: {findings[:15]}"

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.warning("Risk analysis failed", error=str(e))
            return "Risk analysis unavailable."

    async def generate_prioritized_recommendations(
        self,
        findings: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate recommendations using Claude."""
        prompt = f"Top 5 recommendations for: {findings[:15]}"

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text
            return [line.strip() for line in content.split("\n") if line.strip()][:5]
        except Exception as e:
            logger.warning("Recommendations failed", error=str(e))
            return [f.get("recommendation") for f in findings[:5]]


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing/development."""

    async def generate_explanation(
        self,
        finding_description: str,
        context: Dict[str, Any],
    ) -> AIExplanation:
        return AIExplanation(
            finding_id=context.get("rule_id", ""),
            explanation=f"AI Explanation: {finding_description}",
            impact_analysis="This issue could impact production reliability.",
            remediation_steps=["Review the configuration", "Apply recommended changes", "Test thoroughly"],
            confidence=0.8,
        )

    async def generate_executive_summary(
        self,
        findings: List[Dict[str, Any]],
        scores: Dict[str, float],
    ) -> str:
        return f"Executive Summary: Overall score {sum(scores.values()) / len(scores) if scores else 0:.1f}/100"

    async def generate_risk_analysis(self, findings: List[Dict[str, Any]]) -> str:
        return f"Risk Analysis: {len(findings)} findings detected"

    async def generate_prioritized_recommendations(
        self,
        findings: List[Dict[str, Any]],
    ) -> List[str]:
        return [f.get("recommendation") for f in findings[:5]]


def get_llm_provider() -> BaseLLMProvider:
    """Factory function to get configured LLM provider."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL,
        )
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.LLM_MODEL,
        )
    else:
        logger.info("Using mock LLM provider")
        return MockLLMProvider()
