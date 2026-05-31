"""Unit tests for report generation and storage helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.report import Report
from app.models.scan import Scan
from app.services import report_generators
from app.services.report_generators import EXAMPLE_SCAN_DATA, generate_pdf_report
from app.services.report_service import ReportService, normalize_report_format
from app.services.report_storage import ReportStorage


class DummyS3Client:
    """Simple S3 client stub for upload and presign assertions."""

    def __init__(self) -> None:
        self.put_calls: list[dict] = []
        self.presign_calls: list[dict] = []

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)

    def generate_presigned_url(self, **kwargs):
        self.presign_calls.append(kwargs)
        return "https://example.com/report-download"


def test_normalize_report_format_accepts_excel_alias():
    assert normalize_report_format("pdf") == "pdf"
    assert normalize_report_format("excel") == "excel"
    assert normalize_report_format("xlsx") == "excel"


def test_report_artifacts_upload_to_expected_private_s3_keys():
    s3_client = DummyS3Client()
    storage = ReportStorage(bucket_name="devarchai-reports", region_name="us-east-1", s3_client=s3_client)
    service = ReportService(storage=storage)

    scan = Scan(
        id=uuid4(),
        user_id=uuid4(),
        repository_url="https://github.com/acme/platform.git",
        branch="main",
    )
    report = Report(
        id=uuid4(),
        scan_id=scan.id,
        repository_name="acme/platform",
        repository_url=scan.repository_url,
        overall_score=88.5,
        total_findings=2,
        critical_count=1,
        high_count=1,
        medium_count=0,
        low_count=0,
        info_count=0,
        files_analyzed=["Dockerfile", "terraform/main.tf"],
        created_at=datetime.now(UTC),
    )
    findings = [
        SimpleNamespace(
            rule_id="SEC-001",
            rule_name="Public bucket",
            severity="critical",
            category="security",
            description="Bucket is public",
            recommendation="Disable public access",
            file_path="terraform/main.tf",
            line_number=12,
        ),
        SimpleNamespace(
            rule_id="REL-001",
            rule_name="Missing healthcheck",
            severity="high",
            category="reliability",
            description="Container has no healthcheck",
            recommendation="Add HEALTHCHECK",
            file_path="Dockerfile",
            line_number=8,
        ),
    ]

    service.generate_and_store_artifacts(scan=scan, report=report, findings=findings)

    assert report.pdf_s3_key == f"reports/{scan.user_id}/{scan.id}/report.pdf"
    assert report.excel_s3_key == f"reports/{scan.user_id}/{scan.id}/report.xlsx"
    assert report.s3_key == report.pdf_s3_key
    assert len(s3_client.put_calls) == 2
    assert s3_client.put_calls[0]["ServerSideEncryption"] == "AES256"
    assert s3_client.put_calls[0]["ContentType"] == "application/pdf"
    assert s3_client.put_calls[0]["Body"].startswith(b"%PDF")
    assert s3_client.put_calls[1]["ContentType"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert s3_client.put_calls[1]["Body"].startswith(b"PK")


def test_generate_download_url_uses_presigned_s3_response_content_disposition():
    s3_client = DummyS3Client()
    storage = ReportStorage(bucket_name="devarchai-reports", region_name="us-east-1", s3_client=s3_client)
    service = ReportService(storage=storage)

    scan = Scan(
        id=uuid4(),
        user_id=uuid4(),
        repository_url="https://github.com/acme/platform.git",
        branch="main",
    )
    report = Report(
        id=uuid4(),
        scan_id=scan.id,
        repository_name="acme/platform",
        repository_url=scan.repository_url,
        overall_score=75.0,
        total_findings=0,
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        info_count=0,
        pdf_s3_key=f"reports/{scan.user_id}/{scan.id}/report.pdf",
        excel_s3_key=f"reports/{scan.user_id}/{scan.id}/report.xlsx",
    )

    download_url = service.generate_download_url(report=report, scan=scan, format="xlsx")

    assert download_url == "https://example.com/report-download"
    assert s3_client.presign_calls[0]["ClientMethod"] == "get_object"
    assert s3_client.presign_calls[0]["Params"]["Key"] == report.excel_s3_key
    assert s3_client.presign_calls[0]["Params"]["ResponseContentDisposition"].endswith(".xlsx\"")


def test_generate_pdf_report_creates_local_enterprise_pdf(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr(report_generators.settings, "TEMP_DIR", str(tmp_path))

    file_path = generate_pdf_report(EXAMPLE_SCAN_DATA)

    assert file_path.endswith("/report.pdf")
    pdf_path = tmp_path / "reports" / EXAMPLE_SCAN_DATA["user_id"] / EXAMPLE_SCAN_DATA["scan_id"] / "report.pdf"
    assert file_path == str(pdf_path)
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_generate_pdf_report_handles_missing_fields(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr(report_generators.settings, "TEMP_DIR", str(tmp_path))

    file_path = generate_pdf_report({"scan_id": "scan-123", "findings": []})

    pdf_path = tmp_path / "reports" / "anonymous" / "scan-123" / "report.pdf"
    assert file_path == str(pdf_path)
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_report_storage_uses_explicit_settings_credentials(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class FakeSession:
        def __init__(self, **kwargs):
            captured["session_kwargs"] = kwargs

        def client(self, service_name: str, config=None):
            captured["service_name"] = service_name
            captured["config"] = config
            return DummyS3Client()

    monkeypatch.setattr("app.services.report_storage.boto3.session.Session", FakeSession)

    ReportStorage(
        bucket_name="devarchai-reports",
        region_name="ap-south-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        aws_session_token="test-token",
    )

    assert captured["service_name"] == "s3"
    assert captured["session_kwargs"] == {
        "region_name": "ap-south-1",
        "aws_access_key_id": "test-key",
        "aws_secret_access_key": "test-secret",
        "aws_session_token": "test-token",
    }
