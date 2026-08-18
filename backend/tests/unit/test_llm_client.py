"""Unit tests for app.ai_engine.llm_client."""

from __future__ import annotations

import asyncio
import json
from dataclasses import fields
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.ai_engine.llm_client import (
    AIExplanation,
    AISummary,
    GPT4AllProvider,
    MockLLMProvider,
    OllamaProvider,
    _extract_json_object,
    _local_explanation_prompt,
    _local_fallback_explanation,
    _local_fallback_recommendations,
    _local_fallback_summary,
    _local_recommendations_prompt,
    _local_risk_prompt,
    _local_summary_prompt,
    _parse_bulleted_response,
)


# ---------------------------------------------------------------------------
# 1. _extract_json_object
# ---------------------------------------------------------------------------
class TestExtractJsonObject:
    def test_bare_json(self):
        result = _extract_json_object('{"a": 1, "b": "two"}')
        assert result == {"a": 1, "b": "two"}

    def test_markdown_fenced_json(self):
        text = '```json\n{"key": "value"}\n```'
        assert _extract_json_object(text) == {"key": "value"}

    def test_markdown_fenced_without_json_tag(self):
        text = '```\n{"key": "val"}\n```'
        assert _extract_json_object(text) == {"key": "val"}

    def test_embedded_in_larger_text(self):
        text = 'Here is the result: {"x": 42} and more text'
        assert _extract_json_object(text) == {"x": 42}

    def test_no_json_returns_empty_dict(self):
        assert _extract_json_object("no json here") == {}

    def test_empty_string(self):
        assert _extract_json_object("") == {}

    def test_none_input(self):
        assert _extract_json_object(None) == {}

    def test_invalid_json_returns_empty_dict(self):
        assert _extract_json_object("{broken") == {}

    def test_non_dict_json_returns_empty_dict(self):
        assert _extract_json_object("[1, 2, 3]") == {}

    def test_json_with_surrounding_text(self):
        text = 'blah blah {"a": 1} blah'
        assert _extract_json_object(text) == {"a": 1}

    def test_nested_json(self):
        data = {"outer": {"inner": [1, 2]}}
        text = json.dumps(data)
        assert _extract_json_object(text) == data


# ---------------------------------------------------------------------------
# 2. _parse_bulleted_response
# ---------------------------------------------------------------------------
class TestParseBulletedResponse:
    def test_numbered_list(self):
        text = "1. first\n2. second\n3. third"
        assert _parse_bulleted_response(text) == ["first", "second", "third"]

    def test_dash_bullets(self):
        text = "- alpha\n- beta"
        assert _parse_bulleted_response(text) == ["alpha", "beta"]

    def test_star_bullets(self):
        text = "* one\n* two"
        assert _parse_bulleted_response(text) == ["one", "two"]

    def test_mixed_list(self):
        text = "1. first\n- second\n* third"
        assert _parse_bulleted_response(text) == ["first", "second", "third"]

    def test_empty_lines_ignored(self):
        text = "1. first\n\n\n2. second"
        assert _parse_bulleted_response(text) == ["first", "second"]

    def test_no_bullets(self):
        text = "just some text\nwith lines"
        assert _parse_bulleted_response(text) == []

    def test_none_input(self):
        assert _parse_bulleted_response(None) == []

    def test_empty_string(self):
        assert _parse_bulleted_response("") == []

    def test_whitespace_only(self):
        assert _parse_bulleted_response("   \n  \n  ") == []

    def test_mixed_with_non_bullet_lines(self):
        text = "intro line\n1. item a\nignore this\n- item b"
        assert _parse_bulleted_response(text) == ["item a", "item b"]


# ---------------------------------------------------------------------------
# 3. _local_explanation_prompt
# ---------------------------------------------------------------------------
class TestLocalExplanationPrompt:
    def test_contains_description_and_context(self):
        desc = "open port"
        ctx = {"rule_id": "R1", "severity": "high"}
        result = _local_explanation_prompt(desc, ctx)
        assert desc in result
        assert "R1" in result
        assert "high" in result
        assert "JSON" in result

    def test_returns_string(self):
        assert isinstance(_local_explanation_prompt("d", {}), str)


