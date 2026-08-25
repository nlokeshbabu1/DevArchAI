"""
AI Explanation Layer - LLM Integration
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import structlog

from app.ai_engine.llm_client import (
    GPT4AllProvider as _GPT4AllProviderBase,
    OllamaProvider as _OllamaProviderBase,
)
from app.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class AIExplanation:
    """AI-generated explanation for a finding."""

    finding_id: str
    explanation: str
    impact_analysis: str
    remediation_steps: list[str]
    confidence: float


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
                    {"role": "system", "content": "You are a DevOps infrastructure expert. Provide clear, actionable explanations."},
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
                    {"role": "system", "content": "You are a DevOps consultant. Write clear executive summaries."},
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
                    {"role": "system", "content": "You are a DevOps prioritization expert."},
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

    async def generate(self, prompt: str) -> str:
        """Generate raw text response for batched remediation prompts."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a DevOps remediation assistant. Return only the requested content."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        return response.choices[0].message.content or ""

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

    async def generate(self, prompt: str) -> str:
        """Generate raw text response for batched remediation prompts."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


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
        """Generate explanation using Mistral."""
        prompt = f"""You are a DevOps expert. Analyze this finding:

Finding: {finding_description}
Context: {context}

Provide JSON response with: explanation, impact_analysis, remediation_steps (array)"""

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
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
        """Generate executive summary using Mistral."""
        prompt = f"""Scores: {scores}
Findings: {findings[:10]}

