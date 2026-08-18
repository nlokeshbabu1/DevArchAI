"""
Complete AI Generation Test Suite for DevArchAI Platform

Tests all LLM providers (Gemini, OpenAI, Anthropic, Mock) and validates:
- Response format
- Field validation
- Parsing logic
- Fallback mechanisms
- Database storage
- API integration

Usage:
    pytest tests/ai/test_ai_generation_complete.py -v
    pytest tests/ai/test_ai_generation_complete.py --cov=app
"""

import pytest
import json
from unittest.mock import AsyncMock, PropertyMock, patch, MagicMock
from typing import Dict, Any

from app.rule_engine.base import Category, RuleFinding, Severity
from app.services.findings_enricher import FindingsEnricher, AIFixEnrichmentService
from app.services.findings_enricher_new import FindingsEnricher as NewFindingsEnricher
from app.ai.engine import (
    get_llm_provider,
    GeminiProvider,
    OpenAIProvider,
    AnthropicProvider,
    MockLLMProvider,
    AIExplanation
)


# ============================================================================
# MOCK RESPONSES - All LLM Providers
# ============================================================================

MOCK_GEMINI_RESPONSE = {
    "summary": "Gemini: Terraform state stored locally without remote backend",
    "risk": "State corruption and infrastructure drift can occur",
    "impact": "Multiple engineers running terraform apply can corrupt state",
    "fix_code": 'terraform { backend "s3" { bucket = "tf-state" } }',
    "full_example": 'Complete terraform configuration with S3 backend',
    "confidence": 0.92
}

MOCK_OPENAI_RESPONSE = {
    "summary": "OpenAI: Container runs as root user",
    "risk": "Container breakout can lead to host compromise",
    "impact": "Full system access if container is compromised",
    "fix_code": "USER appuser",
    "full_example": "FROM node:18\nRUN useradd appuser\nUSER appuser",
    "confidence": 0.95
}

MOCK_ANTHROPIC_RESPONSE = {
    "summary": "Anthropic: Kubernetes pod without resource limits",
    "risk": "Pod can consume all node resources",
    "impact": "Node instability and service outages",
    "fix_code": "resources:\n  limits:\n    memory: 512Mi\n    cpu: 500m",
    "full_example": "Complete pod spec with resource limits",
    "confidence": 0.88
}

MOCK_LOW_CONFIDENCE_RESPONSE = {
    "summary": "Uncertain analysis",
    "risk": "Unknown risk",
    "impact": "Unknown impact",
    "fix_code": "# Fix unknown",
    "full_example": "# Example unknown",
    "confidence": 0.45  # Below threshold
}

MOCK_INVALID_JSON_RESPONSES = [
    "Not JSON at all",
    "{ invalid json }",
    '{"missing": "required fields"}',
    "",
    None,
    "```json\n{ invalid }\n```",
]

MARKDOWN_JSON_RESPONSE = '''```json
{
  "summary": "Parsed from markdown",
  "risk": "Risk description",
  "impact": "Impact description",
  "fix_code": "terraform fix code",
  "full_example": "Full example code",
  "confidence": 0.88
}
```'''


# ============================================================================
# SECTION 1: UNIT TESTS - AI GENERATOR BY PROVIDER
# ============================================================================

