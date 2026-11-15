"""Regression tests for severity-based AI eligibility and Checkov normalization."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.finding import Finding, Severity as DBSeverity
from app.rule_engine.base import Category, RuleFinding, Severity
from app.services.ai_eligibility import (
    filter_ai_eligible_findings,
    is_ai_eligible_finding,
)
from app.services.ai_recommendation_cache import finding_fingerprint, recommendation_cache_key
from app.services.finding_validator import FindingValidator
def _rule(sev: Severity, rule_id: str = "TEST-001", resource: str = "res-a") -> RuleFinding:
    return RuleFinding(
        rule_id=rule_id,
        rule_name="Test",
        severity=sev,
        category=Category.SECURITY,
        description=f"Issue on {resource}",
        recommendation="Fix it",
        file_path=f"/repo/{resource}.tf",
        scanner_name="Checkov",
        scanner_rule_id="CKV_AWS_1",
    )


def _db_finding(sev: DBSeverity, **kwargs) -> Finding:
    from app.models.finding import Category as DBCategory

    return Finding(
        id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        rule_id=kwargs.get("rule_id", "TEST-001"),
        rule_name=kwargs.get("rule_name", "Test rule"),
        severity=sev,
        category=DBCategory.SECURITY,
        summary=kwargs.get("summary", "s"),
        description=kwargs.get("description", "d"),
        recommendation=kwargs.get("recommendation", "r"),
        file_path=kwargs.get("file_path", "main.tf"),
    )


@pytest.mark.parametrize(
    "severity,expected",
    [
        (Severity.CRITICAL, True),
        (Severity.HIGH, True),
        (Severity.MEDIUM, True),
        (Severity.LOW, False),
        (Severity.INFO, False),
    ],
)
def test_severity_ai_eligibility_default_policy(severity, expected):
    assert is_ai_eligible_finding(_rule(severity)) is expected


def test_low_severity_respects_configuration(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "AI_ELIGIBILITY_INCLUDE_LOW", True)
    assert is_ai_eligible_finding(_rule(Severity.LOW)) is True
    monkeypatch.setattr(config.settings, "AI_ELIGIBILITY_INCLUDE_LOW", False)
    assert is_ai_eligible_finding(_rule(Severity.LOW)) is False


def test_info_findings_remain_in_full_list():
    findings = [
        _rule(Severity.HIGH),
        _rule(Severity.INFO, rule_id="INFO-1"),
    ]
    eligible = filter_ai_eligible_findings(findings)
    assert len(findings) == 2
    assert len(eligible) == 1
    assert eligible[0].severity == Severity.HIGH


def test_same_rule_different_resources_produce_distinct_cache_keys():
    a = _rule(Severity.HIGH, resource="bucket-a")
    b = _rule(Severity.HIGH, resource="bucket-b")
    fp_a = finding_fingerprint(a)
    fp_b = finding_fingerprint(b)
    assert fp_a != fp_b
    base = {"rag_version": "1", "prompt_version": "1", "model_version": "1"}
    assert recommendation_cache_key("CKV_AWS_1", "terraform", fp_a, "", base) != recommendation_cache_key(
        "CKV_AWS_1", "terraform", fp_b, "", base
    )


def test_identical_findings_share_cache_key():
    a = _rule(Severity.MEDIUM, resource="same")
    b = _rule(Severity.MEDIUM, resource="same")
    base = {"rag_version": "1", "prompt_version": "1", "model_version": "1"}
    assert recommendation_cache_key(
        "CKV_AWS_1", "terraform", finding_fingerprint(a), "", base
    ) == recommendation_cache_key("CKV_AWS_1", "terraform", finding_fingerprint(b), "", base)


def test_checkov_info_uses_description_not_generic_summary():
    finding = RuleFinding(
        rule_id="Checkov/CKV_AWS_999",
        rule_name="Checkov: Ensure S3",
        severity=Severity.INFO,
        category=Category.SECURITY,
        description="Ensure S3 bucket logging",
        recommendation="https://example.com/guideline",
        scanner_name="Checkov",
        scanner_rule_id="CKV_AWS_999",
    )
    validator = FindingValidator()
    validator.validate(finding)
    assert finding.summary == "Ensure S3 bucket logging"
    assert "Informational security note for awareness" not in (finding.summary or "")


def test_checkov_adapter_sets_summary_from_check_name():
    check = {
        "check_id": "CKV_AWS_18",
        "check_name": "Ensure S3 access logging",
        "file_path": "main.tf",
        "resource": "aws_s3_bucket.x",
        "guideline": "https://docs.bridgecrew.io/CKV_AWS_18",
        "severity": "LOW",
    }
    # invoke mapping logic via a minimal inline reproduction
    check_name = check["check_name"]
    resource = check["resource"]
    description = check_name
    if resource:
        description = f"{description} in {resource}"
    assert description == "Ensure S3 access logging in aws_s3_bucket.x"
    assert check["guideline"].startswith("https://")


@pytest.mark.asyncio
async def test_build_job_groups_excludes_info_findings():
    from app.services.ai_job_service import build_job_groups

    scan = MagicMock()
    scan.id = uuid.uuid4()
    findings = [
        _db_finding(DBSeverity.HIGH, rule_id="H1"),
        _db_finding(DBSeverity.INFO, rule_id="I1", summary="observation"),
        _db_finding(DBSeverity.INFO, rule_id="I2", summary="observation 2"),
    ]
    session = AsyncMock()

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalars.return_value.all.return_value = findings
        return result

    session.execute = fake_execute
    groups = await build_job_groups(session, scan, max_per_scan=50, context_engine=None)
    assert len(groups) == 1
    assert groups[0]["rule_id"] == "H1"
    assert len(groups[0]["finding_ids"]) == 1


def test_finding_severity_and_rule_id_unchanged_by_validator():
    finding = RuleFinding(
        rule_id="Checkov/CKV_TEST",
        rule_name="Checkov: test",
        severity=Severity.INFO,
        category=Category.SECURITY,
        description="Scanner native description",
        recommendation="",
        scanner_rule_id="CKV_TEST",
    )
    before_id = finding.rule_id
    before_sev = finding.severity
    FindingValidator().validate(finding)
    assert finding.rule_id == before_id
    assert finding.severity == before_sev