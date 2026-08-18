"""Unit tests for pure functions in report-related service files."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from enum import Enum
from unittest.mock import MagicMock

import pytest

from app.services.report_generators import (
    _clean_sentence,
    _coerce_datetime,
    _coerce_int,
    _coerce_score,
    _determine_status,
    _derive_repository_name,
    _is_cicd_finding,
    _is_container_finding,
    _is_terraform_finding,
    _normalize_category_scores,
    _normalize_findings,
    _normalize_recommendations,
    _normalize_report_data,
    _normalize_severity,
    _normalize_summary,
    _score_assessment,
    _severity_rank,
    _truncate_text,
)
from app.services.report_service import (
    ReportService,
    build_download_expiry,
    count_findings_by_severity,
    derive_repository_name,
    normalize_report_format,
    severity_rank,
)
from app.services.report_storage import (
    PRESIGNED_URL_EXPIRY_SECONDS,
    ReportStorage,
)


# ── report_generators: _normalize_report_data ──────────────────────────


class TestNormalizeReportData:
    def test_minimal_input_produces_valid_output(self):
        result = _normalize_report_data({})
        assert result["user_id"] == "anonymous"
        assert result["scan_id"] == "unknown-scan"
        assert result["project_name"] == "Repository URL not provided"
        assert result["overall_score"] == 0.0
        assert result["status"] == "Critical"
        assert isinstance(result["findings"], list)
        assert isinstance(result["summary"], dict)

    def test_populated_scan_data_preserves_fields(self):
        scan_data = {
            "user_id": "u1",
            "scan_id": "s1",
            "project_name": "acme/web",
            "repository_url": "https://github.com/acme/web",
            "generated_at": "2026-01-15T10:00:00+00:00",
            "overall_score": 85.5,
            "findings": [],
            "summary": {"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        }
        result = _normalize_report_data(scan_data)
        assert result["user_id"] == "u1"
        assert result["scan_id"] == "s1"
        assert result["overall_score"] == 85.5
        assert result["overall_score_display"] == "85.5/100"

    def test_falls_back_to_repository_name_when_project_name_missing(self):
        scan_data = {"repository_name": "owner/repo"}
        result = _normalize_report_data(scan_data)
        assert result["project_name"] == "owner/repo"


# ── report_generators: _normalize_findings ─────────────────────────────


class TestNormalizeFindings:
    def test_empty_list(self):
        assert _normalize_findings([]) == []

    def test_sorts_by_severity_then_title(self):
        findings = [
            {"id": "F1", "severity": "low", "title": "Zebra"},
            {"id": "F2", "severity": "critical", "title": "Alpha"},
            {"id": "F3", "severity": "high", "title": "Middle"},
        ]
        result = _normalize_findings(findings)
        severities = [f["severity"] for f in result]
        assert severities == ["critical", "high", "low"]

    def test_missing_severity_defaults_to_info(self):
        findings = [{"id": "F1"}]
        result = _normalize_findings(findings)
        assert result[0]["severity"] == "info"

    def test_line_number_apended_to_location(self):
        findings = [{"id": "F1", "file_path": "main.py", "line_number": 42}]
        result = _normalize_findings(findings)
        assert result[0]["location"] == "main.py:42"

    def test_no_line_number_uses_file_path_only(self):
        findings = [{"id": "F1", "file_path": "main.py"}]
        result = _normalize_findings(findings)
        assert result[0]["location"] == "main.py"

    def test_missing_title_falls_back_to_rule_name(self):
        findings = [{"id": "F1", "rule_name": "My Rule"}]
        result = _normalize_findings(findings)
        assert result[0]["title"] == "My Rule"


# ── report_generators: _normalize_summary ──────────────────────────────


class TestNormalizeSummary:
    def test_none_summary_counts_from_findings(self):
        findings = [
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "high"},
        ]
        result = _normalize_summary(None, findings)
        assert result["critical"] == 1
        assert result["high"] == 2
        assert result["total_findings"] == 3

    def test_dict_summary_overrides_counts(self):
        summary = {"critical": 5, "high": 3, "total_findings": 10}
        result = _normalize_summary(summary, [])
        assert result["critical"] == 5
        assert result["high"] == 3
        assert result["total_findings"] == 10

    def test_total_issues_alias(self):
        summary = {"total_issues": 7}
        result = _normalize_summary(summary, [])
        assert result["total_findings"] == 7


# ── report_generators: _normalize_category_scores ──────────────────────


class TestNormalizeCategoryScores:
    def test_dict_input(self):
        scores = {"security": 80, "reliability": 90}
        result = _normalize_category_scores(scores)
        assert result["security"] == 80.0
        assert result["reliability"] == 90.0

    def test_list_input_with_category_key(self):
        scores = [{"category": "security", "score": 75}]
        result = _normalize_category_scores(scores)
        assert result["security"] == 75.0

    def test_performance_derived_from_scalability(self):
        scores = {"scalability": 80.0}
        result = _normalize_category_scores(scores)
        assert result["performance"] == 80.0

    def test_performance_derived_from_observability(self):
        scores = {"observability": 60.0}
        result = _normalize_category_scores(scores)
        assert result["performance"] == 60.0

    def test_performance_averages_scalability_and_observability(self):
        scores = {"scalability": 80.0, "observability": 60.0}
        result = _normalize_category_scores(scores)
        assert result["performance"] == 70.0

    def test_cost_alias(self):
        scores = {"cost": 55}
        result = _normalize_category_scores(scores)
        assert result["cost_optimization"] == 55.0

    def test_empty_input_defaults(self):
        result = _normalize_category_scores({})
        assert result["security"] == 0.0
        assert result["observability"] is None

    def test_non_numeric_score_coerced_to_zero(self):
        scores = {"security": "bad"}
        result = _normalize_category_scores(scores)
        assert result["security"] == 0.0


# ── report_generators: _normalize_recommendations ──────────────────────


class TestNormalizeRecommendations:
    def test_list_of_strings(self):
        recs = ["Fix A", "Fix B"]
        result = _normalize_recommendations(recs, [])
        assert result == ["Fix A", "Fix B"]

    def test_fallback_to_findings(self):
        findings = [{"recommendation": "Rec from finding"}]
        result = _normalize_recommendations(None, findings)
        assert result == ["Rec from finding"]

    def test_empty_findings_returns_default_message(self):
        result = _normalize_recommendations(None, [])
        assert result == ["No immediate remediation actions were identified."]

    def test_max_five_items(self):
        recs = [f"Rec {i}" for i in range(10)]
        result = _normalize_recommendations(recs, [])
        assert len(result) == 5

    def test_empty_strings_filtered(self):
        result = _normalize_recommendations(["", "  ", "Valid"], [])
        assert result == ["Valid"]


# ── report_generators: _coerce_datetime ────────────────────────────────


class TestCoerceDatetime:
    def test_iso_string(self):
        result = _coerce_datetime("2026-03-15T12:00:00+00:00")
        assert result.year == 2026
        assert result.month == 3
        assert result.tzinfo is not None

    def test_z_suffix(self):
        result = _coerce_datetime("2026-03-15T12:00:00Z")
        assert result.tzinfo is not None

    def test_naive_datetime_gets_utc(self):
        dt = datetime(2026, 1, 1, 12, 0, 0)
        result = _coerce_datetime(dt)
        assert result.tzinfo is not None

    def test_aware_datetime_preserved(self):
        dt = datetime(2026, 1, 1, tzinfo=UTC)
        result = _coerce_datetime(dt)
        assert result.year == 2026

    def test_none_returns_now(self):
        result = _coerce_datetime(None)
        assert result.tzinfo is not None

    def test_invalid_string_returns_now(self):
        result = _coerce_datetime("not-a-date")
        assert result.tzinfo is not None


# ── report_generators: _coerce_score ───────────────────────────────────


class TestCoerceScore:
    def test_float(self):
        assert _coerce_score(42.5) == 42.5

    def test_int(self):
        assert _coerce_score(100) == 100.0

    def test_none(self):
        assert _coerce_score(None) == 0.0

    def test_string_number(self):
        assert _coerce_score("75.5") == 75.5

    def test_invalid_string(self):
        assert _coerce_score("bad") == 0.0

    def test_clamps_above_100(self):
        assert _coerce_score(150) == 100.0

    def test_clamps_below_0(self):
        assert _coerce_score(-10) == 0.0


# ── report_generators: _coerce_int ─────────────────────────────────────


class TestCoerceInt:
    def test_int(self):
        assert _coerce_int(5) == 5

    def test_float(self):
        assert _coerce_int(3.7) == 3

    def test_string_number(self):
        assert _coerce_int("42") == 42

    def test_none(self):
        assert _coerce_int(None) == 0

    def test_invalid(self):
        assert _coerce_int("abc") == 0

    def test_negative_clamped(self):
        assert _coerce_int(-5) == 0


# ── report_generators: _truncate_text ──────────────────────────────────


class TestTruncateText:
    def test_short_text_not_truncated(self):
        assert _truncate_text("hello", 10) == "hello"

    def test_exact_length_not_truncated(self):
        assert _truncate_text("12345", 5) == "12345"

    def test_long_text_truncated(self):
        result = _truncate_text("abcdefghij", 7)
        assert result == "abcd..."

    def test_empty_string(self):
        assert _truncate_text("", 10) == ""

    def test_none_input(self):
        assert _truncate_text(None, 10) == ""


# ── report_generators: _clean_sentence ─────────────────────────────────


class TestCleanSentence:
    def test_strips_whitespace(self):
        assert _clean_sentence("  hello   world  ") == "hello world"

    def test_none_returns_not_provided(self):
        assert _clean_sentence(None) == "Not provided."

    def test_empty_string_returns_not_provided(self):
        assert _clean_sentence("") == "Not provided."

    def test_collapses_internal_whitespace(self):
        assert _clean_sentence("a\n\nb\tc") == "a b c"


# ── report_generators: _severity_rank ──────────────────────────────────


class TestSeverityRankGenerators:
    def test_critical_is_zero(self):
        assert _severity_rank("critical") == 0

    def test_high_is_one(self):
        assert _severity_rank("high") == 1

    def test_medium_is_two(self):
        assert _severity_rank("medium") == 2

    def test_low_is_three(self):
        assert _severity_rank("low") == 3

    def test_info_is_four(self):
        assert _severity_rank("info") == 4

    def test_unknown_is_five(self):
        assert _severity_rank("bogus") == 5


# ── report_generators: _normalize_severity ─────────────────────────────


class TestNormalizeSeverity:
    def test_lowercase_passthrough(self):
        assert _normalize_severity("critical") == "critical"

    def test_uppercase_normalized(self):
        assert _normalize_severity("HIGH") == "high"

    def test_invalid_defaults_to_info(self):
        assert _normalize_severity("bogus") == "info"

    def test_none_defaults_to_info(self):
        assert _normalize_severity(None) == "info"


# ── report_generators: _determine_status ───────────────────────────────


class TestDetermineStatus:
    def test_critical_findings(self):
        assert _determine_status(90, {"critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0}) == "Critical"

    def test_low_score(self):
        assert _determine_status(40, {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}) == "Critical"

    def test_high_findings_needs_attention(self):
        assert _determine_status(90, {"critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0}) == "Needs Attention"

    def test_medium_score_needs_attention(self):
        assert _determine_status(70, {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}) == "Needs Attention"

    def test_secure_when_clean(self):
        assert _determine_status(90, {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}) == "Secure"


# ── report_generators: _score_assessment ───────────────────────────────


class TestScoreAssessment:
    def test_strong(self):
        assert _score_assessment(95) == "Strong"

    def test_stable(self):
        assert _score_assessment(80) == "Stable"

    def test_watch(self):
        assert _score_assessment(65) == "Watch"

    def test_at_risk(self):
        assert _score_assessment(40) == "At Risk"


# ── report_generators: _derive_repository_name ─────────────────────────


class TestDeriveRepoNameGenerators:
    def test_standard_url(self):
        assert _derive_repository_name("https://github.com/acme/web") == "acme/web"

    def test_strips_git_suffix(self):
        assert _derive_repository_name("https://github.com/acme/web.git") == "acme/web"

    def test_trailing_slash(self):
        assert _derive_repository_name("https://github.com/acme/web/") == "acme/web"

    def test_short_url(self):
        assert _derive_repository_name("only-one-segment") == "only-one-segment"


# ── report_generators: _is_terraform_finding ───────────────────────────


class TestIsTerraformFinding:
    def test_tf_extension(self):
        assert _is_terraform_finding({"file_path": "main.tf", "title": "SG"}) is True

    def test_tfvars_extension(self):
        assert _is_terraform_finding({"file_path": "vars.tfvars", "title": "SG"}) is True

    def test_terraform_in_path(self):
        assert _is_terraform_finding({"file_path": "terraform/main.tf", "title": "SG"}) is True

    def test_terraform_in_title(self):
        assert _is_terraform_finding({"file_path": "main.py", "title": "Terraform issue"}) is True

    def test_non_terraform(self):
        assert _is_terraform_finding({"file_path": "app.py", "title": "Bug"}) is False


# ── report_generators: _is_cicd_finding ────────────────────────────────


class TestIsCicdFinding:
    def test_github_workflow(self):
        assert _is_cicd_finding({"file_path": ".github/workflows/ci.yml", "title": "CI"}) is True

    def test_gitlab_ci(self):
        assert _is_cicd_finding({"file_path": ".gitlab-ci.yml", "title": "CI"}) is True

    def test_jenkinsfile(self):
        assert _is_cicd_finding({"file_path": "Jenkinsfile", "title": "Pipeline"}) is True

    def test_pipeline_in_title(self):
        assert _is_cicd_finding({"file_path": "config.yaml", "title": "pipeline setup"}) is True

    def test_non_cicd(self):
        assert _is_cicd_finding({"file_path": "app.py", "title": "Bug"}) is False


# ── report_generators: _is_container_finding ───────────────────────────


class TestIsContainerFinding:
    def test_dockerfile(self):
        assert _is_container_finding({"file_path": "Dockerfile", "title": "Root user"}) is True

    def test_kubernetes_in_path(self):
        assert _is_container_finding({"file_path": "k8s/deploy.yaml", "title": "Missing limits"}) is True

    def test_helm_in_title(self):
        assert _is_container_finding({"file_path": "config.yaml", "title": "Helm chart issue"}) is True

    def test_container_in_title(self):
        assert _is_container_finding({"file_path": "app.py", "title": "container resource"}) is True

    def test_non_container(self):
        assert _is_container_finding({"file_path": "main.py", "title": "Bug"}) is False


# ── report_service: normalize_report_format ────────────────────────────


class TestNormalizeReportFormat:
    def test_pdf(self):
        assert normalize_report_format("pdf") == "pdf"

    def test_pdf_uppercase(self):
        assert normalize_report_format("PDF") == "pdf"

    def test_xlsx(self):
        assert normalize_report_format("xlsx") == "excel"

    def test_excel(self):
        assert normalize_report_format("excel") == "excel"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid format"):
            normalize_report_format("csv")


# ── report_service: derive_repository_name ─────────────────────────────


class TestDeriveRepoNameService:
    def test_standard_url(self):
        assert derive_repository_name("https://github.com/acme/web") == "acme/web"

    def test_strips_git_suffix(self):
        assert derive_repository_name("https://github.com/acme/web.git") == "acme/web"

    def test_trailing_slash(self):
        assert derive_repository_name("https://github.com/acme/web/") == "acme/web"

    def test_short_url(self):
        assert derive_repository_name("single") == "single"


# ── report_service: count_findings_by_severity ─────────────────────────


class TestCountFindingsBySeverity:
    def _make_finding(self, severity):
        f = MagicMock()
        f.severity = severity
        return f

    def test_mixed_severities(self):
        findings = [
            self._make_finding("critical"),
            self._make_finding("high"),
            self._make_finding("high"),
            self._make_finding("low"),
        ]
        counts = count_findings_by_severity(findings)
        assert counts == {"critical": 1, "high": 2, "medium": 0, "low": 1, "info": 0}

    def test_enum_severity(self):
        class Sev(Enum):
            HIGH = "high"

        f = MagicMock()
        f.severity = Sev.HIGH
        counts = count_findings_by_severity([f])
        assert counts["high"] == 1

    def test_invalid_severity_goes_to_info(self):
        f = MagicMock()
        f.severity = "bogus"
        counts = count_findings_by_severity([f])
        assert counts["info"] == 1


# ── report_service: severity_rank ──────────────────────────────────────


class TestSeverityRankService:
    def test_all_ranks(self):
        assert severity_rank("critical") == 0
        assert severity_rank("high") == 1
        assert severity_rank("medium") == 2
        assert severity_rank("low") == 3
        assert severity_rank("info") == 4
        assert severity_rank("unknown") == 5


# ── report_service: build_download_expiry ──────────────────────────────


class TestBuildDownloadExpiry:
    def test_returns_future_datetime(self):
        result = build_download_expiry()
        now = datetime.now(UTC)
        assert result > now

    def test_offset_matches_expiry_seconds(self):
        result = build_download_expiry()
        now = datetime.now(UTC)
        expected = now + timedelta(seconds=PRESIGNED_URL_EXPIRY_SECONDS)
        assert abs((result - expected).total_seconds()) < 2


# ── report_service: ReportService instance methods ─────────────────────


class TestReportServiceInstanceMethods:
    def _svc(self):
        return ReportService(storage=MagicMock(spec=ReportStorage))

    def test_normalize_enum_value_with_enum(self):
        class Color(Enum):
            RED = "red"

        svc = self._svc()
        assert svc._normalize_enum_value(Color.RED) == "red"

    def test_normalize_enum_value_with_string(self):
        svc = self._svc()
        assert svc._normalize_enum_value("hello") == "hello"

    def test_parse_best_practices_none(self):
        assert self._svc()._parse_best_practices(None) == []

    def test_parse_best_practices_list(self):
        assert self._svc()._parse_best_practices(["a", "b"]) == ["a", "b"]

    def test_parse_best_practices_json_string(self):
        result = self._svc()._parse_best_practices(json.dumps(["x", "y"]))
        assert result == ["x", "y"]

    def test_parse_best_practices_plain_string(self):
        assert self._svc()._parse_best_practices("just text") == ["just text"]

    def test_string_or_none_none(self):
        assert self._svc()._string_or_none(None) is None

    def test_string_or_none_string(self):
        assert self._svc()._string_or_none("hello") == "hello"


# ── report_storage: build_object_key ───────────────────────────────────


class TestBuildObjectKey:
    def _storage(self):
        return ReportStorage(s3_client=MagicMock())

    def test_with_user_id(self):
        s = self._storage()
        key = s.build_object_key(user_id="u1", scan_id="s1", format="pdf")
        assert key == "reports/u1/s1/report.pdf"

    def test_without_user_id(self):
        s = self._storage()
        key = s.build_object_key(user_id=None, scan_id="s1", format="pdf")
        assert key == "reports/anonymous/s1/report.pdf"

    def test_excel_format(self):
        s = self._storage()
        key = s.build_object_key(user_id="u1", scan_id="s1", format="excel")
        assert key == "reports/u1/s1/report.xlsx"


# ── report_storage: upload_bytes ───────────────────────────────────────


class TestUploadBytes:
    def test_calls_put_object(self):
        mock_client = MagicMock()
        s = ReportStorage(s3_client=mock_client)
        s.upload_bytes(content=b"data", key="k1", content_type="application/pdf", metadata={"m": "v"})
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == s.bucket_name
        assert call_kwargs["Key"] == "k1"
        assert call_kwargs["Body"] == b"data"
        assert call_kwargs["ServerSideEncryption"] == "AES256"


# ── report_storage: generate_presigned_download_url ────────────────────


class TestPresignedDownloadUrl:
    def test_returns_url(self):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://s3.example.com/presigned"
        s = ReportStorage(s3_client=mock_client)
        url = s.generate_presigned_download_url(key="k1", filename="report.pdf")
        assert url == "https://s3.example.com/presigned"
        mock_client.generate_presigned_url.assert_called_once()