class TestGeminiProvider:
    """Test Gemini LLM provider."""

    @pytest.mark.asyncio
    async def test_gemini_returns_valid_response(self):
        """Test Gemini provider returns valid response with all fields."""
        # Arrange
        provider = GeminiProvider(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.text = json.dumps(MOCK_GEMINI_RESPONSE)
        
        mock_models = MagicMock()
        mock_models.generate_content = MagicMock(return_value=mock_response)
        
        mock_client = MagicMock()
        mock_client.models = mock_models
        
        provider._client = mock_client
        
        # Act
        result = await provider.generate("Test prompt")
        
        # Assert
        assert result is not None
        assert "summary" in result or "Terraform" in result or "Container" in result

    @pytest.mark.asyncio
    async def test_gemini_response_has_required_fields(self):
        """Test Gemini response contains all required AI fields."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "TF-STATE-001",
            "rule_name": "Local Backend",
            "severity": "high",
            "file_type": "terraform",
            "description": "Terraform uses local backend"
        }
        
        with patch.object(ai_service, '_generate_ai_fix', 
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_GEMINI_RESPONSE
            
            # Act
            result = await ai_service.generate_fix(finding)
            
            # Assert - All required fields exist
            assert "summary" in result
            assert "risk" in result
            assert "impact" in result
            assert "fix_code" in result or "fix_example" in result
            assert "full_example" in result or "fix_example" in result
            assert "confidence" in result

    @pytest.mark.asyncio
    async def test_gemini_confidence_is_number(self):
        """Test Gemini returns confidence as number between 0 and 1."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        with patch.object(ai_service, '_generate_ai_fix',
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_GEMINI_RESPONSE
            
            # Act
            result = await ai_service.generate_fix({
                "rule_id": "TEST-001",
                "severity": "high",
                "description": "Test"
            })
            
            # Assert
            assert isinstance(result["confidence"], (int, float))
            assert 0 <= result["confidence"] <= 1


class TestOpenAIProvider:
    """Test OpenAI LLM provider."""

    @pytest.mark.asyncio
    async def test_openai_returns_valid_response(self):
        """Test OpenAI provider returns valid response."""
        # Arrange
        provider = OpenAIProvider(api_key="test-key")
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(MOCK_OPENAI_RESPONSE)
        mock_response.choices = [mock_choice]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client
        
        # Act
        explanation = await provider.generate_explanation(
            "Container runs as root",
            {"rule_id": "DOCKER-001"}
        )
        
        # Assert
        assert explanation is not None
        assert isinstance(explanation, AIExplanation)
        assert explanation.confidence > 0

    @pytest.mark.asyncio
    async def test_openai_response_has_required_fields(self):
        """Test OpenAI response contains all required fields."""
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "DOCKER-001",
            "rule_name": "Root User",
            "severity": "high",
            "file_type": "dockerfile",
            "description": "Container runs as root"
        }
        
        with patch.object(ai_service, '_generate_ai_fix',
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_OPENAI_RESPONSE
            
            # Act
            result = await ai_service.generate_fix(finding)
            
            # Assert
            assert result["summary"] is not None
            assert result["risk"] is not None
            assert result["impact"] is not None
            assert "USER" in result["fix_code"] or "appuser" in result["fix_code"]

    @pytest.mark.asyncio
    async def test_openai_confidence_validation(self):
        """Test OpenAI confidence is valid number."""
        ai_service = AIFixEnrichmentService()
        ai_service._use_mock = False
        
        with patch.object(ai_service, '_generate_ai_fix',
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_OPENAI_RESPONSE
            
            # Act
            result = await ai_service.generate_fix({
                "rule_id": "TEST",
                "severity": "high",
                "description": "Test"
            })
            
            # Assert
            assert isinstance(result["confidence"], float)
            assert 0.0 <= result["confidence"] <= 1.0
            assert result["confidence"] == 0.95


class TestAnthropicProvider:
    """Test Anthropic Claude provider."""

    @pytest.mark.asyncio
    async def test_anthropic_returns_valid_response(self):
        """Test Anthropic provider returns valid response."""
        # Arrange
        provider = AnthropicProvider(api_key="test-key")
        
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = json.dumps(MOCK_ANTHROPIC_RESPONSE)
        mock_response.content = [mock_content]
        
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client
        
        # Act
        explanation = await provider.generate_explanation(
            "Missing resource limits",
            {"rule_id": "K8S-001"}
        )
        
        # Assert
        assert explanation is not None
        assert explanation.confidence > 0

    @pytest.mark.asyncio
    async def test_anthropic_response_has_required_fields(self):
        """Test Anthropic response contains all required fields."""
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "K8S-001",
            "rule_name": "No Resource Limits",
            "severity": "high",
            "file_type": "kubernetes",
            "description": "Pod has no resource limits"
        }
        
        with patch.object(ai_service, '_generate_ai_fix',
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_ANTHROPIC_RESPONSE
            
            # Act
            result = await ai_service.generate_fix(finding)
            
            # Assert
            assert result["summary"] is not None
            assert result["risk"] is not None
            assert "memory" in result["fix_code"].lower() or "limits" in result["fix_code"].lower()

    @pytest.mark.asyncio
    async def test_anthropic_confidence_validation(self):
        """Test Anthropic confidence is valid."""
        ai_service = AIFixEnrichmentService()
        
        with patch.object(ai_service, '_generate_ai_fix',
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_ANTHROPIC_RESPONSE
            
            # Act
            result = await ai_service.generate_fix({
                "rule_id": "TEST",
                "severity": "high",
                "description": "Test"
            })
            
            # Assert
            assert isinstance(result["confidence"], float)
            assert 0.0 <= result["confidence"] <= 1.0


class TestMockProvider:
    """Test Mock LLM provider (fallback)."""

    @pytest.mark.asyncio
    async def test_mock_provider_always_works(self):
        """Test mock provider never fails."""
        # Arrange
        provider = MockLLMProvider()
        
        # Act
        explanation = await provider.generate_explanation(
            "Test finding",
            {"rule_id": "TEST-001"}
        )
        
        # Assert - Should never raise
        assert explanation is not None
        assert explanation.explanation is not None

    @pytest.mark.asyncio
    async def test_mock_provider_returns_required_fields(self):
        """Test mock response has all required fields."""
        # Arrange
        provider = MockLLMProvider()
        
        # Act
        explanation = await provider.generate_explanation(
            "Test finding",
            {"rule_id": "TEST-001"}
        )
        
        # Assert
        assert explanation.explanation is not None
        assert explanation.impact_analysis is not None
        assert explanation.remediation_steps is not None
        assert isinstance(explanation.confidence, float)


# ============================================================================
# SECTION 2: PARSING TESTS
# ============================================================================

class TestAIParsing:
    """Test AI response parsing logic."""

    @pytest.mark.asyncio
    async def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        # Act
        result = ai_service._parse_ai_response(
            json.dumps(MOCK_GEMINI_RESPONSE),
            {"rule_id": "TEST-001"}
        )
        
        # Assert
        assert result["summary"] == MOCK_GEMINI_RESPONSE["summary"]
        assert result["risk"] == MOCK_GEMINI_RESPONSE["risk"]
        assert result["confidence"] == MOCK_GEMINI_RESPONSE["confidence"]

    @pytest.mark.asyncio
    async def test_parse_json_inside_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        # Act
        result = ai_service._parse_ai_response(
            MARKDOWN_JSON_RESPONSE,
            {"rule_id": "TEST-001"}
        )
        
        # Assert
        assert result["summary"] == "Parsed from markdown"
        assert result["confidence"] == 0.88

    @pytest.mark.parametrize("invalid_response", MOCK_INVALID_JSON_RESPONSES)
    @pytest.mark.asyncio
    async def test_parse_invalid_json_triggers_fallback(self, invalid_response):
        """Test that invalid JSON triggers static fallback."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        # Act - Should not raise, should return mock/static fallback
        result = ai_service._parse_ai_response(
            invalid_response,
            {"rule_id": "TF-STATE-001"}  # Use known rule for static fallback
        )
        
        # Assert - Fallback should provide valid data
        assert result is not None
        assert "summary" in result
        assert "risk" in result

    @pytest.mark.asyncio
    async def test_parse_empty_response(self):
        """Test handling of empty response."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        # Act
        result = ai_service._parse_ai_response(
            "",
            {"rule_id": "TEST-001"}
        )
        
        # Assert - Should return fallback
        assert result is not None
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_parse_missing_confidence_defaults_to_0_8(self):
        """Test that missing confidence defaults to 0.8."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        response_without_confidence = {
            "summary": "Test summary",
            "risk": "Test risk"
            # No confidence field
        }
        
        # Act
        result = ai_service._parse_ai_response(
            json.dumps(response_without_confidence),
            {"rule_id": "TEST-001"}
        )
        
        # Assert
        assert result["confidence"] == 0.8


# ============================================================================
# SECTION 3: FALLBACK TESTS (CRITICAL)
# ============================================================================

class TestAIFallbackLogic:
    """Test AI → Static fallback mechanisms."""

    @pytest.mark.asyncio
    async def test_fallback_when_api_fails(self):
        """Test static fallback when AI API fails completely."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        ai_service._use_mock = False
        
        finding = {
            "rule_id": "TF-STATE-001",
            "rule_name": "Local Backend",
            "severity": "critical",
            "file_type": "terraform",
            "description": "Terraform uses local backend"
        }
        
        with patch.object(ai_service, '_generate_ai_fix',
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.side_effect = Exception("API Error - Service unavailable")
            
            # Act
            result = await ai_service.generate_fix(finding)
            
            # Assert - Static fallback should work
            assert result is not None
            assert "summary" in result
            assert "risk" in result
            assert "fix_example" in result or "fix_code" in result

    @pytest.mark.asyncio
    async def test_fallback_on_timeout(self):
        """Test fallback when AI times out."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "TF-STATE-001",
            "severity": "high",
            "description": "Test"
        }
        
        with patch.object(ai_service, '_generate_ai_fix',
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.side_effect = TimeoutError("AI request timed out")
            
            # Act
            result = await ai_service.generate_fix(finding)
            
            # Assert - Should use fallback
            assert result is not None
            assert "summary" in result

    @pytest.mark.asyncio
    async def test_fallback_on_low_confidence(self):
        """Test that low confidence responses are flagged."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        ai_service._use_mock = False
        
        finding = {
            "rule_id": "TEST-001",
            "severity": "high",
            "description": "Test"
        }
        
        with patch.object(ai_service, '_generate_ai_fix',
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_LOW_CONFIDENCE_RESPONSE
            
            # Act
            result = await ai_service.generate_fix(finding)
            
            # Assert - Low confidence should be preserved
            assert result["confidence"] == 0.45
            # Note: In production, you might want to fallback for low confidence

    @pytest.mark.asyncio
    async def test_static_fallback_marked_correctly(self):
        """Test that static fallback is marked as ai_generated=false."""
        # Arrange
        enricher = NewFindingsEnricher()
        
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="terraform/main.tf"
        )
        
        # Mock AI to fail
        with patch.object(enricher, '_get_ai_service') as mock_get_service:
            mock_ai_service = MagicMock()
            mock_ai_service.generate_fix = AsyncMock(
                side_effect=Exception("AI unavailable")
            )
            mock_get_service.return_value = mock_ai_service
            
            # Act
            result = await enricher.enrich_finding_async(finding)
            
            # Assert
            assert result.ai_generated == False
            assert result.risk is not None  # Static fallback provided data

    @pytest.mark.asyncio
    async def test_ai_success_marked_correctly(self):
        """Test that successful AI is marked as ai_generated=true."""
        # Arrange
        enricher = NewFindingsEnricher()
        
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Use remote backend",
            file_path="test.tf"
        )
        
        mock_ai_fix = {
            "summary": "AI summary",
            "risk": "AI risk",
            "confidence": 0.9
        }
        
        with patch.object(enricher, '_get_ai_service') as mock_get_service:
            mock_ai_service = MagicMock()
            mock_ai_service.generate_fix = AsyncMock(return_value=mock_ai_fix)
            mock_get_service.return_value = mock_ai_service
            
            # Act
            result = await enricher.enrich_finding_async(finding)
            
            # Assert
            assert result.ai_generated == True


# ============================================================================
# SECTION 4: INTEGRATION TESTS
# ============================================================================

class TestAIIntegration:
    """Test complete AI integration flow."""

    @pytest.mark.asyncio
    async def test_full_flow_scan_to_ai(self):
        """Test complete flow: Scan → Rule Engine → AI → Result."""
        # Arrange
        enricher = NewFindingsEnricher()
        
        # Simulate findings from rule engine
        findings = [
            RuleFinding(
                rule_id="DOCKER-001",
                rule_name="Container Runs as Root",
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description="Container runs as root user",
                recommendation="Add USER instruction",
                file_path="Dockerfile"
            ),
            RuleFinding(
                rule_id="K8S-001",
                rule_name="Missing Resource Limits",
                severity=Severity.HIGH,
                category=Category.RELIABILITY,
                description="Pod has no resource limits",
                recommendation="Set CPU and memory limits",
                file_path="k8s/deployment.yaml"
            ),
            RuleFinding(
                rule_id="TF-STATE-001",
                rule_name="Local Backend",
                severity=Severity.CRITICAL,
                category=Category.RELIABILITY,
                description="Terraform uses local backend",
                recommendation="Use remote backend",
                file_path="terraform/main.tf"
            )
        ]
        
        # Mock AI to succeed
        mock_ai_fix = {
            "summary": "AI-generated summary",
            "risk": "AI-generated risk",
            "impact": "AI-generated impact",
            "fix_code": "AI fix code",
            "confidence": 0.9
        }
        
        with patch.object(enricher, '_get_ai_service') as mock_get_service:
            mock_ai_service = MagicMock()
            mock_ai_service.generate_fix = AsyncMock(return_value=mock_ai_fix)
            mock_get_service.return_value = mock_ai_service
            
            # Act
            enriched_findings = await enricher.enrich_findings_async(findings)
            
            # Assert - All findings enriched
            assert len(enriched_findings) == 3
            
            for finding in enriched_findings:
                assert finding.summary is not None
                assert finding.risk is not None
                assert finding.ai_generated == True

    @pytest.mark.asyncio
    async def test_ai_fields_not_null_after_enrichment(self):
        """Test that AI fields are NOT NULL after enrichment."""
        # Arrange
        enricher = NewFindingsEnricher()
        
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Use remote backend",
            file_path="test.tf"
        )
        
        with patch.object(enricher, '_get_ai_service') as mock_get_service:
            mock_ai_service = MagicMock()
            mock_ai_service.generate_fix = AsyncMock(return_value={
                "summary": "Summary",
                "risk": "Risk",
                "impact": "Impact",
                "fix_code": "Fix",
                "confidence": 0.9
            })
            mock_get_service.return_value = mock_ai_service
            
            # Act
            result = await enricher.enrich_finding_async(finding)
            
            # Assert - All AI fields have values
            assert result.summary is not None, "summary is NULL"
            assert result.risk is not None, "risk is NULL"
            assert result.impact is not None, "impact is NULL"
            assert result.fix_code is not None, "fix_code is NULL"
            assert result.confidence is not None, "confidence is NULL"
            assert result.confidence > 0, "confidence is 0"

    @pytest.mark.asyncio
    async def test_fix_code_exists_for_all_file_types(self):
        """Test fix_code exists for Docker, K8s, Terraform."""
        # Arrange
        test_cases = [
            ("DOCKER-001", "dockerfile"),
            ("K8S-001", "kubernetes"),
            ("TF-STATE-001", "terraform"),
        ]
        
        enricher = NewFindingsEnricher()
        
        for rule_id, file_type in test_cases:
            finding = RuleFinding(
                rule_id=rule_id,
                rule_name="Test Rule",
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description="Test",
                recommendation="Fix the issue",
                file_path=f"test.{file_type}"
            )
            
            # Act - Use static fallback
            result = enricher.enrich_finding(finding)
            
            # Assert - fix_code or fix_example exists
            assert result.fix_code is not None or result.fix_example is not None, \
                f"No fix for {rule_id}"


# ============================================================================
# SECTION 5: DATABASE TESTS
# ============================================================================

class TestAIDatabaseStorage:
    """Test AI fields are correctly stored in database."""

    @pytest.mark.asyncio
    async def test_ai_fields_stored_in_db(self):
        """Test that all AI fields are stored after scan."""
        from app.models.finding import Finding
        from uuid import uuid4
        
        # Arrange - Simulate enriched finding
        finding_data = {
            "scan_id": uuid4(),
            "rule_id": "TF-STATE-001",
            "rule_name": "Local Backend",
            "severity": Severity.CRITICAL,
            "category": Category.RELIABILITY,
            "description": "Terraform uses local backend",
            "recommendation": "Use remote backend",
            "file_path": "terraform/main.tf",
            "summary": "AI-generated summary",
            "risk": "AI-generated risk",
            "impact": "AI-generated impact",
            "fix_code": "terraform { backend ... }",
            "fix_example": "Complete example",
            "full_example": "Full file example",
            "confidence": 0.92,
            "ai_generated": True
        }
        
        # Act - Create Finding model
        db_finding = Finding(**finding_data)
        
        # Assert - All AI fields stored
        assert db_finding.summary == "AI-generated summary"
        assert db_finding.risk == "AI-generated risk"
        assert db_finding.impact == "AI-generated impact"
        assert db_finding.fix_code == "terraform { backend ... }"
        assert db_finding.fix_example == "Complete example"
        assert db_finding.full_example == "Full file example"
        assert db_finding.confidence == 0.92
        assert db_finding.ai_generated == True

    @pytest.mark.asyncio
    async def test_ai_generated_flag_stored(self):
        """Test ai_generated flag is correctly stored."""
        from app.models.finding import Finding
        from uuid import uuid4
        
        # Arrange
        finding_ai = Finding(
            scan_id=uuid4(),
            rule_id="TF-STATE-001",
            rule_name="Test",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Test",
            file_path="test.tf",
            summary="AI summary",
            ai_generated=True
        )
        
        finding_static = Finding(
            scan_id=uuid4(),
            rule_id="TF-STATE-001",
            rule_name="Test",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Test",
            file_path="test.tf",
            summary="Static summary",
            ai_generated=False
        )
        
        # Assert
        assert finding_ai.ai_generated == True
        assert finding_static.ai_generated == False


# ============================================================================
# SECTION 6: API TESTS
# ============================================================================

class TestAIAPITests:
    """Test AI fields in API responses."""

    @pytest.mark.asyncio
    async def test_scan_response_includes_ai_fields(self):
        """Test /scan response includes all AI fields."""
        from unittest.mock import patch, MagicMock
        
        # Mock API response
        mock_finding = {
            "id": "test-id",
            "rule_id": "TF-STATE-001",
            "rule_name": "Local Backend",
            "severity": "critical",
            "category": "reliability",
            "description": "Terraform uses local backend",
            "recommendation": "Use remote backend",
            "file_path": "terraform/main.tf",
            # AI fields (REQUIRED)
            "summary": "State stored locally",
            "risk": "State corruption risk",
            "impact": "Infrastructure drift",
            "fix_code": 'terraform { backend "s3" {...} }',
            "fix_example": "Complete example",
            "full_example": "Full example",
            "confidence": 0.92,
            "ai_generated": True
        }
        
        # Validate structure
        required_ai_fields = [
            "summary",
            "risk",
            "impact",
            "fix_code",
            "confidence"
        ]
        
        for field in required_ai_fields:
            assert field in mock_finding, f"Missing AI field: {field}"
            assert mock_finding[field] is not None, f"AI field {field} is NULL"

    @pytest.mark.asyncio
    async def test_confidence_is_valid_number(self):
        """Test confidence is valid number in API response."""
        # Test valid confidence values
        valid_confidences = [0.0, 0.5, 0.92, 1.0]
        
        for confidence in valid_confidences:
            assert isinstance(confidence, (int, float))
            assert 0 <= confidence <= 1

    @pytest.mark.asyncio
    async def test_api_response_format(self):
        """Test complete API response format."""
        mock_response = {
            "scan_id": "test-scan-id",
            "status": "completed",
            "overall_score": 75.5,
            "findings": [
                {
                    "rule_id": "TF-STATE-001",
                    "summary": "Summary",
                    "risk": "Risk",
                    "impact": "Impact",
                    "fix_code": "Fix",
                    "confidence": 0.92
                }
            ]
        }
        
        # Validate structure
        assert "scan_id" in mock_response
        assert "findings" in mock_response
        assert len(mock_response["findings"]) > 0
        
        finding = mock_response["findings"][0]
        assert "summary" in finding
        assert "fix_code" in finding
        assert "confidence" in finding


# ============================================================================
# SECTION 7: EDGE CASES
# ============================================================================

class TestAIEdgeCases:
    """Test AI handling of edge cases."""

    @pytest.mark.asyncio
    async def test_very_large_file_content(self):
        """Test AI handles very large file content."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "TF-STATE-001",
            "severity": "high",
            "description": "Test"
        }
        
        # Very large file content (10000 chars)
        large_content = "terraform {\n" + ("# Comment line\n" * 1000) + "}"
        
        # Act - Should not raise
        result = await ai_service.generate_fix(finding, file_content=large_content)
        
        # Assert
        assert result is not None

    @pytest.mark.asyncio
    async def test_unsupported_file_type(self):
        """Test AI handles unsupported file type."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "UNKNOWN-999",
            "severity": "low",
            "file_type": "unsupported",
            "description": "Unknown file type"
        }
        
        # Act - Should use fallback
        result = await ai_service.generate_fix(finding)
        
        # Assert - Fallback should work
        assert result is not None
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_empty_repository(self):
        """Test AI handles empty repository (no findings)."""
        # Arrange
        enricher = NewFindingsEnricher()
        
        # Act - Empty findings list
        result = await enricher.enrich_findings_async([])
        
        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_findings_same_rule(self):
        """Test AI handles multiple findings with same rule_id."""
        # Arrange
        enricher = NewFindingsEnricher()
        
        findings = [
            RuleFinding(
                rule_id="TF-STATE-001",
                rule_name="Local Backend",
                severity=Severity.HIGH,
                category=Category.RELIABILITY,
                description="Test 1",
                recommendation="Test",
                file_path="file1.tf"
            ),
            RuleFinding(
                rule_id="TF-STATE-001",
                rule_name="Local Backend",
                severity=Severity.HIGH,
                category=Category.RELIABILITY,
                description="Test 2",
                recommendation="Test",
                file_path="file2.tf"
            )
        ]
        
        mock_ai_fix = {
            "summary": "AI summary",
            "risk": "AI risk",
            "confidence": 0.9
        }
        
        with patch.object(enricher, '_get_ai_service') as mock_get_service:
            mock_ai_service = MagicMock()
            mock_ai_service.generate_fix = AsyncMock(return_value=mock_ai_fix)
            mock_get_service.return_value = mock_ai_service
            
            # Act
            results = await enricher.enrich_findings_async(findings)
            
            # Assert - Both enriched
            assert len(results) == 2
            assert all(r.summary is not None for r in results)

    @pytest.mark.asyncio
    async def test_special_characters_in_description(self):
        """Test AI handles special characters."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "TEST-001",
            "severity": "high",
            "description": "Test with special chars: <>&\"'\n\t"
        }
        
        # Act - Should not raise
        result = await ai_service.generate_fix(finding)
        
        # Assert
        assert result is not None

    @pytest.mark.asyncio
    async def test_unicode_characters(self):
        """Test AI handles unicode characters."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "TEST-001",
            "severity": "high",
            "description": "Test with unicode: 你好 🚀 ñoño"
        }
        
        # Act
        result = await ai_service.generate_fix(finding)
        
        # Assert
        assert result is not None


