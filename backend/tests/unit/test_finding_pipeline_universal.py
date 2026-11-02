"""Universal finding normalization and deduplication tests."""

from app.rule_engine.base import Category, RuleFinding, Severity
from app.scanners.deduplicator import deduplicate_across_scanners
from app.services.finding_normalizer import (
    DetectionSource,
    RemediationStatus,
    compute_remediation_status,
    normalize_finding,
    normalize_findings,
)
from app.services.findings_deduplicator import deduplicate_findings


def _finding(
    rule_id: str,
    file_path: str | None = None,
    line: int | None = None,
    scanner: str | None = None,
    package: str | None = None,
    resource: str | None = None,
) -> RuleFinding:
    f = RuleFinding(
        rule_id=rule_id,
        rule_name=rule_id,
        severity=Severity.HIGH,
        category=Category.SECURITY,
        description=f"Issue {rule_id}",
        recommendation="Fix it",
        file_path=file_path,
        line_number=line,
        resource_name=resource,
    )
    f.scanner_name = scanner
    f.package = package
    return f


def test_same_rule_different_files_not_merged_in_cross_scanner_dedup():
    a = _finding("CKV_AWS_1", "infra/a.tf", 10, scanner="Checkov")
    b = _finding("CKV_AWS_1", "infra/b.tf", 10, scanner="Checkov")
    out, stats = deduplicate_across_scanners([a, b])
    assert len(out) == 2
    assert stats.merges == 0


def test_same_package_rule_different_paths_not_merged():
    a = _finding("CVE-2024-1", "pkg/a.lock", scanner="Trivy", package="lodash")
    b = _finding("CVE-2024-1", "pkg/b.lock", scanner="Trivy", package="lodash")
    out, stats = deduplicate_across_scanners([a, b])
    assert len(out) == 2


def test_same_location_same_rule_merged_with_evidence():
    a = _finding("CKV_AWS_1", "main.tf", 5, scanner="Checkov")
    b = _finding("CKV_AWS_1", "main.tf", 5, scanner="Tfsec")
    out, stats = deduplicate_across_scanners([a, b])
    assert len(out) == 1
    assert stats.merges == 1
    assert "Checkov" in (out[0].scanner_name or "")
    assert "Tfsec" in (out[0].scanner_name or "")


def test_service_dedup_distinguishes_scanners_at_same_line():
    a = _finding("R1", "app.yaml", 1, scanner="Checkov")
    b = _finding("R1", "app.yaml", 1, scanner="Trivy")
    out, stats = deduplicate_findings([a, b])
    assert len(out) == 2
    assert stats.duplicates_removed == 0


def test_unknown_scanner_severity_maps_with_fallback():
    f = _finding("X", "f.tf", 1, scanner="CustomScanner")
    f.metadata = {"scanner_severity": "ultra-critical-unknown"}
    normalize_finding(f)
    assert f.metadata["original_severity"] == "ultra-critical-unknown"
    assert f.severity == Severity.MEDIUM
    assert f.metadata.get("severity_fallback") == "medium"


def test_remediation_status_not_fix_available_for_text_only():
    f = _finding("R", "a.tf", 1)
    f.fix_code = "# generic comment only"
    f.recommendation = "Please review"
    normalize_finding(f)
    assert compute_remediation_status(f) != RemediationStatus.FIX_AVAILABLE
    assert f.metadata["remediation_status"] in {
        RemediationStatus.AI_SUGGESTED.value,
        RemediationStatus.MANUAL_REMEDIATION.value,
    }


def test_detection_source_external_scanner():
    f = _finding("R", "a.tf", 1, scanner="Gitleaks")
    _, stats = normalize_findings([f])
    assert stats.processed == 1
    assert f.metadata["detection_source"] == DetectionSource.EXTERNAL_SCANNER.value
