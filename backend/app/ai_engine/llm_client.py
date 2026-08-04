"""LLM Client for AI-powered explanations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AIExplanation:
    """AI-generated explanation for a finding."""

    finding_id: str
    explanation: str
    impact_analysis: str
    remediation_steps: list[str]
    confidence: float = 0.9


@dataclass
class AISummary:
    """AI-generated summary."""

    executive_summary: str
    risk_analysis: str
    prioritized_recommendations: list[str]


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_explanation(
        self,
        finding_description: str,
        context: dict[str, Any],
    ) -> AIExplanation:
        """Generate AI explanation for a finding."""
        pass

    @abstractmethod
    async def generate_executive_summary(
        self,
        findings: list[dict[str, Any]],
        scores: dict[str, float],
    ) -> str:
        """Generate executive summary for the report."""
        pass

    @abstractmethod
    async def generate_risk_analysis(
        self,
        findings: list[dict[str, Any]],
    ) -> str:
        """Generate risk analysis for the findings."""
        pass

    @abstractmethod
    async def generate_prioritized_recommendations(
        self,
        findings: list[dict[str, Any]],
    ) -> list[str]:
        """Generate prioritized list of recommendations."""
        pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load Gemini client."""
        if self._client is None:
            from google.genai import Client
            self._client = Client(api_key=self.api_key)
        return self._client

    async def generate_explanation(
        self,
        finding_description: str,
        context: dict[str, Any],
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
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
            )

            import json
            content = response.text
            data = json.loads(content)

            return AIExplanation(
                finding_id=context.get("rule_id", ""),
                explanation=data.get("explanation", ""),
                impact_analysis=data.get("impact_analysis", ""),
                remediation_steps=data.get("remediation_steps", []),
                confidence=0.9,
            )
        except Exception as e:
            logger.warning("Gemini explanation generation failed", error=str(e))
            return self._fallback_explanation(context)

    async def generate_executive_summary(
        self,
        findings: list[dict[str, Any]],
        scores: dict[str, float],
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
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
            )

            return response.text
        except Exception as e:
            logger.warning("Executive summary generation failed", error=str(e))
            return self._fallback_summary(scores)

    async def generate_risk_analysis(
        self,
        findings: list[dict[str, Any]],
    ) -> str:
        """Generate risk analysis."""
        prompt = f"""Analyze the following infrastructure findings and provide a risk assessment:

{self._format_all_findings(findings)}

Provide risk analysis covering:
1. Immediate risks (require urgent attention)
2. Medium-term risks (should be addressed in next sprint)
3. Long-term considerations (technical debt)"""

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
            )

            return response.text
        except Exception as e:
            logger.warning("Risk analysis generation failed", error=str(e))
            return "Risk analysis unavailable."

    async def generate_prioritized_recommendations(
        self,
        findings: list[dict[str, Any]],
    ) -> list[str]:
        """Generate prioritized recommendations."""
        prompt = f"""Based on these findings, provide the top 5 prioritized recommendations:

{self._format_all_findings(findings)}

List recommendations in order of priority (most critical first)."""

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
            )

            content = response.text
            recommendations = []
            for line in content.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    recommendations.append(line.lstrip("0123456789.- ").strip())

            return recommendations[:5]
        except Exception as e:
            logger.warning("Recommendations generation failed", error=str(e))
            return self._fallback_recommendations(findings)

    def _format_findings(self, findings: list[dict], severity: str) -> str:
        """Format findings by severity."""
        filtered = [f for f in findings if f.get("severity") == severity]
        if not filtered:
            return "None"

        return "\n".join([
            f"- {f.get('rule_name')}: {f.get('description')}"
            for f in filtered[:10]
        ])

    def _format_all_findings(self, findings: list[dict]) -> str:
        """Format all findings."""
        return "\n".join([
            f"[{f.get('severity').upper()}] {f.get('rule_name')}: {f.get('description')}"
            for f in findings[:20]
        ])

    def _fallback_explanation(self, context: dict) -> AIExplanation:
        """Fallback explanation when LLM fails."""
        return AIExplanation(
            finding_id=context.get("rule_id", ""),
            explanation=context.get("description", "No detailed explanation available."),
            impact_analysis="This issue may affect system reliability, security, or cost.",
            remediation_steps=["Review the recommendation", "Consult documentation", "Test changes in staging"],
            confidence=0.5,
        )

    def _fallback_summary(self, scores: dict) -> str:
        """Fallback summary when LLM fails."""
        overall = sum(scores.values()) / len(scores) if scores else 0
        return f"""Production Readiness Assessment

Overall Score: {overall:.1f}/100

Category Scores:
{chr(10).join(f'- {k}: {v:.1f}' for k, v in scores.items())}

Please review individual findings for specific recommendations."""

    def _fallback_recommendations(self, findings: list[dict]) -> list[str]:
        """Fallback recommendations when LLM fails."""
        critical = [f for f in findings if f.get("severity") == "critical"]
        high = [f for f in findings if f.get("severity") == "high"]

        recommendations = []
        for f in critical[:3]:
            recommendations.append(f"CRITICAL: {f.get('recommendation')}")
        for f in high[:2]:
            recommendations.append(f"HIGH: {f.get('recommendation')}")

        return recommendations