# ---------------------------------------------------------------------------
# 4. _local_summary_prompt
# ---------------------------------------------------------------------------
class TestLocalSummaryPrompt:
    def test_formats_findings_and_scores(self):
        findings = [
            {"severity": "critical", "rule_name": "R1", "description": "bad"},
            {"severity": "high", "rule_name": "R2", "description": "worse"},
        ]
        scores = {"security": 80.0, "reliability": 60.0}
        result = _local_summary_prompt(findings, scores)
        assert "R1" in result
        assert "R2" in result
        assert "80.0" in result

    def test_empty_findings(self):
        result = _local_summary_prompt([], {})
        assert "None" in result

    def test_only_critical_findings(self):
        findings = [{"severity": "critical", "rule_name": "CR", "description": "crit"}]
        result = _local_summary_prompt(findings, {"s": 1})
        assert "CR" in result


# ---------------------------------------------------------------------------
# 5. _local_risk_prompt
# ---------------------------------------------------------------------------
class TestLocalRiskPrompt:
    def test_truncates_at_20(self):
        findings = [
            {"severity": "high", "rule_name": f"R{i}", "description": f"desc{i}"}
            for i in range(30)
        ]
        result = _local_risk_prompt(findings)
        assert "R19" in result
        assert "R20" not in result

    def test_severity_in_output(self):
        findings = [{"severity": "critical", "rule_name": "X", "description": "y"}]
        result = _local_risk_prompt(findings)
        assert "CRITICAL" in result

    def test_empty_findings(self):
        result = _local_risk_prompt([])
        assert isinstance(result, str)
        assert "risk assessment" in result.lower()


# ---------------------------------------------------------------------------
# 6. _local_recommendations_prompt
# ---------------------------------------------------------------------------
class TestLocalRecommendationsPrompt:
    def test_formats_findings(self):
        findings = [{"severity": "high", "rule_name": "R1", "description": "d1"}]
        result = _local_recommendations_prompt(findings)
        assert "R1" in result
        assert "HIGH" in result

    def test_truncates_at_20(self):
        findings = [
            {"severity": "low", "rule_name": f"R{i}", "description": f"d{i}"}
            for i in range(25)
        ]
        result = _local_recommendations_prompt(findings)
        assert "R19" in result
        assert "R20" not in result


# ---------------------------------------------------------------------------
# 7. _local_fallback_explanation
# ---------------------------------------------------------------------------
class TestLocalFallbackExplanation:
    def test_returns_ai_explanation(self):
        ctx = {"rule_id": "R1", "description": "test desc"}
        result = _local_fallback_explanation(ctx)
        assert isinstance(result, AIExplanation)
        assert result.finding_id == "R1"
        assert result.explanation == "test desc"
        assert result.confidence == 0.5
        assert len(result.remediation_steps) == 3

    def test_empty_context(self):
        result = _local_fallback_explanation({})
        assert result.finding_id == ""
        assert "No detailed explanation" in result.explanation


# ---------------------------------------------------------------------------
# 8. _local_fallback_summary
# ---------------------------------------------------------------------------
class TestLocalFallbackSummary:
    def test_computes_average(self):
        scores = {"a": 80.0, "b": 60.0}
        result = _local_fallback_summary(scores)
        assert "70.0" in result

    def test_empty_scores(self):
        result = _local_fallback_summary({})
        assert "0.0" in result

    def test_single_score(self):
        result = _local_fallback_summary({"x": 42.5})
        assert "42.5" in result


