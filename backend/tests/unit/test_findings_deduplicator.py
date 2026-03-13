"""Tests for findings deduplication engine."""

from app.rule_engine.base import Category, RuleFinding, Severity
from app.services.findings_deduplicator import FindingsDeduplicator, deduplicate_findings


class TestFindingsDeduplicator:
    """Test cases for FindingsDeduplicator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.deduplicator = FindingsDeduplicator()

    def test_empty_findings_list(self):
        """Test deduplication with empty list."""
        result = self.deduplicator.deduplicate([])
        assert result == []

    def test_single_finding_no_duplicates(self):
        """Test deduplication with single finding."""
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="infra/main.tf",
        )
        result = self.deduplicator.deduplicate([finding])
        assert len(result) == 1
        assert result[0].rule_id == "TF-STATE-001"

    def test_duplicate_findings_merged(self):
        """Test that duplicate findings are merged."""
        finding1 = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="infra/main.tf",
            resource_name="backend",
        )
        finding2 = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="infra/main.tf",
            resource_name="backend",
        )

        result = self.deduplicator.deduplicate([finding1, finding2])

        assert len(result) == 1
        assert result[0].metadata["occurrence_count"] == 2

    def test_different_rule_ids_not_merged(self):
        """Test that findings with different rule IDs are not merged."""
        finding1 = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="infra/main.tf",
        )
        finding2 = RuleFinding(
            rule_id="TF-STATE-002",
            rule_name="Remote Backend Required",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            description="No remote backend configured",
            recommendation="Configure remote backend",
            file_path="infra/main.tf",
        )

        result = self.deduplicator.deduplicate([finding1, finding2])

        assert len(result) == 2
        assert result[0].rule_id == "TF-STATE-001"
        assert result[1].rule_id == "TF-STATE-002"

    def test_different_files_not_merged(self):
        """Test that findings in different files are not merged."""
        finding1 = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="infra/main.tf",
        )
        finding2 = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="modules/network/main.tf",
        )

        result = self.deduplicator.deduplicate([finding1, finding2])

        assert len(result) == 2

    def test_different_resources_not_merged(self):
        """Test that findings for different resources are not merged."""
        finding1 = RuleFinding(
            rule_id="TF-ENC-001",
            rule_name="S3 Bucket Encryption Required",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="S3 bucket not encrypted",
            recommendation="Enable encryption",
            file_path="infra/s3.tf",
            resource_name="data_bucket",
        )
        finding2 = RuleFinding(
            rule_id="TF-ENC-001",
            rule_name="S3 Bucket Encryption Required",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="S3 bucket not encrypted",
            recommendation="Enable encryption",
            file_path="infra/s3.tf",
            resource_name="logs_bucket",
        )

        result = self.deduplicator.deduplicate([finding1, finding2])

        assert len(result) == 2

    def test_aggregated_description_with_multiple_occurrences(self):
        """Test that description is enhanced with occurrence count."""
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

        result = self.deduplicator.deduplicate(findings)

        assert len(result) == 1
        assert "3" in result[0].description or "found" in result[0].description.lower()

    def test_convenience_function(self):
        """Test the convenience function deduplicate_findings."""
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="infra/main.tf",
        )
        result = deduplicate_findings([finding])
        assert len(result) == 1


class TestDeduplicationKey:
    """Test deduplication key generation."""

    def test_key_includes_rule_id_file_resource(self):
        """Test that dedup key includes rule_id, file_path, and resource_name."""
        deduplicator = FindingsDeduplicator()

        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Test",
            file_path="infra/main.tf",
            resource_name="backend",
        )

        key = deduplicator._create_dedup_key(finding)
        assert "TF-STATE-001" in key
        assert "infra/main.tf" in key
        assert "backend" in key

    def test_key_handles_none_values(self):
        """Test that dedup key handles None values gracefully."""
        deduplicator = FindingsDeduplicator()

        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend Not Allowed",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Test",
            file_path=None,
            resource_name=None,
        )

        # Should not raise an exception
        key = deduplicator._create_dedup_key(finding)
        assert isinstance(key, str)