class MistralProvider(BaseLLMProvider):
    """Mistral AI LLM provider."""

    def __init__(self, api_key: str, model: str = "mistral-large-latest"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load Mistral client."""
        if self._client is None:
            try:
                from mistralai.client import Mistral
            except ImportError:
                from mistralai import Mistral
            self._client = Mistral(api_key=self.api_key)
        return self._client

    async def generate_explanation(
        self,
        finding_description: str,
        context: dict[str, Any],
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
            response = await self.client.chat.complete_async(
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
            logger.warning("Mistral explanation generation failed", error=str(e))
            return self._fallback_explanation(context)

    async def generate_executive_summary(
        self,
        findings: list[dict[str, Any]],
        scores: dict[str, float],
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
            response = await self.client.chat.complete_async(
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
        findings: list[dict[str, Any]],
    ) -> str:
        """Generate risk analysis."""
        prompt = f"""Analyze the following infrastructure findings and provide a risk assessment:

{self._format_all_findings(findings)}

Provide risk analysis covering:
1. Immediate risks (require urgent attention)
2. Medium-term risks (should be addressed in next sprint)
3. Long-term considerations (technical debt)"""

        try:
            response = await self.client.chat.complete_async(
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
        findings: list[dict[str, Any]],
    ) -> list[str]:
        """Generate prioritized recommendations."""
        prompt = f"""Based on these findings, provide the top 5 prioritized recommendations:

{self._format_all_findings(findings)}

List recommendations in order of priority (most critical first)."""

        try:
            response = await self.client.chat.complete_async(
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
            recommendations = []
            for line in content.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    recommendations.append(line.lstrip("0123456789.- ").strip())

            return recommendations[:5]
        except Exception as e:
            logger.warning("Recommendations generation failed", error=str(e))
            return self._fallback_recommendations(findings)

    def _format_findings(self, findings: list[dict], severity: str) -> str:
        """Format findings by severity."""
        filtered = [f for f in findings if f.get("severity") == severity]
        if not filtered:
            return "None"

        return "\n".join([
            f"- {f.get('rule_name')}: {f.get('description')}"
            for f in filtered[:10]
        ])

    def _format_all_findings(self, findings: list[dict]) -> str:
        """Format all findings."""
        return "\n".join([
            f"[{f.get('severity').upper()}] {f.get('rule_name')}: {f.get('description')}"
            for f in findings[:20]
        ])

    def _fallback_explanation(self, context: dict) -> AIExplanation:
        """Fallback explanation when LLM fails."""
        return AIExplanation(
            finding_id=context.get("rule_id", ""),
            explanation=context.get("description", "No detailed explanation available."),
            impact_analysis="This issue may affect system reliability, security, or cost.",
            remediation_steps=["Review the recommendation", "Consult documentation", "Test changes in staging"],
            confidence=0.5,
        )

    def _fallback_summary(self, scores: dict) -> str:
        """Fallback summary when LLM fails."""
        overall = sum(scores.values()) / len(scores) if scores else 0
        return f"""Production Readiness Assessment

Overall Score: {overall:.1f}/100

Category Scores:
{chr(10).join(f'- {k}: {v:.1f}' for k, v in scores.items())}

Please review individual findings for specific recommendations."""

    def _fallback_recommendations(self, findings: list[dict]) -> list[str]:
        """Fallback recommendations when LLM fails."""
        critical = [f for f in findings if f.get("severity") == "critical"]
        high = [f for f in findings if f.get("severity") == "high"]

        recommendations = []
        for f in critical[:3]:
            recommendations.append(f"CRITICAL: {f.get('recommendation')}")
        for f in high[:2]:
            recommendations.append(f"HIGH: {f.get('recommendation')}")

        return recommendations


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
        context: dict[str, Any],
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
        findings: list[dict[str, Any]],
        scores: dict[str, float],
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
        findings: list[dict[str, Any]],
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
        findings: list[dict[str, Any]],
    ) -> list[str]:
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

    def _format_findings(self, findings: list[dict], severity: str) -> str:
        """Format findings by severity."""
        filtered = [f for f in findings if f.get("severity") == severity]
        if not filtered:
            return "None"

        return "\n".join([
            f"- {f.get('rule_name')}: {f.get('description')}"
            for f in filtered[:10]
        ])

    def _format_all_findings(self, findings: list[dict]) -> str:
        """Format all findings."""
        return "\n".join([
            f"[{f.get('severity').upper()}] {f.get('rule_name')}: {f.get('description')}"
            for f in findings[:20]
        ])

    def _fallback_explanation(self, context: dict) -> AIExplanation:
        """Fallback explanation when LLM fails."""
        return AIExplanation(
            finding_id=context.get("rule_id", ""),
            explanation=context.get("description", "No detailed explanation available."),
            impact_analysis="This issue may affect system reliability, security, or cost.",
            remediation_steps=["Review the recommendation", "Consult documentation", "Test changes in staging"],
            confidence=0.5,
        )

    def _fallback_summary(self, scores: dict) -> str:
        """Fallback summary when LLM fails."""
        overall = sum(scores.values()) / len(scores) if scores else 0
        return f"""Production Readiness Assessment

Overall Score: {overall:.1f}/100

Category Scores:
{chr(10).join(f'- {k}: {v:.1f}' for k, v in scores.items())}

Please review individual findings for specific recommendations."""

    def _fallback_recommendations(self, findings: list[dict]) -> list[str]:
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
        context: dict[str, Any],
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
        findings: list[dict[str, Any]],
        scores: dict[str, float],
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

    async def generate_risk_analysis(self, findings: list[dict[str, Any]]) -> str:
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
        findings: list[dict[str, Any]],
    ) -> list[str]:
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


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider (self-hosted via ``ollama serve``).

    Talks to the Ollama HTTP API with a health check, per-request timeouts,
    automatic retries with backoff, optional streaming and structured logging.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        stream: bool | None = None,
    ):
        from app.ai_engine.local_llm import OllamaClient

        self._llm_client = OllamaClient(
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            stream=stream,
        )
        self.model = self._llm_client.model
        self.base_url = self._llm_client.base_url

    async def generate(self, prompt: str, max_tokens: int | None = None) -> str:
        """Generate a raw completion for ``prompt`` via the Ollama API."""
        return await self._llm_client.generate(prompt, max_tokens=max_tokens)

    async def health_check(self) -> bool:
        """Return True when the configured Ollama server is reachable."""
        return await self._llm_client.health_check()

    async def generate_explanation(
        self,
        finding_description: str,
        context: dict[str, Any],
    ) -> AIExplanation:
        """Generate a detailed explanation for a finding."""
        prompt = _local_explanation_prompt(finding_description, context)
        try:
            response = await self.generate(prompt, max_tokens=1000)
            data = _extract_json_object(response)
            return AIExplanation(
                finding_id=context.get("rule_id", ""),
                explanation=data.get("explanation", finding_description),
                impact_analysis=data.get("impact_analysis", "This issue may affect system reliability, security, or cost."),
                remediation_steps=data.get("remediation_steps", ["Review the recommendation", "Consult documentation", "Test changes in staging"]),
                confidence=0.85,
            )
        except Exception as e:
            logger.warning("Ollama explanation generation failed", error=str(e))
            return _local_fallback_explanation(context)

    async def generate_executive_summary(
        self,
        findings: list[dict[str, Any]],
        scores: dict[str, float],
    ) -> str:
        """Generate an executive summary."""
        prompt = _local_summary_prompt(findings, scores)
        try:
            return await self.generate(prompt, max_tokens=800)
        except Exception as e:
            logger.warning("Ollama executive summary failed", error=str(e))
            return _local_fallback_summary(scores)

    async def generate_risk_analysis(self, findings: list[dict[str, Any]]) -> str:
        """Generate a risk analysis for the findings."""
        prompt = _local_risk_prompt(findings)
        try:
            return await self.generate(prompt, max_tokens=1000)
        except Exception as e:
            logger.warning("Ollama risk analysis failed", error=str(e))
            return "Risk analysis unavailable."

    async def generate_prioritized_recommendations(
        self,
        findings: list[dict[str, Any]],
    ) -> list[str]:
        """Generate prioritized recommendations."""
        prompt = _local_recommendations_prompt(findings)
        try:
            response = await self.generate(prompt, max_tokens=500)
            return _parse_bulleted_response(response)[:5]
        except Exception as e:
            logger.warning("Ollama recommendations failed", error=str(e))
            return _local_fallback_recommendations(findings)

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._llm_client.aclose()


class GPT4AllProvider(BaseLLMProvider):
    """GPT4All local LLM provider.

    Uses the ``gpt4all`` Python bindings with lazy model loading, a process-wide
    singleton model, thread-safe inference and explicit cleanup.
    """

    def __init__(
        self,
        model: str | None = None,
        model_path: str | None = None,
        threads: int | None = None,
        max_tokens: int | None = None,
    ):
        from app.ai_engine.local_llm import GPT4AllModel

        self._llm_client = GPT4AllModel(
            model=model,
            model_path=model_path,
            threads=threads,
            max_tokens=max_tokens,
        )
        self.model = self._llm_client.model_name

    async def generate(self, prompt: str, max_tokens: int | None = None) -> str:
        """Generate a raw completion for ``prompt`` (inference in a thread)."""
        return await self._llm_client.agenerate(prompt, max_tokens=max_tokens)

    async def generate_explanation(
        self,
        finding_description: str,
        context: dict[str, Any],
    ) -> AIExplanation:
        """Generate a detailed explanation for a finding."""
        prompt = _local_explanation_prompt(finding_description, context)
        try:
            response = await self.generate(prompt, max_tokens=1000)
            data = _extract_json_object(response)
            return AIExplanation(
                finding_id=context.get("rule_id", ""),
                explanation=data.get("explanation", finding_description),
                impact_analysis=data.get("impact_analysis", "This issue may affect system reliability, security, or cost."),
                remediation_steps=data.get("remediation_steps", ["Review the recommendation", "Consult documentation", "Test changes in staging"]),
                confidence=0.8,
            )
        except Exception as e:
            logger.warning("GPT4All explanation generation failed", error=str(e))
            return _local_fallback_explanation(context)

    async def generate_executive_summary(
        self,
        findings: list[dict[str, Any]],
        scores: dict[str, float],
    ) -> str:
        """Generate an executive summary."""
        prompt = _local_summary_prompt(findings, scores)
        try:
            return await self.generate(prompt, max_tokens=800)
        except Exception as e:
            logger.warning("GPT4All executive summary failed", error=str(e))
            return _local_fallback_summary(scores)

    async def generate_risk_analysis(self, findings: list[dict[str, Any]]) -> str:
        """Generate a risk analysis for the findings."""
        prompt = _local_risk_prompt(findings)
        try:
            return await self.generate(prompt, max_tokens=1000)
        except Exception as e:
            logger.warning("GPT4All risk analysis failed", error=str(e))
            return "Risk analysis unavailable."

    async def generate_prioritized_recommendations(
        self,
        findings: list[dict[str, Any]],
    ) -> list[str]:
        """Generate prioritized recommendations."""
        prompt = _local_recommendations_prompt(findings)
        try:
            response = await self.generate(prompt, max_tokens=500)
            return _parse_bulleted_response(response)[:5]
        except Exception as e:
            logger.warning("GPT4All recommendations failed", error=str(e))
            return _local_fallback_recommendations(findings)

    async def close(self) -> None:
        """Release the cached GPT4All model from memory."""
        self._llm_client.close()


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing/development."""

    async def generate_explanation(
        self,
        finding_description: str,
        context: dict[str, Any],
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
        findings: list[dict[str, Any]],
        scores: dict[str, float],
    ) -> str:
        return f"Executive Summary: Overall score {sum(scores.values()) / len(scores) if scores else 0:.1f}/100"

    async def generate_risk_analysis(self, findings: list[dict[str, Any]]) -> str:
        return f"Risk Analysis: {len(findings)} findings detected"

    async def generate_prioritized_recommendations(
        self,
        findings: list[dict[str, Any]],
    ) -> list[str]:
        return [f.get("recommendation") for f in findings[:5]]


def get_llm_provider() -> BaseLLMProvider:
    """Factory function to get configured LLM provider with fallback chain."""
    provider = settings.LLM_PROVIDER.lower()

    # Try configured provider first
    if provider == "openai" and settings.OPENAI_API_KEY:
        logger.info("Using OpenAI LLM provider")
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL,
        )
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        logger.info("Using Anthropic LLM provider")
        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.LLM_MODEL,
        )
    elif provider == "gemini" and settings.GEMINI_API_KEY:
        logger.info("Using Gemini LLM provider")
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.LLM_MODEL if settings.LLM_MODEL != "gpt-4-turbo-preview" else "gemini-pro",
        )
    elif provider == "mistral" and settings.MISTRAL_API_KEY:
        logger.info("Using Mistral LLM provider")
        # Use correct Mistral model, not the configured LLM_MODEL which might be for another provider
        mistral_model = "mistral-large-latest"
        if settings.LLM_MODEL and settings.LLM_MODEL not in ["gpt-4-turbo-preview", "gemini-pro"]:
            mistral_model = settings.LLM_MODEL
        return MistralProvider(
            api_key=settings.MISTRAL_API_KEY,
            model=mistral_model,
        )
    elif provider == "ollama":
        logger.info("Using Ollama local LLM provider")
        return OllamaProvider()
    elif provider == "gpt4all":
        logger.info("Using GPT4All local LLM provider")
        return GPT4AllProvider()
    else:
        # Fallback chain: try available providers in order
        if settings.OPENAI_API_KEY:
            logger.info("Using OpenAI LLM provider (fallback)")
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY)
        elif settings.ANTHROPIC_API_KEY:
            logger.info("Using Anthropic LLM provider (fallback)")
            return AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY)
        elif settings.GEMINI_API_KEY:
            logger.info("Using Gemini LLM provider (fallback)")
            return GeminiProvider(api_key=settings.GEMINI_API_KEY)
        elif settings.MISTRAL_API_KEY:
            logger.info("Using Mistral LLM provider (fallback)")
            # Use correct Mistral model, not the configured LLM_MODEL which might be for another provider
            mistral_model = "mistral-large-latest"
            if settings.LLM_MODEL and settings.LLM_MODEL not in ["gpt-4-turbo-preview", "gemini-pro"]:
                mistral_model = settings.LLM_MODEL
            return MistralProvider(api_key=settings.MISTRAL_API_KEY, model=mistral_model)
        else:
            logger.warning("No LLM API keys configured, using Mock provider")
            return MockLLMProvider()


