"""Report orchestration for persistence, artifact generation, and downloads."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.scan import Scan
from app.services.report_generators import generate_excel_report, generate_pdf_report
from app.services.report_storage import (
    EXCEL_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    PRESIGNED_URL_EXPIRY_SECONDS,
    ReportStorage,
)

logger = structlog.get_logger(__name__)

SUPPORTED_REPORT_FORMATS = {"pdf", "excel", "xlsx"}


class ReportService:
    """Create report records, upload artifacts, and issue download URLs."""

    def __init__(self, storage: ReportStorage | None = None) -> None:
        self.storage = storage or ReportStorage()

    async def upsert_report_record_async(
        self,
        *,
        db: AsyncSession,
        scan: Scan,
        findings: Sequence[Any],
        scores: Any,
        files_analyzed: Sequence[str],
        executive_summary: str | None = None,
        risk_analysis: str | None = None,
        prioritized_recommendations: Sequence[str] | None = None,
    ) -> Report:
        result = await db.execute(select(Report).where(Report.scan_id == scan.id))
        report = result.scalar_one_or_none() or Report(scan_id=scan.id)
        self._populate_report_record(
            report=report,
            scan=scan,
            findings=findings,
            scores=scores,
            files_analyzed=files_analyzed,
            executive_summary=executive_summary,
            risk_analysis=risk_analysis,
            prioritized_recommendations=prioritized_recommendations,
        )
        db.add(report)
        await db.flush()
        return report

    def upsert_report_record_sync(
        self,
        *,
        db: Session,
        scan: Scan,
        findings: Sequence[Any],
        scores: Any,
        files_analyzed: Sequence[str],
        executive_summary: str | None = None,
        risk_analysis: str | None = None,
        prioritized_recommendations: Sequence[str] | None = None,
    ) -> Report:
        report = db.execute(select(Report).where(Report.scan_id == scan.id)).scalar_one_or_none()
        report = report or Report(scan_id=scan.id)
        self._populate_report_record(
            report=report,
            scan=scan,
            findings=findings,
            scores=scores,
            files_analyzed=files_analyzed,
            executive_summary=executive_summary,
            risk_analysis=risk_analysis,
            prioritized_recommendations=prioritized_recommendations,
        )
        db.add(report)
        db.flush()
        return report

    def generate_and_store_artifacts(
        self,
        *,
        scan: Scan,
        report: Report,
        findings: Sequence[Any],
    ) -> Report:
        payload = self.build_report_payload(scan=scan, report=report, findings=findings)
        metadata = {
            "scan_id": str(scan.id),
            "report_id": str(report.id),
            "repository_name": report.repository_name,
        }

        pdf_key = self.storage.build_object_key(
            user_id=str(scan.user_id) if scan.user_id else None,
            scan_id=str(scan.id),
            format="pdf",
        )
        excel_key = self.storage.build_object_key(
            user_id=str(scan.user_id) if scan.user_id else None,
            scan_id=str(scan.id),
            format="excel",
        )

        pdf_file_path = generate_pdf_report(payload)

        self.storage.upload_file(
            file_path=pdf_file_path,
            key=pdf_key,
            content_type=PDF_CONTENT_TYPE,
            metadata=metadata,
        )
        self.storage.upload_bytes(
            content=generate_excel_report(payload),
            key=excel_key,
            content_type=EXCEL_CONTENT_TYPE,
            metadata=metadata,
        )

        report.s3_key = pdf_key
        report.pdf_s3_key = pdf_key
        report.excel_s3_key = excel_key
        return report

    def generate_download_url(self, *, report: Report, scan: Scan, format: str) -> str:
        normalized_format = normalize_report_format(format)
        key = report.pdf_s3_key if normalized_format == "pdf" else report.excel_s3_key
        if not key:
            raise ValueError(f"{normalized_format} report not found")

        return self.storage.generate_presigned_download_url(
            key=key,
            filename=self.build_download_filename(scan=scan, format=normalized_format),
            expires_in=PRESIGNED_URL_EXPIRY_SECONDS,
        )

    def build_report_payload(
        self,
        *,
        scan: Scan,
        report: Report,
        findings: Sequence[Any],
    ) -> dict[str, Any]:
        generated_at = report.created_at or datetime.now(UTC)
        serialized_findings = [self._serialize_finding(finding) for finding in findings]
        recommendations = report.prioritized_recommendations or self._default_recommendations(findings)

        return {
            "report_id": str(report.id),
            "scan_id": str(scan.id),
            "user_id": str(scan.user_id) if scan.user_id else "anonymous",
            "project_name": report.repository_name,
            "repository_name": report.repository_name,
            "repository_url": report.repository_url,
            "branch": scan.branch,
            "commit_hash": report.commit_hash,
            "generated_at": generated_at.isoformat(),
            "overall_score": report.overall_score,
            "category_scores": report.category_scores or {},
            "detected_stack": scan.detected_stack or {},
            "executive_summary": report.executive_summary or self._default_executive_summary(report),
            "risk_analysis": report.risk_analysis or self._default_risk_analysis(report),
            "prioritized_recommendations": recommendations,
            "files_analyzed": report.files_analyzed or [],
            "summary": {
                "total_findings": report.total_findings,
                "critical": report.critical_count,
                "high": report.high_count,
                "medium": report.medium_count,
                "low": report.low_count,
                "info": report.info_count,
            },
            "findings": serialized_findings,
        }

    def build_download_filename(self, *, scan: Scan, format: str) -> str:
        extension = "pdf" if format == "pdf" else "xlsx"
        repository_name = derive_repository_name(scan.repository_url).replace("/", "-")
        return f"{repository_name}-{scan.id}.{extension}"

    def _populate_report_record(
        self,
        *,
        report: Report,
        scan: Scan,
        findings: Sequence[Any],
        scores: Any,
        files_analyzed: Sequence[str],
        executive_summary: str | None,
        risk_analysis: str | None,
        prioritized_recommendations: Sequence[str] | None,
    ) -> None:
        severity_counts = count_findings_by_severity(findings)

        report.repository_name = derive_repository_name(scan.repository_url)
        report.repository_url = scan.repository_url
        report.commit_hash = scan.commit_hash
        report.overall_score = float(getattr(scores, "score", 0) or 0)
        report.category_scores = {
            self._normalize_enum_value(category_score.category): float(category_score.score)
            for category_score in getattr(scores, "category_scores", [])
        }
        report.executive_summary = executive_summary or self._default_executive_summary_from_counts(
            report.repository_name,
            severity_counts,
        )
        report.risk_analysis = risk_analysis or self._build_risk_analysis(severity_counts)
        report.prioritized_recommendations = list(
            prioritized_recommendations or self._default_recommendations(findings)
        )
        report.total_findings = len(findings)
        report.critical_count = severity_counts["critical"]
        report.high_count = severity_counts["high"]
        report.medium_count = severity_counts["medium"]
        report.low_count = severity_counts["low"]
        report.info_count = severity_counts["info"]
        report.files_analyzed = [str(file_path) for file_path in files_analyzed]

    def _serialize_finding(self, finding: Any) -> dict[str, Any]:
        return {
            "rule_id": str(getattr(finding, "rule_id", "")),
            "rule_name": str(getattr(finding, "rule_name", "")),
            "severity": self._normalize_enum_value(getattr(finding, "severity", "")),
            "category": self._normalize_enum_value(getattr(finding, "category", "")),
            "description": str(getattr(finding, "description", "")),
            "recommendation": str(getattr(finding, "recommendation", "")),
            "file_path": getattr(finding, "file_path", None),
            "line_number": getattr(finding, "line_number", None),
            "summary": self._string_or_none(getattr(finding, "summary", None)),
            "risk": self._string_or_none(getattr(finding, "risk", None)),
            "impact": self._string_or_none(getattr(finding, "impact", None)),
            "best_practices": self._parse_best_practices(getattr(finding, "best_practices", None)),
            "scanner_name": getattr(finding, "scanner_name", None),
            "scanner_rule_id": getattr(finding, "scanner_rule_id", None),
            "package": getattr(finding, "package", None),
            "installed_version": getattr(finding, "installed_version", None),
            "fixed_version": getattr(finding, "fixed_version", None),
            "cve": getattr(finding, "cve", None),
            "cwe": getattr(finding, "cwe", None),
            "references": getattr(finding, "references", None),
            "evidence": getattr(finding, "evidence", None),
        }

    def _default_recommendations(self, findings: Sequence[Any]) -> list[str]:
        recommendations: list[str] = []
        for finding in sorted(
            findings,
            key=lambda item: severity_rank(self._normalize_enum_value(getattr(item, "severity", "info"))),
        ):
            recommendation = self._string_or_none(getattr(finding, "recommendation", None))
            if recommendation and recommendation not in recommendations:
                recommendations.append(recommendation)
            if len(recommendations) == 5:
                break
        return recommendations

    def _default_executive_summary(self, report: Report) -> str:
        return self._default_executive_summary_from_counts(
            report.repository_name,
            {
                "critical": report.critical_count,
                "high": report.high_count,
                "medium": report.medium_count,
                "low": report.low_count,
                "info": report.info_count,
            },
        )

    def _default_executive_summary_from_counts(
        self,
        repository_name: str,
        severity_counts: dict[str, int],
    ) -> str:
        total_findings = sum(severity_counts.values())
        return (
            f"{repository_name} completed with {total_findings} findings: "
            f"{severity_counts['critical']} critical, {severity_counts['high']} high, "
            f"{severity_counts['medium']} medium, {severity_counts['low']} low."
        )

    def _default_risk_analysis(self, report: Report) -> str:
        return self._build_risk_analysis(
            {
                "critical": report.critical_count,
                "high": report.high_count,
                "medium": report.medium_count,
                "low": report.low_count,
                "info": report.info_count,
            }
        )

    def _build_risk_analysis(self, severity_counts: dict[str, int]) -> str:
        if severity_counts["critical"] > 0:
            return "Critical issues were detected. Remediate those items before production deployment."
        if severity_counts["high"] > 0:
            return "High-risk issues remain. Prioritize remediation before broad rollout."
        if severity_counts["medium"] > 0:
            return "No blocking issues were found, but medium-risk findings should be scheduled for remediation."
        return "No material risk signals were detected in this scan."

    def _normalize_enum_value(self, value: Any) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    def _parse_best_practices(self, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                return [value]
        return [str(value)]

    def _string_or_none(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)


def normalize_report_format(format: str) -> str:
    """Normalize accepted download formats to report artifact types."""
    normalized = format.lower().strip()
    if normalized == "xlsx":
        return "excel"
    if normalized not in SUPPORTED_REPORT_FORMATS:
        raise ValueError("Invalid format. Use 'pdf' or 'excel'.")
    return normalized


def derive_repository_name(repository_url: str) -> str:
    """Return owner/repo when possible for user-facing report labels."""
    clean_url = repository_url.rstrip("/")
    parts = clean_url.split("/")
    if len(parts) >= 2:
        return "/".join(parts[-2:]).replace(".git", "")
    return clean_url.replace(".git", "")


def count_findings_by_severity(findings: Sequence[Any]) -> dict[str, int]:
    """Count findings by normalized severity."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for finding in findings:
        severity = getattr(finding, "severity", "info")
        if hasattr(severity, "value"):
            severity = severity.value
        severity = str(severity).lower()
        counts[severity if severity in counts else "info"] += 1
    return counts


def severity_rank(severity: str) -> int:
    """Sort higher-severity findings first."""
    return {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(severity, 5)


def build_download_expiry() -> datetime:
    """Return the absolute expiry timestamp for a presigned report URL."""
    return datetime.now(UTC) + timedelta(seconds=PRESIGNED_URL_EXPIRY_SECONDS)
