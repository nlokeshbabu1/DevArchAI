"""
Service Layer Tests

Tests for service layer functionality
"""

from app.rule_engine.base import Category, RuleFinding, Severity
from app.services.findings_deduplicator import FindingsDeduplicator, deduplicate_findings
from app.services.findings_enricher import FindingsEnricher, enrich_findings


class TestFindingsDeduplicator:
    """Test findings deduplication service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.deduplicator = FindingsDeduplicator()

    def test_deduplicate_empty_list(self):
        """Test deduplication with empty list."""
        findings, stats = self.deduplicator.deduplicate([])
        assert findings == []
        assert stats.original_count == 0
        assert stats.duplicates_removed == 0

    def test_deduplicate_single_finding(self):
        """Test deduplication with single finding."""
        finding = RuleFinding(
            rule_id="TEST-001",
            rule_name="Test Rule",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Test description",
            recommendation="Test recommendation",
            file_path="test.tf",
        )
        findings, stats = self.deduplicator.deduplicate([finding])
        assert len(findings) == 1
        assert findings[0].rule_id == "TEST-001"
        assert stats.deduplicated_count == 1

    def test_deduplicate_identical_findings(self):
        """Test deduplication removes identical findings."""
        finding1 = RuleFinding(
            rule_id="TEST-001",
            rule_name="Test Rule",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Test",
            recommendation="Test",
            file_path="test.tf",
        )
        finding2 = RuleFinding(
            rule_id="TEST-001",
            rule_name="Test Rule",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Test",
            recommendation="Test",
            file_path="test.tf",
        )
        findings, stats = self.deduplicator.deduplicate([finding1, finding2])
        assert len(findings) == 1
        assert stats.duplicates_removed == 1

    def test_deduplicate_different_files(self):
        """Test findings in different files are not merged."""
        finding1 = RuleFinding(
            rule_id="TEST-001",
            rule_name="Test Rule",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Test",
            recommendation="Test",
            file_path="file1.tf",
        )
        finding2 = RuleFinding(
            rule_id="TEST-001",
            rule_name="Test Rule",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Test",
            recommendation="Test",
            file_path="file2.tf",
        )
        findings, stats = self.deduplicator.deduplicate([finding1, finding2])
        assert len(findings) == 2
        assert stats.duplicates_removed == 0


class TestFindingsEnricher:
    """Test findings enrichment service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.enricher = FindingsEnricher()

    def test_enrich_empty_list(self):
        """Test enrichment with empty list."""
        result = self.enricher.enrich_findings([])
        assert result == []

    def test_enrich_finding_with_known_rule(self):
        """Test enrichment for known rule."""
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Test",
            file_path="test.tf",
        )
        result = self.enricher.enrich_finding(finding)

        assert result.risk is not None
        assert result.impact is not None
        assert result.fix_example is not None

    def test_enrich_finding_unknown_rule(self):
        """Test enrichment for unknown rule."""
        finding = RuleFinding(
            rule_id="UNKNOWN-999",
            rule_name="Unknown Rule",
            severity=Severity.INFO,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Test",
            file_path="test.tf",
        )
        result = self.enricher.enrich_finding(finding)

        # Should not raise exception
        assert result.rule_id == "UNKNOWN-999"

    def test_enrich_does_not_overwrite(self):
        """Test enrichment doesn't overwrite existing values."""
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Test",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Test",
            recommendation="Test",
            file_path="test.tf",
            risk="Custom risk",
            impact="Custom impact",
            fix_example="custom_code",
        )
        result = self.enricher.enrich_finding(finding)

        assert result.risk == "Custom risk"
        assert result.impact == "Custom impact"
        assert result.fix_example == "custom_code"


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_deduplicate_findings_function(self):
        """Test deduplicate_findings convenience function."""
        finding = RuleFinding(
            rule_id="TEST-001",
            rule_name="Test",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Test",
            recommendation="Test",
            file_path="test.tf",
        )
        findings, stats = deduplicate_findings([finding])
        assert len(findings) == 1
        assert stats.deduplicated_count == 1

    def test_enrich_findings_function(self):
        """Test enrich_findings convenience function."""
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Test",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Test",
            recommendation="Test",
            file_path="test.tf",
        )
        result = enrich_findings([finding])
        assert len(result) == 1
