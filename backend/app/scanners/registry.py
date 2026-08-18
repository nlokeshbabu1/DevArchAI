"""
Scanner Registry — discovers available scanner adapters and provides
a unified interface for running them with full execution tracking.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.scanners.models import ApplicabilityInfo, ScannerExecutionResult, ScannerStatus
from app.scanners.technology_detector import get_scanner_applicability

logger = logging.getLogger(__name__)


class ScannerRegistry:
    """Registry of all available scanner adapters with execution tracking."""

    def __init__(self) -> None:
        self._adapters: dict[str, BaseScannerAdapter] = {}
        self._register_adapters()

    def _register_adapters(self) -> None:
        adapters_to_try: list[tuple[str, type]] = [
            ("hadolint", self._import_adapter("app.scanners.adapters.hadolint_adapter", "HadolintAdapter")),
            ("gitleaks", self._import_adapter("app.scanners.adapters.gitleaks_adapter", "GitleaksAdapter")),
            ("npm_audit", self._import_adapter("app.scanners.adapters.npm_audit_adapter", "NpmAuditAdapter")),
            ("pip_audit", self._import_adapter("app.scanners.adapters.pip_audit_adapter", "PipAuditAdapter")),
            ("govulncheck", self._import_adapter("app.scanners.adapters.govulncheck_adapter", "GovulncheckAdapter")),
            ("dependency_check", self._import_adapter("app.scanners.adapters.dependency_check_adapter", "DependencyCheckAdapter")),
            ("checkov", self._import_adapter("app.scanners.adapters.checkov_adapter", "CheckovAdapter")),
            ("tfsec", self._import_adapter("app.scanners.adapters.tfsec_adapter", "TfsecAdapter")),
            ("kube_score", self._import_adapter("app.scanners.adapters.kube_score_adapter", "KubeScoreAdapter")),
            ("trivy_filesystem", self._import_adapter("app.scanners.adapters.trivy_adapter", "TrivyFilesystemAdapter")),
            ("trivy_config", self._import_adapter("app.scanners.adapters.trivy_adapter", "TrivyConfigAdapter")),
        ]

        for scanner_id, adapter_cls in adapters_to_try:
            if adapter_cls is None:
                continue
            try:
                instance = adapter_cls()
                self._adapters[scanner_id] = instance
            except Exception as exc:
                logger.debug("Failed to instantiate scanner %s: %s", scanner_id, exc)

    def _import_adapter(self, module_path: str, class_name: str) -> type | None:
        try:
            import importlib
            module = importlib.import_module(module_path)
            return getattr(module, class_name, None)
        except Exception:
            return None

    def get(self, scanner_id: str) -> BaseScannerAdapter | None:
        return self._adapters.get(scanner_id)

    def get_all_adapter_ids(self) -> list[str]:
        return list(self._adapters.keys())

    def get_available(self) -> list[BaseScannerAdapter]:
        return [a for a in self._adapters.values() if a.is_available()]

    def get_available_ids(self) -> list[str]:
        return [aid for aid, a in self._adapters.items() if a.is_available()]

    def _build_result(
        self,
        scanner_id: str,
        adapter: BaseScannerAdapter | None,
        status: ScannerStatus,
        applicable: bool = True,
        findings: list[Any] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        skipped_reason: str | None = None,
        error_message: str | None = None,
    ) -> ScannerExecutionResult:
        duration_ms = None
        if start and end:
            duration_ms = int((end - start).total_seconds() * 1000)

        return ScannerExecutionResult(
            scanner_name=adapter.name if adapter else scanner_id,
            scanner_id=scanner_id,
            status=status,
            applicable=applicable,
            enabled=adapter is not None,
            version=adapter.get_version() if adapter else None,
            execution_start=start,
            execution_end=end,
            duration_ms=duration_ms,
            files_scanned=adapter.get_files_scanned_count() if adapter else None,
            rules_executed=adapter.get_rules_count() if adapter else None,
            findings_count=len(findings) if findings else 0,
            skipped_reason=skipped_reason,
            error_message=error_message,
            findings=findings or [],
        )

    def run_scanners(
        self,
        scanner_ids: list[str],
        repo_path: Path,
        detection: dict[str, Any],
    ) -> list[ScannerExecutionResult]:
        """Run specified scanners and return execution results with metadata.

        Unavailable scanners are recorded as DISABLED.
        Failed scanners are recorded as FAILED with error_message.
        """
        results: list[ScannerExecutionResult] = []
        for sid in scanner_ids:
            adapter = self.get(sid)
            if adapter is None or not adapter.is_available():
                results.append(self._build_result(
                    sid, adapter,
                    ScannerStatus.UNAVAILABLE,
                    applicable=True,
                    skipped_reason=f"CLI tool not installed. {adapter.get_install_hint() if adapter else ''}",
                ))
                continue

            start = datetime.now(UTC)
            try:
                findings = adapter.scan(repo_path, detection)
                end = datetime.now(UTC)
                status = (
                    ScannerStatus.COMPLETED_WITH_FINDINGS if findings
                    else ScannerStatus.COMPLETED_NO_FINDINGS
                )
                results.append(self._build_result(
                    sid, adapter, status,
                    applicable=True,
                    findings=findings,
                    start=start, end=end,
                ))
                logger.info("Scanner %s completed: %d findings", sid, len(findings))
            except Exception as exc:
                end = datetime.now(UTC)
                logger.warning("Scanner %s failed: %s", sid, exc)
                results.append(self._build_result(
                    sid, adapter,
                    ScannerStatus.FAILED,
                    applicable=True,
                    start=start, end=end,
                    error_message=str(exc),
                ))
        return results

    def run_for_repo(
        self,
        repo_path: Path,
        detected_stack: dict[str, Any] | None,
    ) -> list[ScannerExecutionResult]:
        """Auto-detect which scanners to run, including skipped/non-applicable.

        Returns execution results for ALL registered scanners, not just those
        that ran. Skipped and non-applicable scanners are included with
        appropriate status and reason.
        """
        if detected_stack is None:
            detected_stack = {}

        applicability = get_scanner_applicability(repo_path, detected_stack)

        # Build result for every registered scanner
        results: list[ScannerExecutionResult] = []
        for sid in sorted(self._adapters.keys()):
            adapter = self.get(sid)
            app_info = applicability.get(sid, ApplicabilityInfo(applicable=False, reason="Unknown scanner."))

            if not app_info.applicable:
                # Record as SKIPPED_NOT_APPLICABLE
                results.append(self._build_result(
                    sid, adapter,
                    ScannerStatus.SKIPPED_NOT_APPLICABLE,
                    applicable=False,
                    skipped_reason=app_info.reason,
                ))
                continue

            # Check CLI availability
            if adapter is None or not adapter.is_available():
                results.append(self._build_result(
                    sid, adapter,
                    ScannerStatus.UNAVAILABLE,
                    applicable=True,
                    skipped_reason=f"CLI tool not installed. {adapter.get_install_hint() if adapter else ''}",
                ))
                continue

            # Run the scanner
            start = datetime.now(UTC)
            try:
                findings = adapter.scan(repo_path, detected_stack)
                end = datetime.now(UTC)
                status = (
                    ScannerStatus.COMPLETED_WITH_FINDINGS if findings
                    else ScannerStatus.COMPLETED_NO_FINDINGS
                )
                results.append(self._build_result(
                    sid, adapter, status,
                    applicable=True,
                    findings=findings,
                    start=start, end=end,
                ))
                logger.info("Scanner %s completed: %d findings", sid, len(findings))
            except Exception as exc:
                end = datetime.now(UTC)
                logger.warning("Scanner %s failed: %s", sid, exc)
                results.append(self._build_result(
                    sid, adapter,
                    ScannerStatus.FAILED,
                    applicable=True,
                    start=start, end=end,
                    error_message=str(exc),
                ))

        return results


def get_scanner_registry() -> ScannerRegistry:
    return ScannerRegistry()


from app.scanners.adapters.base import BaseScannerAdapter  # noqa: E402, F401
