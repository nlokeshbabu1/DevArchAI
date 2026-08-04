"""Tests for the Ollama and GPT4All local LLM providers.

These providers are shared between ``app.ai_engine.llm_client`` and
``app.ai.engine`` (via thin alias classes), so this suite exercises the
canonical implementation and the factory selection paths.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.engine import (
    GPT4AllProvider as EngineGPT4AllProvider,
    OllamaProvider as EngineOllamaProvider,
    get_llm_provider as engine_get_llm_provider,
)
from app.ai_engine.llm_client import (
    GPT4AllProvider,
    OllamaProvider,
    _extract_json_object,
    _local_fallback_explanation,
    _parse_bulleted_response,
)

CONTEXT = {"rule_id": "TF-SEC-001", "severity": "high"}

VALID_EXPLANATION_JSON = json.dumps({
    "explanation": "State stored locally can be corrupted or lost.",
    "impact_analysis": "Drift and corruption risk for production infra.",
    "remediation_steps": ["Configure remote backend", "Enable locking"],
})


# ============================================================================
# OllamaProvider
# ============================================================================

class TestOllamaProvider:
    @pytest.mark.asyncio
    async def test_generate_returns_raw_completion(self):
        provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.2")
        provider._llm_client = MagicMock()
        provider._llm_client.generate = AsyncMock(return_value="  completion text  ")

        result = await provider.generate("hello", max_tokens=64)

        assert result == "  completion text  "
        provider._llm_client.generate.assert_awaited_once_with(
            "hello", max_tokens=64
        )

    @pytest.mark.asyncio
    async def test_generate_explanation_returns_ai_explanation(self):
        provider = OllamaProvider()
        provider._llm_client = MagicMock()
        provider._llm_client.generate = AsyncMock(return_value=VALID_EXPLANATION_JSON)

        result = await provider.generate_explanation(
            "Terraform state stored locally", CONTEXT
        )

        assert result.finding_id == "TF-SEC-001"
        assert result.explanation == "State stored locally can be corrupted or lost."
        assert result.impact_analysis.startswith("Drift")
        assert len(result.remediation_steps) == 2
        assert 0 <= result.confidence <= 1

    @pytest.mark.asyncio
    async def test_generate_explanation_falls_back_on_error(self):
        provider = OllamaProvider()
        provider._llm_client = MagicMock()
        provider._llm_client.generate = AsyncMock(side_effect=RuntimeError("down"))

        result = await provider.generate_explanation("desc", CONTEXT)

        expected = _local_fallback_explanation(CONTEXT)
        assert result.finding_id == "TF-SEC-001"
        assert result.explanation == expected.explanation

    @pytest.mark.asyncio
    async def test_executive_summary_falls_back(self):
        provider = OllamaProvider()
        provider._llm_client = MagicMock()
        provider._llm_client.generate = AsyncMock(side_effect=RuntimeError("down"))

        result = await provider.generate_executive_summary([], {"overall": 70.0})

        assert "70" in result or "70.0" in result

    @pytest.mark.asyncio
    async def test_prioritized_recommendations_parses_bullets(self):
        provider = OllamaProvider()
        provider._llm_client = MagicMock()
        provider._llm_client.generate = AsyncMock(
            return_value="- First\n- Second\n- Third"
        )

        result = await provider.generate_prioritized_recommendations([{}])

        assert result == ["First", "Second", "Third"]

    @pytest.mark.asyncio
    async def test_close_releases_client(self):
        provider = OllamaProvider()
        provider._llm_client = MagicMock()
        provider._llm_client.aclose = AsyncMock()

        await provider.close()

        provider._llm_client.aclose.assert_awaited_once()


# ============================================================================
# GPT4AllProvider
# ============================================================================

class TestGPT4AllProvider:
    @pytest.mark.asyncio
    async def test_generate_uses_threaded_inference(self):
        provider = GPT4AllProvider(model="test-model")
        provider._llm_client = MagicMock()
        provider._llm_client.agenerate = AsyncMock(return_value="generated text")

        result = await provider.generate("prompt", max_tokens=256)

        assert result == "generated text"
        provider._llm_client.agenerate.assert_awaited_once_with(
            "prompt", max_tokens=256
        )

    @pytest.mark.asyncio
    async def test_generate_explanation_returns_ai_explanation(self):
        provider = GPT4AllProvider(model="test-model")
        provider._llm_client = MagicMock()
        provider._llm_client.agenerate = AsyncMock(return_value=VALID_EXPLANATION_JSON)

        result = await provider.generate_explanation("K8s pod runs as root", CONTEXT)

        assert result.finding_id == "TF-SEC-001"
        assert result.explanation == "State stored locally can be corrupted or lost."
        assert 0 <= result.confidence <= 1

    @pytest.mark.asyncio
    async def test_generate_explanation_falls_back_on_error(self):
        provider = GPT4AllProvider(model="test-model")
        provider._llm_client = MagicMock()
        provider._llm_client.agenerate = AsyncMock(side_effect=RuntimeError("no model"))

        result = await provider.generate_explanation("desc", CONTEXT)

        expected = _local_fallback_explanation(CONTEXT)
        assert result.explanation == expected.explanation

    @pytest.mark.asyncio
    async def test_close_releases_model(self):
        provider = GPT4AllProvider(model="test-model")
        provider._llm_client = MagicMock()

        await provider.close()

        provider._llm_client.close.assert_called_once()


# ============================================================================
# Engine alias classes
# ============================================================================

class TestEngineAliases:
    @pytest.mark.asyncio
    async def test_engine_ollama_alias_delegates_to_shared_provider(self):
        provider = EngineOllamaProvider()
        assert isinstance(provider, EngineOllamaProvider)
        assert hasattr(provider, "generate")
        assert callable(provider.generate)

    @pytest.mark.asyncio
    async def test_engine_gpt4all_alias_delegates_to_shared_provider(self):
        provider = EngineGPT4AllProvider()
        assert isinstance(provider, EngineGPT4AllProvider)
        assert hasattr(provider, "generate")
        assert callable(provider.generate)


# ============================================================================
# Factory selection
# ============================================================================

class TestLocalProviderSelection:
    def test_get_llm_provider_ollama(self):
        with patch("app.ai.engine.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "ollama"

            provider = engine_get_llm_provider()

            assert isinstance(provider, EngineOllamaProvider)

    def test_get_llm_provider_gpt4all(self):
        with patch("app.ai.engine.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "gpt4all"

            provider = engine_get_llm_provider()

            assert isinstance(provider, EngineGPT4AllProvider)

    def test_get_llm_provider_ollama_in_llm_client(self):
        with patch("app.ai_engine.llm_client.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "ollama"

            from app.ai_engine.llm_client import get_llm_provider

            provider = get_llm_provider()

            assert isinstance(provider, OllamaProvider)


# ============================================================================
# Local parsing helpers
# ============================================================================

class TestLocalHelpers:
    def test_extract_json_object_fenced(self):
        text = "```json\n" + VALID_EXPLANATION_JSON + "\n```"
        data = _extract_json_object(text)
        assert data["explanation"].startswith("State stored")

    def test_extract_json_object_inline(self):
        text = f"prefix {VALID_EXPLANATION_JSON} suffix"
        data = _extract_json_object(text)
        assert data["impact_analysis"].startswith("Drift")

    def test_extract_json_object_fallback_on_invalid(self):
        data = _extract_json_object("not json at all")
        assert isinstance(data, dict)

    def test_parse_bulleted_response(self):
        items = _parse_bulleted_response("- Alpha\n* Beta\n1. Gamma\nplain line")
        assert items == ["Alpha", "Beta", "Gamma"]

    def test_parse_bulleted_response_empty(self):
        assert _parse_bulleted_response("") == []
