"""Tests for the ExplanationEngine."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.ai_engine.explanation_engine import ExplanationEngine
from app.ai_engine.llm_client import AIExplanation, MockLLMProvider
from app.rule_engine.base import Category, RuleFinding, Severity


def _make_finding(
    rule_id="TF-STATE-001",
    rule_name="Local Backend",
    severity=Severity.HIGH,
    category=Category.RELIABILITY,
    description="Uses local backend",
    recommendation="Use remote backend",
    file_path="main.tf",
    resource_name=None,
):
    return RuleFinding(
        rule_id=rule_id,
        rule_name=rule_name,
        severity=severity,
        category=category,
        description=description,
        recommendation=recommendation,
        file_path=file_path,
        resource_name=resource_name,
    )


class TestInit:
    def test_default_provider(self):
        with patch(
            "app.ai_engine.explanation_engine.get_llm_provider",
            return_value=MockLLMProvider(),
        ):
            engine = ExplanationEngine()
        assert isinstance(engine.llm_provider, MockLLMProvider)
        assert engine._explanation_cache == {}

    def test_injected_provider(self):
        provider = MockLLMProvider()
        engine = ExplanationEngine(llm_provider=provider)
        assert engine.llm_provider is provider
        assert engine._explanation_cache == {}


class TestExplainFinding:
    @pytest.mark.asyncio
    async def test_cache_miss_populates_finding(self):
        engine = ExplanationEngine(llm_provider=MockLLMProvider())
        finding = _make_finding()

        result = await engine.explain_finding(finding)

        assert result is finding
        assert result.ai_explanation is not None
        assert result.impact_analysis is not None
        assert result.recommendation is not None
        assert "Review" in result.recommendation or "Apply" in result.recommendation

    @pytest.mark.asyncio
    async def test_cache_hit_skips_provider(self):
        mock_provider = MockLLMProvider()
        mock_provider.generate_explanation = AsyncMock()
        engine = ExplanationEngine(llm_provider=mock_provider)
        finding = _make_finding()

        await engine.explain_finding(finding)
        call_count_after_first = mock_provider.generate_explanation.call_count

        await engine.explain_finding(_make_finding())

        assert mock_provider.generate_explanation.call_count == call_count_after_first

    @pytest.mark.asyncio
    async def test_use_cache_false_bypasses_cache(self):
        mock_provider = MockLLMProvider()
        mock_provider.generate_explanation = AsyncMock()
        engine = ExplanationEngine(llm_provider=mock_provider)

        await engine.explain_finding(_make_finding(), use_cache=False)
        await engine.explain_finding(_make_finding(), use_cache=False)

        assert mock_provider.generate_explanation.call_count == 2

    @pytest.mark.asyncio
    async def test_provider_exception_returns_finding_unchanged(self):
        mock_provider = MockLLMProvider()
        mock_provider.generate_explanation = AsyncMock(
            side_effect=RuntimeError("LLM down")
        )
        engine = ExplanationEngine(llm_provider=mock_provider)
        finding = _make_finding()
        original_rec = finding.recommendation

        result = await engine.explain_finding(finding)

        assert result is finding
        assert result.recommendation == original_rec


class TestExplainFindingsBatch:
    @pytest.mark.asyncio
    async def test_sorting_critical_before_low(self):
        engine = ExplanationEngine(llm_provider=MockLLMProvider())
        findings = [
            _make_finding(rule_id="LOW-1", severity=Severity.LOW),
            _make_finding(rule_id="INFO-1", severity=Severity.INFO),
            _make_finding(rule_id="CRIT-1", severity=Severity.CRITICAL),
            _make_finding(rule_id="MED-1", severity=Severity.MEDIUM),
        ]

        result = await engine.explain_findings_batch(findings)

        ids = [f.rule_id for f in result]
        assert ids.index("CRIT-1") < ids.index("MED-1")
        assert ids.index("MED-1") < ids.index("LOW-1")
        assert ids.index("LOW-1") < ids.index("INFO-1")

    @pytest.mark.asyncio
    async def test_max_findings_limits_enrichment(self):
        engine = ExplanationEngine(llm_provider=MockLLMProvider())
        findings = [_make_finding(rule_id=f"F-{i}", severity=Severity.HIGH) for i in range(5)]

        result = await engine.explain_findings_batch(findings, max_findings=2)

        assert len(result) == 5
        enriched = [f for f in result if f.ai_explanation is not None]
        assert len(enriched) == 2
        remaining = [f for f in result if f.ai_explanation is None]
        assert len(remaining) == 3


class TestGenerateReportSummary:
    @pytest.mark.asyncio
    async def test_success_calls_three_methods(self):
        mock_provider = AsyncMock()
        mock_provider.generate_executive_summary = AsyncMock(return_value="Summary text")
        mock_provider.generate_risk_analysis = AsyncMock(return_value="Risk text")
        mock_provider.generate_prioritized_recommendations = AsyncMock(
            return_value=["Rec 1", "Rec 2"]
        )
        engine = ExplanationEngine(llm_provider=mock_provider)
        findings = [_make_finding()]
        scores = {"security": 80.0, "reliability": 70.0}

        result = await engine.generate_report_summary(findings, scores)

        mock_provider.generate_executive_summary.assert_called_once()
        mock_provider.generate_risk_analysis.assert_called_once()
        mock_provider.generate_prioritized_recommendations.assert_called_once()
        assert result["executive_summary"] == "Summary text"
        assert result["risk_analysis"] == "Risk text"
        assert result["prioritized_recommendations"] == ["Rec 1", "Rec 2"]

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        mock_provider = AsyncMock()
        mock_provider.generate_executive_summary = AsyncMock(
            side_effect=RuntimeError("fail")
        )
        mock_provider.generate_risk_analysis = AsyncMock(return_value="Risk text")
        mock_provider.generate_prioritized_recommendations = AsyncMock(
            return_value=["Rec 1"]
        )
        engine = ExplanationEngine(llm_provider=mock_provider)
        findings = [_make_finding()]
        scores = {"security": 80.0}

        result = await engine.generate_report_summary(findings, scores)

        assert "Score:" in result["executive_summary"]
        assert result["risk_analysis"] == "Risk text"
        assert result["prioritized_recommendations"] == ["Rec 1"]

    @pytest.mark.asyncio
    async def test_all_fail_returns_fallbacks(self):
        mock_provider = AsyncMock()
        mock_provider.generate_executive_summary = AsyncMock(
            side_effect=RuntimeError("fail")
        )
        mock_provider.generate_risk_analysis = AsyncMock(
            side_effect=RuntimeError("fail")
        )
        mock_provider.generate_prioritized_recommendations = AsyncMock(
            side_effect=RuntimeError("fail")
        )
        engine = ExplanationEngine(llm_provider=mock_provider)
        findings = [_make_finding()]
        scores = {"security": 60.0, "reliability": 70.0}

        result = await engine.generate_report_summary(findings, scores)

        assert isinstance(result["executive_summary"], str)
        assert isinstance(result["risk_analysis"], str)
        assert isinstance(result["prioritized_recommendations"], list)


class TestCacheOperations:
    def test_clear_cache(self):
        engine = ExplanationEngine(llm_provider=MockLLMProvider())
        engine._explanation_cache["k1"] = "v1"
        engine._explanation_cache["k2"] = "v2"

        engine.clear_cache()

        assert engine._explanation_cache == {}

    def test_get_cache_stats(self):
        engine = ExplanationEngine(llm_provider=MockLLMProvider())
        assert engine.get_cache_stats() == {"cached_explanations": 0}

        engine._explanation_cache["k1"] = "v1"
        assert engine.get_cache_stats() == {"cached_explanations": 1}