# ---------------------------------------------------------------------------
# 9. _local_fallback_recommendations
# ---------------------------------------------------------------------------
class TestLocalFallbackRecommendations:
    def test_extracts_critical_and_high(self):
        findings = [
            {"severity": "critical", "recommendation": "fix critical"},
            {"severity": "high", "recommendation": "fix high"},
            {"severity": "low", "recommendation": "ignored"},
        ]
        result = _local_fallback_recommendations(findings)
        assert len(result) == 2
        assert "CRITICAL: fix critical" in result
        assert "HIGH: fix high" in result

    def test_truncates_critical_at_3(self):
        findings = [
            {"severity": "critical", "recommendation": f"r{i}"} for i in range(5)
        ]
        result = _local_fallback_recommendations(findings)
        assert len(result) == 3

    def test_truncates_high_at_2(self):
        findings = [
            {"severity": "high", "recommendation": f"r{i}"} for i in range(5)
        ]
        result = _local_fallback_recommendations(findings)
        assert len(result) == 2

    def test_no_critical_or_high(self):
        findings = [{"severity": "low", "recommendation": "skip"}]
        assert _local_fallback_recommendations(findings) == []


# ---------------------------------------------------------------------------
# 10. MockLLMProvider
# ---------------------------------------------------------------------------
class TestMockLLMProvider:
    @pytest.fixture
    def provider(self):
        return MockLLMProvider()

    @pytest.mark.asyncio
    async def test_generate_explanation(self, provider):
        ctx = {"rule_id": "MR-001"}
        result = await provider.generate_explanation("test finding", ctx)
        assert isinstance(result, AIExplanation)
        assert result.finding_id == "MR-001"
        assert "test finding" in result.explanation
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_generate_executive_summary(self, provider):
        result = await provider.generate_executive_summary([], {"sec": 80.0, "rel": 60.0})
        assert "Executive Summary" in result
        assert "70.0" in result

    @pytest.mark.asyncio
    async def test_generate_executive_summary_empty_scores(self, provider):
        result = await provider.generate_executive_summary([], {})
        assert "0.0" in result

    @pytest.mark.asyncio
    async def test_generate_risk_analysis(self, provider):
        result = await provider.generate_risk_analysis([1, 2, 3])
        assert "3 findings" in result

    @pytest.mark.asyncio
    async def test_generate_prioritized_recommendations(self, provider):
        findings = [
            {"recommendation": "Fix A"},
            {"recommendation": "Fix B"},
        ]
        result = await provider.generate_prioritized_recommendations(findings)
        assert result == ["Fix A", "Fix B"]

    @pytest.mark.asyncio
    async def test_generate_prioritized_recommendations_truncates(self, provider):
        findings = [{"recommendation": f"Fix {i}"} for i in range(10)]
        result = await provider.generate_prioritized_recommendations(findings)
        assert len(result) == 5


# ---------------------------------------------------------------------------
# 11. AIExplanation dataclass
# ---------------------------------------------------------------------------
class TestAIExplanation:
    def test_construction(self):
        e = AIExplanation(
            finding_id="f1",
            explanation="exp",
            impact_analysis="impact",
            remediation_steps=["step1"],
        )
        assert e.finding_id == "f1"
        assert e.confidence == 0.9  # default

    def test_custom_confidence(self):
        e = AIExplanation(
            finding_id="f1",
            explanation="exp",
            impact_analysis="impact",
            remediation_steps=[],
            confidence=0.5,
        )
        assert e.confidence == 0.5

    def test_fields_exist(self):
        names = {f.name for f in fields(AIExplanation)}
        assert names == {"finding_id", "explanation", "impact_analysis", "remediation_steps", "confidence"}


# ---------------------------------------------------------------------------
# 12. AISummary dataclass
# ---------------------------------------------------------------------------
class TestAISummary:
    def test_construction(self):
        s = AISummary(
            executive_summary="exec",
            risk_analysis="risk",
            prioritized_recommendations=["r1"],
        )
        assert s.executive_summary == "exec"
        assert s.prioritized_recommendations == ["r1"]

    def test_fields_exist(self):
        names = {f.name for f in fields(AISummary)}
        assert names == {"executive_summary", "risk_analysis", "prioritized_recommendations"}


