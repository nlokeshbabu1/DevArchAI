"""Tests for app.ai.engine — LLM provider factory and provider utilities."""

import pytest
from unittest.mock import patch, MagicMock

from app.ai.engine import (
    AIExplanation,
    MockLLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    MistralProvider,
    GeminiProvider,
    get_llm_provider,
)


def _mock_settings(**overrides):
    """Create a MagicMock with all settings attributes explicitly set.

    Unset attributes default to None/empty so the fallback chain works correctly.
    """
    defaults = {
        "LLM_PROVIDER": "mock",
        "OPENAI_API_KEY": None,
        "ANTHROPIC_API_KEY": None,
        "GEMINI_API_KEY": None,
        "MISTRAL_API_KEY": None,
        "LLM_MODEL": None,
    }
    defaults.update(overrides)
    s = MagicMock()
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


_local_patches = {
    "_ollama_is_available": MagicMock(return_value=False),
    "_gpt4all_is_available": MagicMock(return_value=False),
}


# ---------------------------------------------------------------------------
# AIExplanation dataclass
# ---------------------------------------------------------------------------

class TestAIExplanation:
    def test_construction(self):
        e = AIExplanation(
            finding_id="R1",
            explanation="exp",
            impact_analysis="imp",
            remediation_steps=["step1"],
            confidence=0.9,
        )
        assert e.finding_id == "R1"
        assert e.explanation == "exp"
        assert e.impact_analysis == "imp"
        assert e.remediation_steps == ["step1"]
        assert e.confidence == 0.9

    def test_default_confidence(self):
        e = AIExplanation(
            finding_id="R2", explanation="e", impact_analysis="i",
            remediation_steps=[], confidence=0.9,
        )
        assert e.confidence == 0.9

    def test_empty_fields(self):
        e = AIExplanation(
            finding_id="", explanation="", impact_analysis="",
            remediation_steps=[], confidence=0.0,
        )
        assert e.finding_id == ""
        assert e.remediation_steps == []

    def test_missing_confidence_raises(self):
        with pytest.raises(TypeError):
            AIExplanation(
                finding_id="R1", explanation="e", impact_analysis="i",
                remediation_steps=[],
            )


# ---------------------------------------------------------------------------
# MockLLMProvider
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMockLLMProvider:
    @pytest.fixture
    def provider(self):
        return MockLLMProvider()

    async def test_generate_explanation(self, provider):
        result = await provider.generate_explanation(
            "Missing health check", {"rule_id": "R1"},
        )
        assert isinstance(result, AIExplanation)
        assert result.finding_id == "R1"
        assert result.explanation == "AI Explanation: Missing health check"
        assert "production reliability" in result.impact_analysis.lower()
        assert isinstance(result.remediation_steps, list)
        assert len(result.remediation_steps) == 3
        assert result.confidence == 0.8

    async def test_generate_explanation_empty_context(self, provider):
        result = await provider.generate_explanation("desc", {})
        assert result.finding_id == ""
        assert "desc" in result.explanation

    async def test_generate_executive_summary(self, provider):
        scores = {"security": 80.0, "reliability": 60.0}
        result = await provider.generate_executive_summary([], scores)
        assert isinstance(result, str)
        assert "70.0" in result

    async def test_generate_executive_summary_empty_scores(self, provider):
        result = await provider.generate_executive_summary([], {})
        assert "0.0" in result

    async def test_generate_risk_analysis(self, provider):
        findings = [{"severity": "critical"}, {"severity": "high"}]
        result = await provider.generate_risk_analysis(findings)
        assert result == "Risk Analysis: 2 findings detected"

    async def test_generate_risk_analysis_empty(self, provider):
        result = await provider.generate_risk_analysis([])
        assert result == "Risk Analysis: 0 findings detected"

    async def test_generate_prioritized_recommendations(self, provider):
        findings = [
            {"recommendation": "Fix A"},
            {"recommendation": "Fix B"},
            {"recommendation": "Fix C"},
        ]
        result = await provider.generate_prioritized_recommendations(findings)
        assert result == ["Fix A", "Fix B", "Fix C"]

    async def test_generate_prioritized_recommendations_limit(self, provider):
        findings = [{"recommendation": f"R{i}"} for i in range(10)]
        result = await provider.generate_prioritized_recommendations(findings)
        assert len(result) == 5

    async def test_generate_prioritized_recommendations_empty(self, provider):
        result = await provider.generate_prioritized_recommendations([])
        assert result == []