# ---------------------------------------------------------------------------
# Shared helpers for local LLM providers (Ollama / GPT4All)
# ---------------------------------------------------------------------------


def _extract_json_object(text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM response."""
    import json

    stripped = (text or "").strip()
    if stripped.startswith("```"):
        parts = stripped.split("```")
        if len(parts) >= 2:
            stripped = parts[1]
        if stripped.startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end < start:
        return {}
    try:
        parsed = json.loads(stripped[start : end + 1])
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_bulleted_response(text: str) -> list[str]:
    """Parse a numbered or bulleted list out of an LLM response."""
    items: list[str] = []
    for line in (text or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        if line[0].isdigit() or line.startswith(("-", "*")):
            items.append(line.lstrip("0123456789.-* ").strip())
    return items


def _local_explanation_prompt(finding_description: str, context: dict[str, Any]) -> str:
    return (
        "You are a DevOps expert analyzing infrastructure issues.\n\n"
        f"Finding: {finding_description}\n"
        f"Context: {context}\n\n"
        "Provide a detailed explanation including:\n"
        "1. What this issue means in practical terms\n"
        "2. The potential impact on security, reliability, or cost\n"
        "3. Specific steps to remediate this issue\n\n"
        "Format your response as JSON with keys: explanation, impact_analysis, remediation_steps"
    )


def _local_summary_prompt(findings: list[dict[str, Any]], scores: dict[str, float]) -> str:
    critical = [f for f in findings if f.get("severity") == "critical"][:10]
    high = [f for f in findings if f.get("severity") == "high"][:10]
    return (
        "You are a DevOps consultant providing an executive summary.\n\n"
        f"Overall Scores:\n{scores}\n\n"
        f"Critical Findings:\n{chr(10).join('- ' + str(f.get('rule_name')) + ': ' + str(f.get('description')) for f in critical) or 'None'}\n\n"
        f"High Severity Findings:\n{chr(10).join('- ' + str(f.get('rule_name')) + ': ' + str(f.get('description')) for f in high) or 'None'}\n\n"
        "Write a concise executive summary (3-4 paragraphs) covering:\n"
        "1. Overall production readiness assessment\n"
        "2. Key risk areas\n"
        "3. Priority recommendations"
    )


def _local_risk_prompt(findings: list[dict[str, Any]]) -> str:
    formatted = "\n".join(
        f"[{str(f.get('severity', 'unknown')).upper()}] {f.get('rule_name')}: {f.get('description')}"
        for f in findings[:20]
    )
    return (
        "Analyze the following infrastructure findings and provide a risk assessment:\n\n"
        f"{formatted}\n\n"
        "Provide risk analysis covering:\n"
        "1. Immediate risks (require urgent attention)\n"
        "2. Medium-term risks (should be addressed in next sprint)\n"
        "3. Long-term considerations (technical debt)"
    )


def _local_recommendations_prompt(findings: list[dict[str, Any]]) -> str:
    formatted = "\n".join(
        f"[{str(f.get('severity', 'unknown')).upper()}] {f.get('rule_name')}: {f.get('description')}"
        for f in findings[:20]
    )
    return (
        "Based on these findings, provide the top 5 prioritized recommendations:\n\n"
        f"{formatted}\n\n"
        "List recommendations in order of priority (most critical first)."
    )


def _local_fallback_explanation(context: dict[str, Any]) -> AIExplanation:
    return AIExplanation(
        finding_id=context.get("rule_id", ""),
        explanation=context.get("description", "No detailed explanation available."),
        impact_analysis="This issue may affect system reliability, security, or cost.",
        remediation_steps=["Review the recommendation", "Consult documentation", "Test changes in staging"],
        confidence=0.5,
    )


def _local_fallback_summary(scores: dict[str, float]) -> str:
    overall = sum(scores.values()) / len(scores) if scores else 0
    return f"""Production Readiness Assessment

Overall Score: {overall:.1f}/100

Category Scores:
{chr(10).join(f'- {k}: {v:.1f}' for k, v in scores.items())}

Please review individual findings for specific recommendations."""


def _local_fallback_recommendations(findings: list[dict[str, Any]]) -> list[str]:
    critical = [f for f in findings if f.get("severity") == "critical"]
    high = [f for f in findings if f.get("severity") == "high"]
    recommendations = [f"CRITICAL: {f.get('recommendation')}" for f in critical[:3]]
    recommendations += [f"HIGH: {f.get('recommendation')}" for f in high[:2]]
    return recommendations