# ---------------------------------------------------------------------------
# 13. OllamaClient
# ---------------------------------------------------------------------------
class TestOllamaClient:
    """Tests for the low-level OllamaClient (from local_llm)."""

    def _make_client(self, stream=False, max_retries=2):
        from app.ai_engine.local_llm import OllamaClient

        return OllamaClient(
            base_url="http://test:11434",
            model="testmodel",
            timeout_seconds=10,
            max_retries=max_retries,
            stream=stream,
        )

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure_non_200(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        assert await client.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        client = self._make_client()
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        client._client = mock_http

        assert await client.health_check() is False

    @pytest.mark.asyncio
    async def test_generate_non_streaming_success(self):
        client = self._make_client(stream=False)
        client._health_checked = True

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "hello world"}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        client._client = mock_http

        result = await client.generate("test prompt")
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_generate_retries_on_5xx(self):
        client = self._make_client(max_retries=2)
        client._health_checked = True

        response_500 = MagicMock()
        response_500.status_code = 500
        response_500.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500",
            request=MagicMock(),
            response=response_500,
        )

        response_ok = MagicMock()
        response_ok.status_code = 200
        response_ok.json.return_value = {"response": "recovered"}
        response_ok.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=[response_500, response_ok])
        client._client = mock_http

        with patch("app.ai_engine.local_llm.asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate("prompt")
        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_generate_fails_after_max_retries(self):
        client = self._make_client(max_retries=1)
        client._health_checked = True

        response_500 = MagicMock()
        response_500.status_code = 500
        response_500.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500",
            request=MagicMock(),
            response=response_500,
        )

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=response_500)
        client._client = mock_http

        with patch("app.ai_engine.local_llm.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.HTTPStatusError):
                await client.generate("prompt")

    @pytest.mark.asyncio
    async def test_generate_empty_completion_raises(self):
        client = self._make_client(max_retries=0)
        client._health_checked = True

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "   "}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        client._client = mock_http

        with pytest.raises(RuntimeError, match="empty completion"):
            await client.generate("prompt")

    @pytest.mark.asyncio
    async def test_first_call_health_check_failure(self):
        client = self._make_client(max_retries=0)

        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client._client = mock_http

        with pytest.raises(RuntimeError, match="unreachable"):
            await client.generate("prompt")

    @pytest.mark.asyncio
    async def test_aclose_resets_state(self):
        client = self._make_client()
        client._health_checked = True
        client._client = AsyncMock()

        await client.aclose()

        assert client._client is None
        assert client._health_checked is False

    @pytest.mark.asyncio
    async def test_aclose_when_no_client(self):
        client = self._make_client()
        client._client = None
        await client.aclose()
        assert client._health_checked is False


# ---------------------------------------------------------------------------
# 14. GPT4AllModel
# ---------------------------------------------------------------------------
class TestGPT4AllModel:
    def _make_model(self, **kwargs):
        from app.ai_engine.local_llm import GPT4AllModel

        return GPT4AllModel(model="test.gguf", model_path="/tmp", threads=2, max_tokens=100, **kwargs)

    def test_load_model_raises_when_gpt4all_not_installed(self):
        model = self._make_model()
        with patch.dict("sys.modules", {"gpt4all": None}):
            with pytest.raises(RuntimeError, match="gpt4all"):
                model._load_model()

    def test_generate_delegates_to_model(self):
        from app.ai_engine.local_llm import GPT4AllModel

        GPT4AllModel._model_instance = None

        model = self._make_model()
        mock_gpt = MagicMock()
        mock_gpt.generate.return_value = "generated text"

        with patch("app.ai_engine.local_llm.GPT4AllModel._load_model", return_value=mock_gpt):
            result = model.generate("hello")

        assert result == "generated text"
        mock_gpt.generate.assert_called_once_with("hello", max_tokens=100, temp=0.2)

    @pytest.mark.asyncio
    async def test_agenerate_delegates(self):
        from app.ai_engine.local_llm import GPT4AllModel

        GPT4AllModel._model_instance = None

        model = self._make_model()

        with patch.object(model, "generate", return_value="async result") as mock_gen:
            result = await model.agenerate("prompt")
        assert result == "async result"
        mock_gen.assert_called_once_with("prompt", None, 0.2)

    def test_close_sets_model_instance_to_none(self):
        from app.ai_engine.local_llm import GPT4AllModel

        GPT4AllModel._model_instance = "something"
        model = self._make_model()
        model.close()
        assert GPT4AllModel._model_instance is None

    def test_close_when_already_none(self):
        from app.ai_engine.local_llm import GPT4AllModel

        GPT4AllModel._model_instance = None
        model = self._make_model()
        model.close()
        assert GPT4AllModel._model_instance is None


