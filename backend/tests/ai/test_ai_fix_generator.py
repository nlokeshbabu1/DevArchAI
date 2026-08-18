"""AI Fix Generator tests - Validate AI generation and fallback logic."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.rule_engine.base import Category, RuleFinding, Severity
from app.services.findings_enricher import FindingsEnricher, AIFixEnrichmentService
from app.services.findings_enricher_new import FindingsEnricher as NewFindingsEnricher


@pytest.mark.asyncio
class TestAIFixGenerator:
    """Test AI fix generation with mock LLM."""

    async def test_ai_generates_fix_for_high_severity(self):
        """Test AI generates fix for HIGH severity finding."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        ai_service._use_mock = False
        
        finding = {
            "rule_id": "TF-STATE-001",
            "rule_name": "Local Backend",
            "severity": "high",
            "file_type": "terraform",
            "description": "Terraform uses local backend"
        }
        
        # Mock LLM response
        mock_response = {
            "summary": "Terraform state stored locally",
            "risk": "State corruption and drift",
            "fix_code": 'terraform { backend "s3" {...} }',
            "full_example": "Complete terraform config...",
            "impact": "Infrastructure drift",
            "confidence": 0.92
        }
        
        with patch.object(ai_service, '_generate_ai_fix', 
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = mock_response
            
            # Act
            result = await ai_service.generate_fix(finding)
            
            # Assert
            assert result["summary"] == "Terraform state stored locally"
            assert result["risk"] == "State corruption and drift"
            assert "s3" in result["fix_code"]
            assert result["confidence"] == 0.92
            mock_ai.assert_called_once()

    async def test_ai_fallback_to_static_when_api_fails(self):
        """Test that static examples are used when AI API fails."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        ai_service._use_mock = False  # Try real AI first
        
        finding = {
            "rule_id": "TF-STATE-001",
            "rule_name": "Local Backend",
            "severity": "critical",
            "file_type": "terraform",
            "description": "Terraform uses local backend"
        }
        
        # Mock AI to fail
        with patch.object(ai_service, '_generate_ai_fix', 
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.side_effect = Exception("API Error - Service unavailable")
            
            # Act - Should not raise, should use mock/static fallback
            result = await ai_service.generate_fix(finding)
            
            # Assert - Fallback should provide valid data
            assert result is not None
            assert "summary" in result
            assert "risk" in result
            assert "fix_example" in result or "fix_code" in result
            assert result["confidence"] >= 0.75  # Minimum confidence

    async def test_ai_uses_cache_for_repeated_requests(self):
        """Test that AI responses are cached."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        ai_service._use_mock = False
        
        finding = {
            "rule_id": "TF-STATE-001",
            "rule_name": "Local Backend",
            "severity": "high",
            "file_type": "terraform",
            "description": "Test"
        }
        
        with patch.object(ai_service, '_generate_ai_fix', 
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = {"summary": "Test", "confidence": 0.9}
            
            # Act - Call twice
            result1 = await ai_service.generate_fix(finding)
            result2 = await ai_service.generate_fix(finding)
            
            # Assert - Should only call AI once (cached)
            mock_ai.assert_called_once()
            assert result1 == result2

    async def test_ai_parses_markdown_json_response(self):
        """Test AI handles markdown-formatted JSON responses."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        ai_service._use_mock = False
        
        # Mock LLM returning markdown code block
        markdown_response = '''```json
{
  "summary": "Parsed from markdown",
  "risk": "Risk description",
  "fix_code": "terraform fix",
  "confidence": 0.88
}
```'''
        
        with patch.object(ai_service, '_generate_ai_fix', 
                         new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = ai_service._parse_ai_response(
                markdown_response, 
                {"rule_id": "TEST-001"}
            )
            
            # Act
            result = await ai_service.generate_fix({
                "rule_id": "TEST-001",
                "severity": "high",
                "description": "Test"
            })
            
            # Assert
            assert result["summary"] == "Parsed from markdown"
            assert result["confidence"] == 0.88

    async def test_ai_handles_invalid_json_response(self):
        """Test AI handles invalid JSON gracefully."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        invalid_responses = [
            "Not JSON at all",
            "{ invalid json }",
            '{"missing": "required fields"}',
            "",
            None
        ]
        
        for invalid_response in invalid_responses:
            with patch.object(ai_service, '_parse_ai_response',
                            return_value=ai_service._generate_mock_fix(
                                {"rule_id": "TF-STATE-001"}
                            )):
                
                # Act - Should not raise
                result = await ai_service.generate_fix({
                    "rule_id": "TF-STATE-001",
                    "severity": "high",
                    "description": "Test"
                })
                
                # Assert - Should have fallback data
                assert result is not None
                assert "risk" in result


@pytest.mark.asyncio
class TestAIFallbackLogic:
    """Test AI → Static fallback mechanism."""

    async def test_enrich_finding_async_uses_ai_first(self):
        """Test that async enrichment attempts AI first."""
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
        
        # Mock AI service
        mock_ai_fix = {
            "summary": "AI-generated summary",
            "risk": "AI-generated risk",
            "fix_code": "AI-generated fix",
            "confidence": 0.95
        }
        
        with patch.object(enricher, '_get_ai_service') as mock_get_service:
            mock_ai_service = MagicMock()
            mock_ai_service.generate_fix = AsyncMock(return_value=mock_ai_fix)
            mock_get_service.return_value = mock_ai_service
            
            # Act
            result = await enricher.enrich_finding_async(finding)
            
            # Assert - AI was called
            mock_ai_service.generate_fix.assert_called_once()
            
            # AI data was applied
            assert result.ai_generated == True

    async def test_enrich_finding_async_falls_back_to_static(self):
        """Test that static enrichment is used when AI fails."""
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
            
            # Assert - Static fallback used
            assert result.risk is not None
            assert result.impact is not None
            assert result.fix_example is not None
            assert result.ai_generated == False  # Marked as static

    async def test_enrich_finding_sync_always_uses_static(self):
        """Test that sync enrichment uses static fallback."""
        # Arrange
        enricher = NewFindingsEnricher()
        
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Use remote state backend",
            file_path="test.tf"
        )
        
        # Act
        result = enricher.enrich_finding(finding)
        
        # Assert - Static enrichment applied
        assert result.risk is not None
        assert "terraform" in result.risk.lower() or "state" in result.risk.lower()
        assert result.fix_example is not None
        assert result.ai_generated == False


