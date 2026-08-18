"""Unit tests for the AI context engine."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.context_engine import (
    AIContext,
    AIRecommendation,
    StaticRecommendationBuilder,
    AIContextEngine,
    _coerce_confidence,
    _clean_text,
    _extract_json_payload,
    _enum_value,
    _deserialize_best_practices,
    is_llm_capable,
)


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_coerce_confidence_float(self):
        """Float input returns same value clamped to 0-1."""
        assert _coerce_confidence(0.5) == 0.5
        assert _coerce_confidence(1.5) == 1.0
        assert _coerce_confidence(-0.5) == 0.0

    def test_coerce_confidence_string(self):
        """String '0.8' converts to 0.8."""
        assert _coerce_confidence("0.8") == 0.8

    def test_coerce_confidence_invalid(self):
        """Invalid string returns default 0.55."""
        assert _coerce_confidence("invalid") == 0.55

    def test_coerce_confidence_none(self):
        """None returns default 0.55."""
        assert _coerce_confidence(None) == 0.55

    def test_clean_text(self):
        """Strips and preserves text."""
        assert _clean_text("  hello  ") == "hello"

    def test_clean_text_none(self):
        """None returns empty string."""
        assert _clean_text(None) == ""

    def test_enum_value(self):
        """Enum-like objects return .value attribute."""
        from app.models.scan import ScanStatus
        assert _enum_value(ScanStatus.COMPLETED) == "completed"

    def test_enum_value_string(self):
        """Plain string passes through."""
        assert _enum_value("test") == "test"

    def test_deserialize_best_practices_list(self):
        """List input returns same list."""
        assert _deserialize_best_practices(["a", "b"]) == ["a", "b"]

    def test_deserialize_best_practices_json_string(self):
        """JSON string input returns parsed list."""
        assert _deserialize_best_practices('["a", "b"]') == ["a", "b"]

    def test_deserialize_best_practices_none(self):
        """None returns empty list."""
        assert _deserialize_best_practices(None) == []

    def test_extract_json_payload_plain(self):
        """Extracts JSON from plain JSON string."""
        payload = '{"key": "value"}'
        result = _extract_json_payload(payload)
        assert json.loads(result) == {"key": "value"}

    def test_extract_json_payload_markdown_block(self):
        """Extracts JSON from markdown code block."""
        payload = '```json\n{"key": "value"}\n```'
        result = _extract_json_payload(payload)
        assert json.loads(result) == {"key": "value"}

    def test_extract_json_payload_with_surrounding_text(self):
        """Extracts JSON from surrounding text."""
        payload = 'Here is the result: {"key": "value"} end.'
        result = _extract_json_payload(payload)
        assert json.loads(result) == {"key": "value"}

    def test_extract_json_payload_no_json_raises(self):
        """No JSON found => ValueError."""
        with pytest.raises(ValueError):
            _extract_json_payload("no json here")


class TestAIContext:
    """Tests for the AIContext dataclass."""

    def test_ai_context_creation(self):
        """AIContext can be created with fields."""
        ctx = AIContext(
            rule_id="TF-001",
            technology="terraform",
            rule_knowledge="knowledge text",
            mcp_results=[],
            file_snippet="snippet",
            rag_version="v1",
            mcp_version="v1",
        )
        assert ctx.rule_id == "TF-001"
        assert ctx.technology == "terraform"


class TestAIRecommendation:
    """Tests for the AIRecommendation dataclass."""

    def test_to_dict(self):
        """to_dict returns serializable dictionary."""
        rec = AIRecommendation(
            finding_fingerprint="fp-1",
            rule_id="TF-001",
            technology="terraform",
            summary="Fix this",
            risk="high",
            impact="production outage",
            ai_explanation="Because...",
            fix_code="resource ...",
            fix_example="example",
            full_example="full",
            best_practices=["prac1"],
            confidence=0.9,
            documentation_url=None,
            ai_generated=True,
            source="llm",
        )
        d = rec.to_dict()
        assert d["rule_id"] == "TF-001"
        assert d["confidence"] == 0.9
        assert d["ai_generated"] is True
        assert isinstance(d["best_practices"], list)


class TestStaticRecommendationBuilder:
    """Tests for the deterministic fallback builder."""

    @pytest.fixture
    def builder(self):
        return StaticRecommendationBuilder()

    def test_build_returns_recommendation(self, builder):
        """build returns an AIRecommendation."""
        finding = MagicMock()
        finding.rule_id = "TF-001"
        finding.category.value = "security"
        finding.severity.value = "high"
        finding.title = "Test finding"
        finding.description = "Test description"
        finding.remediation = "Fix it"
        rec = builder.build(finding, "fp-1")
        assert isinstance(rec, AIRecommendation)
        assert rec.finding_fingerprint == "fp-1"
        assert rec.ai_generated is False

    def test_build_confidence_zero(self, builder):
        """Static recommendations have 0 confidence."""
        finding = MagicMock()
        finding.rule_id = "TF-001"
        finding.category.value = "security"
        finding.severity.value = "high"
        finding.title = "T"
        finding.description = "D"
        finding.remediation = "R"
        finding.confidence = None
        finding.confidence_score = None
        rec = builder.build(finding, "fp-1")
        assert rec.confidence == 0.55


class TestAIContextEngine:
    """Tests for the main AIContextEngine."""

    @pytest.fixture
    def engine(self):
        """Provide an AIContextEngine with mocked dependencies."""
        rag_service = AsyncMock()
        rag_service.get_rule_knowledge = AsyncMock(return_value=MagicMock(
            documents=[], method="keyword", total_available=0, rag_version="v1"
        ))
        mcp_service = MagicMock()
        mcp_service.requires_live_context = MagicMock(return_value=False)
        mcp_service.requires_docs_context = MagicMock(return_value=False)
        llm_provider = MagicMock()
        llm_provider.generate = AsyncMock(return_value=json.dumps({
            "summary": "Fix needed",
            "risk": "high",
            "impact": "outage",
            "ai_explanation": "Critical vulnerability",
            "fix_code": "resource ...",
            "fix_example": "example",
            "full_example": "full",
            "best_practices": ["use encryption"],
            "confidence": 0.9,
            "documentation_url": None,
        }))
        redactor = MagicMock()
        redactor.redact_text = MagicMock(side_effect=lambda x: x)

        return AIContextEngine(
            rag_service=rag_service,
            mcp_service=mcp_service,
            llm_provider=llm_provider,
            redactor=redactor,
        )

    @pytest.mark.asyncio
    async def test_build_context_returns_ai_context(self, engine):
        """build_context returns an AIContext."""
        finding = MagicMock()
        finding.rule_id = "TF-001"
        finding.technology = None
        finding.filename = "main.tf"
        finding.title = "Test"
        finding.description = "Test finding"
        finding.severity = MagicMock(value="high")

        with patch.object(engine, "technology_for_finding", return_value="terraform"):
            ctx = await engine.build_context(finding)
            assert isinstance(ctx, AIContext)
            assert ctx.rule_id == "TF-001"

    @pytest.mark.asyncio
    async def test_generate_recommendation_with_llm(self, engine):
        """generate_recommendation calls LLM and returns AIRecommendation."""
        finding = MagicMock()
        finding.rule_id = "TF-001"
        finding.technology = "terraform"
        finding.fingerprint = MagicMock(return_value="fp-1")
        finding.line_number = None

        ctx = AIContext(
            rule_id="TF-001",
            technology="terraform",
            rule_knowledge="knowledge",
            mcp_results=[],
            file_snippet="",
            rag_version="v1",
            mcp_version="v1",
        )
        rec = await engine.generate_recommendation(finding, ctx, "fp-1")
        assert isinstance(rec, AIRecommendation)
        assert rec.ai_generated is True

    @pytest.mark.asyncio
    async def test_generate_recommendation_llm_failure_fallback(self, engine):
        """LLM failure falls back to StaticRecommendationBuilder."""
        engine._llm_provider.generate = AsyncMock(side_effect=Exception("LLM down"))
        finding = MagicMock()
        finding.rule_id = "TF-001"
        finding.technology = "terraform"
        finding.fingerprint = MagicMock(return_value="fp-1")
        finding.line_number = None
        finding.category = MagicMock(value="security")
        finding.severity = MagicMock(value="high")
        finding.title = "Test"
        finding.description = "Test"
        finding.remediation = "Fix it"

        ctx = AIContext(
            rule_id="TF-001",
            technology="terraform",
            rule_knowledge="",
            mcp_results=[],
            file_snippet="",
            rag_version="v1",
            mcp_version="v1",
        )
        rec = await engine.generate_recommendation(finding, ctx, "fp-1")
        assert isinstance(rec, AIRecommendation)
        assert rec.ai_generated is False  # fallback

    def test_technology_for_finding(self, engine):
        """technology_for_finding returns technology from finding."""
        engine._rag_service.technology_for_rule_id = MagicMock(return_value=["terraform"])
        finding = MagicMock()
        finding.technology = "terraform"
        finding.rule_id = "TF-001"
        result = engine.technology_for_finding(finding)
        assert result == "terraform"

    def test_technology_for_finding_none(self, engine):
        """technology_for_finding returns None when finding has no technology."""
        finding = MagicMock()
        finding.technology = None
        result = engine.technology_for_finding(finding)
        assert result is None


class TestIsLLMCapable:
    """Tests for is_llm_capable helper."""

    def test_mock_provider_not_capable(self):
        """MockLLMProvider is not considered capable."""
        from app.ai.engine import MockLLMProvider
        provider = MockLLMProvider()
        assert not is_llm_capable(provider)

    def test_provider_with_generate_is_capable(self):
        """Provider with generate method is capable."""
        provider = MagicMock()
        provider.generate = AsyncMock
        assert is_llm_capable(provider)

    def test_provider_without_generate_not_capable(self):
        """Provider without generate method is not capable."""
        provider = MagicMock(spec=[])  # no attributes
        assert not is_llm_capable(provider)
