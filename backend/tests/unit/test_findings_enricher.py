"""Tests for findings enrichment service."""

from app.rule_engine.base import Category, RuleFinding, Severity
from app.services.findings_enricher import FIX_EXAMPLES, FindingsEnricher, enrich_findings


class TestFindingsEnricher:
    """Test cases for FindingsEnricher."""

    def setup_method(self):
        """Set up test fixtures."""
        self.enricher = FindingsEnricher()

    def test_empty_findings_list(self):
        """Test enrichment with empty list."""
        result = self.enricher.enrich_findings([])
        assert result == []

    def test_enrich_finding_with_known_rule(self):
        """Test enrichment for a known rule ID."""
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="infra/main.tf",
        )

        result = self.enricher.enrich_finding(finding)

        assert result.risk is not None
        assert result.impact is not None
        assert result.fix_example is not None
        assert "state" in result.risk.lower() or "terraform" in result.risk.lower()

    def test_enrich_finding_unknown_rule(self):
        """Test enrichment for unknown rule ID doesn't break."""
        finding = RuleFinding(
            rule_id="UNKNOWN-999",
            rule_name="Unknown Rule",
            severity=Severity.INFO,
            category=Category.RELIABILITY,
            description="Some issue",
            recommendation="Fix it",
            file_path="test.tf",
        )

        # Should not raise an exception
        result = self.enricher.enrich_finding(finding)
        assert result.rule_id == "UNKNOWN-999"

    def test_enrich_does_not_overwrite_existing_values(self):
        """Test that enrichment doesn't overwrite existing risk/impact/fix_example."""
        original_risk = "Custom risk description"
        original_impact = "Custom impact description"
        original_fix = "custom_fix_code"

        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="infra/main.tf",
            risk=original_risk,
            impact=original_impact,
            fix_example=original_fix,
        )

        result = self.enricher.enrich_finding(finding)

        assert result.risk == original_risk
        assert result.impact == original_impact
        assert result.fix_example == original_fix

    def test_enrich_multiple_findings(self):
        """Test enrichment of multiple findings."""
        findings = [
            RuleFinding(
                rule_id="TF-STATE-001",
                rule_name="Local Backend Not Allowed",
                severity=Severity.CRITICAL,
                category=Category.RELIABILITY,
                description="Terraform uses local backend",
                recommendation="Use remote backend",
                file_path="infra/main.tf",
            ),
            RuleFinding(
                rule_id="TF-ENC-001",
                rule_name="S3 Bucket Encryption Required",
                severity=Severity.HIGH,
                category=Category.SECURITY,
                description="S3 bucket not encrypted",
                recommendation="Enable encryption",
                file_path="infra/s3.tf",
            ),
        ]

        result = self.enricher.enrich_findings(findings)

        assert len(result) == 2
        assert result[0].risk is not None
        assert result[1].risk is not None

    def test_convenience_function(self):
        """Test the convenience function enrich_findings."""
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="infra/main.tf",
        )
        result = enrich_findings([finding])
        assert len(result) == 1
        assert result[0].risk is not None


class TestFixExamplesLibrary:
    """Test the fix examples library."""

    def test_fix_examples_has_terraform_rules(self):
        """Test that fix examples library has Terraform rules."""
        assert "TF-STATE-001" in FIX_EXAMPLES
        assert "TF-STATE-002" in FIX_EXAMPLES
        assert "TF-STATE-003" in FIX_EXAMPLES
        assert "TF-STATE-004" in FIX_EXAMPLES

    def test_fix_examples_has_required_fields(self):
        """Test that fix examples have required fields."""
        for rule_id, data in FIX_EXAMPLES.items():
            assert "risk" in data, f"Missing 'risk' for {rule_id}"
            assert "impact" in data, f"Missing 'impact' for {rule_id}"
            assert "fix_example" in data, f"Missing 'fix_example' for {rule_id}"

    def test_fix_example_terraform_state_locking(self):
        """Test specific fix example for state locking."""
        fix_data = FIX_EXAMPLES.get("TF-STATE-003", {})
        assert "dynamodb_table" in fix_data.get("fix_example", "") or "lock" in fix_data.get("fix_example", "").lower()

    def test_fix_example_s3_encryption(self):
        """Test specific fix example for S3 encryption."""
        fix_data = FIX_EXAMPLES.get("TF-ENC-001", {})
        fix_example = fix_data.get("fix_example", "")
        assert "encryption" in fix_example.lower() or "sse" in fix_example.lower()


class TestEnrichmentIntegration:
    """Integration tests for enrichment with deduplication."""

    def test_enrich_after_deduplication(self):
        """Test that enrichment works correctly after deduplication."""
        from app.services.findings_deduplicator import FindingsDeduplicator

        deduplicator = FindingsDeduplicator()
        enricher = FindingsEnricher()

        # Create duplicate findings
        findings = [
            RuleFinding(
                rule_id="TF-STATE-001",
                rule_name="Local Backend Not Allowed",
                severity=Severity.CRITICAL,
                category=Category.RELIABILITY,
                description="Terraform uses local backend",
                recommendation="Use remote backend",
                file_path="infra/main.tf",
                resource_name="backend",
            )
            for _ in range(3)
        ]

        # Deduplicate first
        deduplicated = deduplicator.deduplicate(findings)
        assert len(deduplicated) == 1

        # Then enrich
        enriched = enricher.enrich_findings(deduplicated)
        assert len(enriched) == 1
        assert enriched[0].risk is not None
        assert enriched[0].impact is not None
        assert enriched[0].fix_example is not None

    def test_deduplication_preserves_enrichment(self):
        """Test that deduplication preserves existing enrichment."""
        from app.services.findings_deduplicator import FindingsDeduplicator

        deduplicator = FindingsDeduplicator()
        enricher = FindingsEnricher()

        # Create findings with enrichment
        findings = [
            RuleFinding(
                rule_id="TF-STATE-001",
                rule_name="Local Backend Not Allowed",
                severity=Severity.CRITICAL,
                category=Category.RELIABILITY,
                description="Terraform uses local backend",
                recommendation="Use remote backend",
                file_path="infra/main.tf",
                resource_name="backend",
                risk="Custom risk",
                impact="Custom impact",
                fix_example="custom_code",
            )
            for _ in range(2)
        ]

        # Enrich first
        enriched = enricher.enrich_findings(findings)

        # Then deduplicate - should preserve enrichment
        deduplicated = deduplicator.deduplicate(enriched)

        assert len(deduplicated) == 1
        # The first finding's enrichment should be preserved
        assert deduplicated[0].risk is not None