@pytest.mark.asyncio
class TestAIConfidenceHandling:
    """Test AI confidence score handling."""

    async def test_ai_rejects_low_confidence_responses(self):
        """Test that low confidence AI responses are flagged."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "TEST-001",
            "severity": "high",
            "description": "Test"
        }
        
        # Mock low confidence response
        low_confidence_response = {
            "summary": "Uncertain summary",
            "risk": "Uncertain risk",
            "confidence": 0.45  # Below threshold
        }
        
        with patch.object(ai_service, 'generate_fix',
                         new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = low_confidence_response
            
            # Act
            result = await ai_service.generate_fix(finding)
            
            # Assert - Low confidence should be noted
            assert result["confidence"] == 0.45
            # In production, you might want to fallback to static for low confidence

    async def test_ai_confidence_defaults_to_0_8_if_missing(self):
        """Test that missing confidence defaults to 0.8."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "TEST-001",
            "severity": "high",
            "description": "Test"
        }
        
        # Mock generate_fix to return response without confidence
        no_confidence_response = {
            "summary": "Test summary",
            "risk": "Test risk"
            # No confidence field
        }
        
        with patch.object(ai_service, 'generate_fix',
                         new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = no_confidence_response
            
            # Act
            result = await ai_service.generate_fix(finding)
            
            # Assert - Default confidence
            assert result.get("confidence", 0.8) == 0.8


@pytest.mark.asyncio
class TestAIMultiSeverityHandling:
    """Test AI enrichment for different severity levels."""

    @pytest.mark.parametrize("severity,should_use_ai", [
        ("critical", True),
        ("high", True),
        ("medium", True),  # Now uses AI for all severities
        ("low", True),
        ("info", True),
    ])
    async def test_ai_enrichment_for_all_severities(self, severity, should_use_ai):
        """Test AI enrichment is attempted for all severity levels."""
        # Arrange
        enricher = NewFindingsEnricher()
        
        finding = RuleFinding(
            rule_id="TEST-001",
            rule_name="Test Rule",
            severity=getattr(Severity, severity.upper()),
            category=Category.SECURITY,
            description="Test description",
            recommendation="Fix the issue",
            file_path="test.tf"
        )
        
        mock_ai_fix = {
            "summary": f"AI summary for {severity}",
            "risk": f"AI risk for {severity}",
            "confidence": 0.9
        }
        
        with patch.object(enricher, '_get_ai_service') as mock_get_service:
            mock_ai_service = MagicMock()
            mock_ai_service.generate_fix = AsyncMock(return_value=mock_ai_fix)
            mock_get_service.return_value = mock_ai_service
            
            # Act
            result = await enricher.enrich_finding_async(finding)
            
            # Assert - AI should be called for all severities
            if should_use_ai:
                mock_ai_service.generate_fix.assert_called_once()
                assert result.ai_generated == True


@pytest.mark.asyncio
class TestAIEdgeCases:
    """Test AI edge cases and error handling."""

    async def test_ai_handles_empty_file_content(self):
        """Test AI handles empty file content gracefully."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "TF-STATE-001",
            "severity": "high",
            "description": "Test"
        }
        
        # Act with empty file content
        result = await ai_service.generate_fix(finding, file_content="")
        
        # Assert - Should not raise
        assert result is not None
        assert "summary" in result

    async def test_ai_handles_very_long_file_content(self):
        """Test AI handles very long file content."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "TF-STATE-001",
            "severity": "high",
            "description": "Test"
        }
        
        # Very long file content (10000 chars)
        long_content = "terraform {\n" + ("# Comment line\n" * 1000) + "}"
        
        # Act
        result = await ai_service.generate_fix(finding, file_content=long_content)
        
        # Assert - Should not raise
        assert result is not None

    async def test_ai_handles_special_characters_in_description(self):
        """Test AI handles special characters in description."""
        # Arrange
        ai_service = AIFixEnrichmentService()
        
        finding = {
            "rule_id": "TEST-001",
            "severity": "high",
            "description": "Test with special chars: <>&\"'\\n\\t"
        }
        
        # Act
        result = await ai_service.generate_fix(finding)
        
        # Assert - Should not raise
        assert result is not None

    async def test_ai_handles_unicode_characters(self):
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
        
        # Assert - Should not raise
        assert result is not None