# ---------------------------------------------------------------------------
# 15. OllamaProvider
# ---------------------------------------------------------------------------
class TestOllamaProvider:
    @pytest.fixture
    def provider(self):
        with patch("app.ai_engine.local_llm.OllamaClient") as MockOllama:
            mock_client = MagicMock()
            mock_client.model = "test-model"
            mock_client.base_url = "http://test:11434"
            mock_client.generate = AsyncMock(return_value="response text")
            mock_client.health_check = AsyncMock(return_value=True)
            mock_client.aclose = AsyncMock()
            MockOllama.return_value = mock_client
            p = OllamaProvider(base_url="http://test:11434", model="test-model")
            return p

    @pytest.mark.asyncio
    async def test_generate_delegates(self, provider):
        provider._llm_client.generate = AsyncMock(return_value="output")
        result = await provider.generate("hello")
        assert result == "output"
        provider._llm_client.generate.assert_called_once_with("hello", max_tokens=None)

    @pytest.mark.asyncio
    async def test_health_check_delegates(self, provider):
        provider._llm_client.health_check = AsyncMock(return_value=True)
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_generate_explanation_success(self, provider):
        data = {
            "explanation": "This is an explanation",
            "impact_analysis": "impact here",
            "remediation_steps": ["step1", "step2"],
        }
        provider._llm_client.generate = AsyncMock(return_value=json.dumps(data))
        result = await provider.generate_explanation("finding desc", {"rule_id": "R1"})
        assert isinstance(result, AIExplanation)
        assert result.finding_id == "R1"
        assert result.explanation == "This is an explanation"
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_generate_explanation_fallback_on_exception(self, provider):
        provider._llm_client.generate = AsyncMock(side_effect=RuntimeError("fail"))
        result = await provider.generate_explanation("desc", {"rule_id": "R2"})
        assert isinstance(result, AIExplanation)
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_generate_executive_summary_success(self, provider):
        provider._llm_client.generate = AsyncMock(return_value="summary text")
        result = await provider.generate_executive_summary([], {"s": 1.0})
        assert result == "summary text"

    @pytest.mark.asyncio
    async def test_generate_executive_summary_fallback(self, provider):
        provider._llm_client.generate = AsyncMock(side_effect=RuntimeError("fail"))
        result = await provider.generate_executive_summary([], {"s": 50.0})
        assert "50.0" in result

    @pytest.mark.asyncio
    async def test_generate_risk_analysis_success(self, provider):
        provider._llm_client.generate = AsyncMock(return_value="risk text")
        result = await provider.generate_risk_analysis([])
        assert result == "risk text"

    @pytest.mark.asyncio
    async def test_generate_risk_analysis_fallback(self, provider):
        provider._llm_client.generate = AsyncMock(side_effect=RuntimeError("fail"))
        result = await provider.generate_risk_analysis([])
        assert result == "Risk analysis unavailable."

    @pytest.mark.asyncio
    async def test_generate_prioritized_recommendations_success(self, provider):
        provider._llm_client.generate = AsyncMock(
            return_value="1. fix this\n2. fix that\n3. fix other"
        )
        result = await provider.generate_prioritized_recommendations([])
        assert "fix this" in result
        assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_generate_prioritized_recommendations_fallback(self, provider):
        provider._llm_client.generate = AsyncMock(side_effect=RuntimeError("fail"))
        findings = [{"severity": "critical", "recommendation": "fix critical"}]
        result = await provider.generate_prioritized_recommendations(findings)
        assert "CRITICAL: fix critical" in result

    @pytest.mark.asyncio
    async def test_close(self, provider):
        await provider.close()
        provider._llm_client.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# 16. GPT4AllProvider