Write a 3-paragraph executive summary."""

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning("Mistral summary generation failed", error=str(e))
            return f"Overall Score: {sum(scores.values()) / len(scores) if scores else 0:.1f}/100"

    async def generate_risk_analysis(self, findings: list[dict[str, Any]]) -> str:
        """Generate risk analysis using Mistral."""
        prompt = f"Analyze risks: {findings[:15]}"

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning("Mistral risk analysis failed", error=str(e))
            return "Risk analysis unavailable."

    async def generate_prioritized_recommendations(
        self,
        findings: list[dict[str, Any]],
    ) -> list[str]:
        """Generate recommendations using Mistral."""
        prompt = f"Top 5 recommendations for: {findings[:15]}"

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content
            return [line.strip() for line in content.split("\n") if line.strip()][:5]
        except Exception as e:
            logger.warning("Mistral recommendations failed", error=str(e))
            return [f.get("recommendation") for f in findings[:5]]

    async def generate(self, prompt: str) -> str:
        """Generate raw text response - used by fix generator."""
        try:
            response = await asyncio.to_thread(
                self.client.chat.complete,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Mistral generation failed", error=str(e))
            raise


class OllamaProvider(_OllamaProviderBase, BaseLLMProvider):
    """Ollama local LLM provider (self-hosted via ``ollama serve``).

    Reuses the shared implementation from ``app.ai_engine.llm_client`` while
    satisfying this module's ``BaseLLMProvider`` interface.
    """


class GPT4AllProvider(_GPT4AllProviderBase, BaseLLMProvider):
    """GPT4All local LLM provider.

    Reuses the shared implementation from ``app.ai_engine.llm_client`` while
    satisfying this module's ``BaseLLMProvider`` interface.
    """


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


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider - Using new google-genai library."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load Gemini client using new google-genai library."""
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate_explanation(
        self,
        finding_description: str,
        context: dict[str, Any],
    ) -> AIExplanation:
        """Generate explanation using Gemini."""
        prompt = f"""You are a DevOps expert. Analyze this finding:

Finding: {finding_description}
Context: {context}

Provide JSON response with: explanation, impact_analysis, remediation_steps (array)

Respond ONLY with valid JSON."""

        try:
            # Use new google-genai library
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            import json
            content = response.text
            # Clean markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
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
        """Generate executive summary using Gemini."""
        prompt = f"""Scores: {scores}
Findings: {findings[:10]}

Write a 3-paragraph executive summary. Respond ONLY with the summary text."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.warning("Gemini summary generation failed", error=str(e))
            return f"Overall Score: {sum(scores.values()) / len(scores) if scores else 0:.1f}/100"

    async def generate_risk_analysis(self, findings: list[dict[str, Any]]) -> str:
        """Generate risk analysis using Gemini."""
        prompt = f"Analyze risks for these findings: {findings[:15]}. Respond ONLY with risk analysis text."

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.warning("Gemini risk analysis failed", error=str(e))
            return "Risk analysis unavailable."

    async def generate_prioritized_recommendations(
        self,
        findings: list[dict[str, Any]],
    ) -> list[str]:
        """Generate recommendations using Gemini."""
        prompt = f"Top 5 recommendations for: {findings[:15]}. Respond with numbered list."

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            content = response.text
            return [line.strip() for line in content.split("\n") if line.strip()][:5]
        except Exception as e:
            logger.warning("Gemini recommendations failed", error=str(e))
            return [f.get("recommendation") for f in findings[:5]]

    async def generate(self, prompt: str) -> str:
        """Generate raw text response - used by fix generator."""
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            logger.error("Gemini generation failed", error=str(e))
            raise



def _ollama_is_available() -> bool:
    """Probe the local Ollama server (short timeout; never raise)."""
    try:
        import urllib.request

        with urllib.request.urlopen(  # nosec B310 - fixed localhost probe, no user input
            "http://localhost:11434/api/tags", timeout=1
        ):
            return True
    except Exception:
        return False


def _gpt4all_is_available() -> bool:
    """Probe the local GPT4All API server (short timeout; never raise)."""
    try:
        import urllib.request

        with urllib.request.urlopen(  # nosec B310 - fixed localhost probe, no user input
            "http://localhost:4891/v1/models", timeout=1
        ):
            return True
    except Exception:
        return False


def _try_cloud_providers() -> BaseLLMProvider | None:
    """Return the first configured cloud LLM provider, or None."""
    if settings.OPENAI_API_KEY:
        logger.info("Using OpenAI LLM provider")
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL or "gpt-4-turbo-preview",
        )
    if settings.ANTHROPIC_API_KEY:
        logger.info("Using Anthropic LLM provider")
        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.LLM_MODEL or "claude-3-sonnet-20240229",
        )
    if settings.GEMINI_API_KEY:
        logger.info("Using Gemini LLM provider")
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.LLM_MODEL or "gemini-1.5-flash",
        )
    if settings.MISTRAL_API_KEY:
        logger.info("Using Mistral LLM provider")
        return MistralProvider(
            api_key=settings.MISTRAL_API_KEY,
            model=settings.MISTRAL_MODEL,
        )
    return None


def get_llm_provider() -> BaseLLMProvider:
    """Factory function to get configured LLM provider with automatic fallback.

    Priority order:
    1. Explicit LLM_PROVIDER when that provider is available (API key or local server)
    2. Cloud fallback chain: OpenAI -> Anthropic -> Gemini -> Mistral
    3. Local fallback: Ollama -> GPT4All (only when reachable)
    4. Mock (static examples)

    If LLM_PROVIDER is ``ollama``/``gpt4all`` but the local server is not running,
    cloud providers (including Mistral when MISTRAL_API_KEY is set) are used instead.
    """
    provider = settings.LLM_PROVIDER.lower()

    # Try configured cloud provider first (requires matching API key)
    if provider == "gemini" and settings.GEMINI_API_KEY:
        logger.info("Using Gemini LLM provider (configured)")
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.LLM_MODEL or "gemini-1.5-flash",
        )
    if provider == "openai" and settings.OPENAI_API_KEY:
        logger.info("Using OpenAI LLM provider (configured)")
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL or "gpt-4-turbo-preview",
        )
    if provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        logger.info("Using Anthropic LLM provider (configured)")
        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.LLM_MODEL or "claude-3-sonnet-20240229",
        )
    if provider == "mistral" and settings.MISTRAL_API_KEY:
        logger.info("Using Mistral LLM provider (configured)")
        return MistralProvider(
            api_key=settings.MISTRAL_API_KEY,
            model=settings.MISTRAL_MODEL,
        )

    # Local providers — only when the server/process is actually reachable
    if provider == "ollama":
        if _ollama_is_available():
            logger.info("Using Ollama local LLM provider (configured)")
            return OllamaProvider()
        logger.warning(
            "LLM_PROVIDER=ollama but Ollama is not reachable; falling back to cloud providers",
            base_url=settings.OLLAMA_BASE_URL,
        )
        cloud = _try_cloud_providers()
        if cloud is not None:
            return cloud

    if provider == "gpt4all":
        if _gpt4all_is_available():
            logger.info("Using GPT4All local LLM provider (configured)")
            return GPT4AllProvider()
        logger.warning(
            "LLM_PROVIDER=gpt4all but GPT4All is not reachable; falling back to cloud providers",
        )
        cloud = _try_cloud_providers()
        if cloud is not None:
            return cloud

    # Configured cloud provider missing its API key — try any available cloud provider
    if provider in ("openai", "anthropic", "gemini", "mistral"):
        cloud = _try_cloud_providers()
        if cloud is not None:
            logger.info(
                "Configured LLM provider unavailable, using alternate cloud provider",
                configured=provider,
            )
            return cloud

    # Explicit mock, or no configured provider matched — cloud chain then local
    cloud = _try_cloud_providers()
    if cloud is not None:
        return cloud

    if _ollama_is_available():
        logger.info("Using Ollama local LLM provider (fallback)")
        return OllamaProvider()
    if _gpt4all_is_available():
        logger.info("Using GPT4All local LLM provider (fallback)")
        return GPT4AllProvider()

    logger.info("No LLM API keys or local providers available, using static fallback (Mock provider)")
    return MockLLMProvider()