# ---------------------------------------------------------------------------
# get_llm_provider() factory — configured providers
# ---------------------------------------------------------------------------

class TestGetLLMProviderConfigured:

    @patch("app.ai.engine.settings")
    def test_openai(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test",
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": "gpt-4",
        }
        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "sk-test"
        assert provider.model == "gpt-4"

    @patch("app.ai.engine.settings")
    def test_openai_default_model(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test",
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert provider.model == "gpt-4-turbo-preview"

    @patch("app.ai.engine.settings")
    def test_anthropic(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "anthropic",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": "claude-3-opus",
        }
        provider = get_llm_provider()
        assert isinstance(provider, AnthropicProvider)
        assert provider.api_key == "sk-ant-test"

    @patch("app.ai.engine.settings")
    def test_anthropic_default_model(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "anthropic",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert provider.model == "claude-3-sonnet-20240229"

    @patch("app.ai.engine.settings")
    def test_gemini(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "gemini",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": "gkey",
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": "gemini-2.0-flash",
        }
        provider = get_llm_provider()
        assert isinstance(provider, GeminiProvider)
        assert provider.api_key == "gkey"

    @patch("app.ai.engine.settings")
    def test_gemini_default_model(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "gemini",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": "gkey",
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert provider.model == "gemini-1.5-flash"

    @patch("app.ai.engine.settings")
    def test_mistral(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mistral",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": "mkey",
            "LLM_MODEL": "mistral-embed",
        }
        provider = get_llm_provider()
        assert isinstance(provider, MistralProvider)
        assert provider.model == "mistral-embed"

    @patch("app.ai.engine.settings")
    def test_mistral_ignores_gpt4_model_name(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mistral",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": "mkey",
            "LLM_MODEL": "gpt-4-turbo-preview",
        }
        provider = get_llm_provider()
        assert provider.model == "mistral-large-latest"

    @patch("app.ai.engine.settings")
    def test_mistral_ignores_gemini_model_name(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mistral",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": "mkey",
            "LLM_MODEL": "gemini-pro",
        }
        provider = get_llm_provider()
        assert provider.model == "mistral-large-latest"

    @patch("app.ai.engine.settings")
    def test_ollama(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "ollama",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        with patch.dict("app.ai.engine.__dict__", _local_patches):
            with patch("app.ai.engine.OllamaProvider") as MockOP:
                MockOP.return_value = MagicMock()
                provider = get_llm_provider()
                MockOP.assert_called_once()

    @patch("app.ai.engine.settings")
    def test_gpt4all(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "gpt4all",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        with patch.dict("app.ai.engine.__dict__", _local_patches):
            with patch("app.ai.engine.GPT4AllProvider") as MockGP:
                MockGP.return_value = MagicMock()
                provider = get_llm_provider()
                MockGP.assert_called_once()


# ---------------------------------------------------------------------------
# get_llm_provider() factory — fallback when configured provider lacks key
# ---------------------------------------------------------------------------

class TestGetLLMProviderFallback:

    @patch("app.ai.engine.settings")
    def test_openai_no_key_falls_to_anthropic(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": "sk-ant",
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert isinstance(provider, AnthropicProvider)

    @patch("app.ai.engine.settings")
    def test_anthropic_no_key_falls_to_gemini(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "anthropic",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": "gkey",
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert isinstance(provider, GeminiProvider)

    @patch("app.ai.engine.settings")
    def test_gemini_no_key_falls_to_mistral(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "gemini",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": "mkey",
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert isinstance(provider, MistralProvider)

    @patch("app.ai.engine.settings")
    def test_mistral_no_key_falls_to_mock(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mistral",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        with patch.dict("app.ai.engine.__dict__", _local_patches):
            provider = get_llm_provider()
        assert isinstance(provider, MockLLMProvider)

    @patch("app.ai.engine.settings")
    def test_unknown_provider_tries_fallback_chain(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "unknown",
            "OPENAI_API_KEY": "sk-oai",
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)


# ---------------------------------------------------------------------------
# get_llm_provider() factory — full fallback chain with no API keys
# ---------------------------------------------------------------------------

class TestGetLLMProviderFallbackChain:

    @patch("app.ai.engine.settings")
    def test_no_keys_falls_to_local_then_mock(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mock",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        with patch.dict("app.ai.engine.__dict__", _local_patches):
            provider = get_llm_provider()
        assert isinstance(provider, MockLLMProvider)

    @patch("app.ai.engine.settings")
    def test_fallback_chain_openai_first(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mock",
            "OPENAI_API_KEY": "sk-oai",
            "ANTHROPIC_API_KEY": "sk-ant",
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)

    @patch("app.ai.engine.settings")
    def test_fallback_chain_anthropic_second(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mock",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": "sk-ant",
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert isinstance(provider, AnthropicProvider)

    @patch("app.ai.engine.settings")
    def test_fallback_chain_gemini_third(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mock",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": "gkey",
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert isinstance(provider, GeminiProvider)

    @patch("app.ai.engine.settings")
    def test_fallback_chain_mistral_fourth(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mock",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": "mkey",
            "LLM_MODEL": None,
        }
        provider = get_llm_provider()
        assert isinstance(provider, MistralProvider)

    @patch("app.ai.engine.settings")
    def test_ollama_available_in_fallback(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mock",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        patches = {
            "_ollama_is_available": MagicMock(return_value=True),
            "_gpt4all_is_available": MagicMock(return_value=False),
        }
        with patch.dict("app.ai.engine.__dict__", patches):
            with patch("app.ai.engine.OllamaProvider") as MockOP:
                MockOP.return_value = MagicMock()
                provider = get_llm_provider()
                MockOP.assert_called_once()

    @patch("app.ai.engine.settings")
    def test_gpt4all_available_in_fallback(self, mock_settings):
        mock_settings.__dict__ = {
            "LLM_PROVIDER": "mock",
            "OPENAI_API_KEY": None,
            "ANTHROPIC_API_KEY": None,
            "GEMINI_API_KEY": None,
            "MISTRAL_API_KEY": None,
            "LLM_MODEL": None,
        }
        patches = {
            "_ollama_is_available": MagicMock(return_value=False),
            "_gpt4all_is_available": MagicMock(return_value=True),
        }
        with patch.dict("app.ai.engine.__dict__", patches):
            with patch("app.ai.engine.GPT4AllProvider") as MockGP:
                MockGP.return_value = MagicMock()
                provider = get_llm_provider()
                MockGP.assert_called_once()


# ---------------------------------------------------------------------------
# OpenAIProvider — _format_findings, _format_all_findings, _fallback_*
# ---------------------------------------------------------------------------

class TestOpenAIFormatHelpers:
    @pytest.fixture
    def provider(self):
        return OpenAIProvider(api_key="test-key", model="gpt-4")

    def test_format_findings_matches_severity(self, provider):
        findings = [
            {"severity": "high", "rule_name": "R1", "description": "d1"},
            {"severity": "critical", "rule_name": "R2", "description": "d2"},
            {"severity": "high", "rule_name": "R3", "description": "d3"},
        ]
        result = provider._format_findings(findings, "high")
        assert "- R1: d1" in result
        assert "- R3: d3" in result
        assert "R2" not in result

    def test_format_findings_no_matches_returns_none(self, provider):
        findings = [{"severity": "low", "rule_name": "R1", "description": "d1"}]
        result = provider._format_findings(findings, "high")
        assert result == "None"

    def test_format_findings_empty_list(self, provider):
        assert provider._format_findings([], "high") == "None"

    def test_format_findings_truncates_at_10(self, provider):
        findings = [
            {"severity": "high", "rule_name": f"R{i}", "description": f"d{i}"}
            for i in range(15)
        ]
        result = provider._format_findings(findings, "high")
        lines = [l for l in result.split("\n") if l.startswith("- ")]
        assert len(lines) == 10

    def test_format_all_findings(self, provider):
        findings = [
            {"severity": "critical", "rule_name": "R1", "description": "d1"},
            {"severity": "high", "rule_name": "R2", "description": "d2"},
        ]
        result = provider._format_all_findings(findings)
        assert "[CRITICAL] R1: d1" in result
        assert "[HIGH] R2: d2" in result

    def test_format_all_findings_truncates_at_20(self, provider):
        findings = [
            {"severity": "medium", "rule_name": f"R{i}", "description": f"d{i}"}
            for i in range(30)
        ]
        result = provider._format_all_findings(findings)
        lines = [l for l in result.split("\n") if l.startswith("[")]
        assert len(lines) == 20


class TestOpenAIFallbacks:
    @pytest.fixture
    def provider(self):
        return OpenAIProvider(api_key="test-key", model="gpt-4")

    def test_fallback_explanation(self, provider):
        context = {"rule_id": "R1", "description": "container runs as root"}
        result = provider._fallback_explanation(context)
        assert isinstance(result, AIExplanation)
        assert result.finding_id == "R1"
        assert result.explanation == "container runs as root"
        assert result.confidence == 0.5
        assert isinstance(result.remediation_steps, list)

    def test_fallback_explanation_empty_context(self, provider):
        result = provider._fallback_explanation({})
        assert result.finding_id == ""
        assert result.explanation == "No detailed explanation available."

    def test_fallback_summary(self, provider):
        scores = {"security": 80.0, "reliability": 60.0, "cost": 70.0}
        result = provider._fallback_summary(scores)
        assert "70.0" in result
        assert "security" in result

    def test_fallback_summary_empty_scores(self, provider):
        result = provider._fallback_summary({})
        assert "0.0" in result

    def test_fallback_recommendations(self, provider):
        findings = [
            {"severity": "critical", "recommendation": "Fix immediately"},
            {"severity": "critical", "recommendation": "Patch now"},
            {"severity": "high", "recommendation": "Update soon"},
            {"severity": "low", "recommendation": "Nice to have"},
        ]
        result = provider._fallback_recommendations(findings)
        assert "CRITICAL: Fix immediately" in result
        assert "CRITICAL: Patch now" in result
        assert "HIGH: Update soon" in result
        assert len(result) == 3

    def test_fallback_recommendations_truncates_critical_at_3(self, provider):
        findings = [
            {"severity": "critical", "recommendation": f"Fix {i}"}
            for i in range(5)
        ]
        result = provider._fallback_recommendations(findings)
        critical = [r for r in result if r.startswith("CRITICAL")]
        assert len(critical) == 3

    def test_fallback_recommendations_truncates_high_at_2(self, provider):
        findings = [
            {"severity": "high", "recommendation": f"Fix {i}"}
            for i in range(5)
        ]
        result = provider._fallback_recommendations(findings)
        high = [r for r in result if r.startswith("HIGH")]
        assert len(high) == 2

    def test_fallback_recommendations_empty(self, provider):
        assert provider._fallback_recommendations([]) == []

    def test_fallback_recommendations_only_low_severity(self, provider):
        findings = [
            {"severity": "low", "recommendation": "Nice to have"},
        ]
        result = provider._fallback_recommendations(findings)
        assert result == []