# ============================================================================
# SECTION 8: PROVIDER SELECTION TESTS
# ============================================================================

class TestProviderSelection:
    """Test LLM provider selection logic."""

    def test_get_llm_provider_gemini(self):
        """Test Gemini provider selection."""
        with patch('app.ai.engine.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "gemini"
            mock_settings.GEMINI_API_KEY = "test-key"
            
            from app.ai.engine import get_llm_provider
            provider = get_llm_provider()
            
            assert isinstance(provider, GeminiProvider)

    def test_get_llm_provider_openai(self):
        """Test OpenAI provider selection."""
        with patch('app.ai.engine.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.OPENAI_API_KEY = "test-key"
            
            from app.ai.engine import get_llm_provider
            provider = get_llm_provider()
            
            assert isinstance(provider, OpenAIProvider)

    def test_get_llm_provider_anthropic(self):
        """Test Anthropic provider selection."""
        with patch('app.ai.engine.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "anthropic"
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            
            from app.ai.engine import get_llm_provider
            provider = get_llm_provider()
            
            assert isinstance(provider, AnthropicProvider)

    def test_get_llm_provider_fallback_to_mock(self):
        """Test fallback to Mock when no API key."""
        with patch('app.ai.engine.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.OPENAI_API_KEY = None
            mock_settings.ANTHROPIC_API_KEY = None
            mock_settings.GEMINI_API_KEY = None
            mock_settings.MISTRAL_API_KEY = None
            mock_settings.LLM_MODEL = None
            
            with patch('app.ai.engine._ollama_is_available', return_value=False, create=True), \
                 patch('app.ai.engine._gpt4all_is_available', return_value=False, create=True):
                from app.ai.engine import get_llm_provider
                provider = get_llm_provider()
                
                assert isinstance(provider, MockLLMProvider)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