# ---------------------------------------------------------------------------
class TestGPT4AllProvider:
    @pytest.fixture
    def provider(self):
        with patch("app.ai_engine.local_llm.GPT4AllModel") as MockGPT:
            mock_client = MagicMock()
            mock_client.model_name = "test-model"
            mock_client.agenerate = AsyncMock(return_value="generated text")
            mock_client.close = MagicMock()
            MockGPT.return_value = mock_client
            p = GPT4AllProvider(model="test-model", model_path="/tmp")
            return p

    @pytest.mark.asyncio
    async def test_generate_delegates(self, provider):
        provider._llm_client.agenerate = AsyncMock(return_value="output")
        result = await provider.generate("hello")
        assert result == "output"

    @pytest.mark.asyncio
    async def test_generate_explanation_success(self, provider):
        data = {
            "explanation": "gpt4all explanation",
            "impact_analysis": "impact",
            "remediation_steps": ["s1"],
        }
        provider._llm_client.agenerate = AsyncMock(return_value=json.dumps(data))
        result = await provider.generate_explanation("desc", {"rule_id": "R3"})
        assert isinstance(result, AIExplanation)
        assert result.explanation == "gpt4all explanation"
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_generate_explanation_fallback(self, provider):
        provider._llm_client.agenerate = AsyncMock(side_effect=RuntimeError("fail"))
        result = await provider.generate_explanation("desc", {"rule_id": "R4"})
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_generate_executive_summary_success(self, provider):
        provider._llm_client.agenerate = AsyncMock(return_value="gpt4all summary")
        result = await provider.generate_executive_summary([], {})
        assert result == "gpt4all summary"

    @pytest.mark.asyncio
    async def test_generate_executive_summary_fallback(self, provider):
        provider._llm_client.agenerate = AsyncMock(side_effect=RuntimeError("fail"))
        result = await provider.generate_executive_summary([], {"a": 10.0})
        assert "10.0" in result

    @pytest.mark.asyncio
    async def test_generate_risk_analysis_success(self, provider):
        provider._llm_client.agenerate = AsyncMock(return_value="gpt4all risk")
        result = await provider.generate_risk_analysis([])
        assert result == "gpt4all risk"

    @pytest.mark.asyncio
    async def test_generate_risk_analysis_fallback(self, provider):
        provider._llm_client.agenerate = AsyncMock(side_effect=RuntimeError("fail"))
        result = await provider.generate_risk_analysis([])
        assert result == "Risk analysis unavailable."

    @pytest.mark.asyncio
    async def test_generate_prioritized_recommendations_success(self, provider):
        provider._llm_client.agenerate = AsyncMock(
            return_value="1. do A\n2. do B\n3. do C"
        )
        result = await provider.generate_prioritized_recommendations([])
        assert "do A" in result

    @pytest.mark.asyncio
    async def test_generate_prioritized_recommendations_fallback(self, provider):
        provider._llm_client.agenerate = AsyncMock(side_effect=RuntimeError("fail"))
        findings = [{"severity": "high", "recommendation": "fix high"}]
        result = await provider.generate_prioritized_recommendations(findings)
        assert "HIGH: fix high" in result

    @pytest.mark.asyncio
    async def test_close(self, provider):
        await provider.close()
        provider._llm_client.close.assert_called_once()
