"""Comprehensive tests for the Scanner Execution Framework.

Validates:
  - ScannerStatus enum values
  - ScannerExecutionResult dataclass
  - ApplicabilityInfo detection
  - technology_detector applicability for all scanners
  - ScannerRegistry execution tracking (timing, status, errors)
  - Serialization to dict
  - End-to-end: applicable → run → results
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.scanners.models import (
    ApplicabilityInfo,
    ScannerExecutionResult,
    ScannerStatus,
)
from app.scanners.technology_detector import (
    get_scanner_applicability,
    get_scanners_for_stack,
    get_skipped_scanners,
)


class TestScannerStatus:
    """ScannerStatus enum must have all required states."""

    def test_all_statuses_defined(self):
        assert ScannerStatus.DISCOVERED.value == "DISCOVERED"
        assert ScannerStatus.INITIALIZING.value == "INITIALIZING"
        assert ScannerStatus.RUNNING.value == "RUNNING"
        assert ScannerStatus.COMPLETED.value == "COMPLETED"
        assert ScannerStatus.COMPLETED_WITH_FINDINGS.value == "COMPLETED_WITH_FINDINGS"
        assert ScannerStatus.COMPLETED_NO_FINDINGS.value == "COMPLETED_NO_FINDINGS"
        assert ScannerStatus.SKIPPED_NOT_APPLICABLE.value == "SKIPPED_NOT_APPLICABLE"
        assert ScannerStatus.DISABLED.value == "DISABLED"
        assert ScannerStatus.FAILED.value == "FAILED"

    def test_all_statuses_in_enum(self):
        expected = {
            "DISCOVERED", "INITIALIZING", "RUNNING", "COMPLETED",
            "COMPLETED_WITH_FINDINGS", "COMPLETED_NO_FINDINGS",
            "SKIPPED_NOT_APPLICABLE", "DISABLED", "FAILED", "UNAVAILABLE",
        }
        actual = {s.name for s in ScannerStatus}
        assert actual == expected


class TestApplicabilityInfo:
    """ApplicabilityInfo must carry both boolean and reason."""

    def test_applicable(self):
        info = ApplicabilityInfo(applicable=True)
        assert info.applicable is True
        assert info.reason == ""

    def test_not_applicable_with_reason(self):
        info = ApplicabilityInfo(applicable=False, reason="No Kubernetes manifests detected.")
        assert info.applicable is False
        assert info.reason == "No Kubernetes manifests detected."

    def test_default_reason(self):
        info = ApplicabilityInfo(applicable=False)
        assert info.reason == ""


class TestScannerExecutionResult:
    """ScannerExecutionResult must track all execution metadata."""

    def test_minimal_result(self):
        result = ScannerExecutionResult(
            scanner_name="TestScanner",
            scanner_id="test_scanner",
            status=ScannerStatus.DISCOVERED,
        )
        assert result.scanner_name == "TestScanner"
        assert result.scanner_id == "test_scanner"
        assert result.status == ScannerStatus.DISCOVERED
        assert result.findings_count == 0
        assert result.findings == []

    def test_with_findings(self):
        from app.rule_engine.base import Category, RuleFinding, Severity

        findings = [
            RuleFinding(rule_id="TEST-001", rule_name="Test Rule", severity=Severity.HIGH, category=Category.SECURITY, description="Test", recommendation="Fix it"),
        ]
        result = ScannerExecutionResult(
            scanner_name="TestScanner",
            scanner_id="test_scanner",
            status=ScannerStatus.COMPLETED_WITH_FINDINGS,
            findings=findings,
            findings_count=len(findings),
        )
        assert result.findings_count == 1
        assert len(result.findings) == 1

    def test_duration_detection(self):
        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 0, 0, 5, tzinfo=timezone.utc)  # 5 seconds
        result = ScannerExecutionResult(
            scanner_name="Test",
            scanner_id="test",
            status=ScannerStatus.COMPLETED,
            execution_start=start,
            execution_end=end,
            duration_ms=5000,
        )
        assert result.duration_ms == 5000
        assert result.duration_seconds == 5.0

    def test_to_dict(self):
        result = ScannerExecutionResult(
            scanner_name="Hadolint",
            scanner_id="hadolint",
            status=ScannerStatus.COMPLETED_NO_FINDINGS,
            applicable=True,
            enabled=True,
            version="2.12.0",
            files_scanned=5,
            rules_executed=10,
            findings_count=0,
        )
        d = result.to_dict()
        assert d["scanner_name"] == "Hadolint"
        assert d["scanner_id"] == "hadolint"
        assert d["status"] == "COMPLETED_NO_FINDINGS"
        assert d["applicable"] is True
        assert d["version"] == "2.12.0"
        assert d["files_scanned"] == 5
        assert d["rules_executed"] == 10
        assert d["findings_count"] == 0
        assert d["skipped_reason"] is None
        assert d["error_message"] is None

    def test_to_dict_with_skipped(self):
        result = ScannerExecutionResult(
            scanner_name="kube-score",
            scanner_id="kube_score",
            status=ScannerStatus.SKIPPED_NOT_APPLICABLE,
            applicable=False,
            skipped_reason="No Kubernetes manifests detected.",
        )
        d = result.to_dict()
        assert d["status"] == "SKIPPED_NOT_APPLICABLE"
        assert d["applicable"] is False
        assert d["skipped_reason"] == "No Kubernetes manifests detected."

    def test_to_dict_with_error(self):
        result = ScannerExecutionResult(
            scanner_name="Checkov",
            scanner_id="checkov",
            status=ScannerStatus.FAILED,
            error_message="Command exited with code 1",
        )
        d = result.to_dict()
        assert d["status"] == "FAILED"
        assert d["error_message"] == "Command exited with code 1"


class TestTechnologyDetectorApplicability:
    """get_scanner_applicability must correctly classify scanners."""

    @pytest.fixture
    def terraform_only_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "main.tf").touch()
            yield repo

    @pytest.fixture
    def docker_only_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Dockerfile").touch()
            yield repo

    @pytest.fixture
    def kubernetes_only_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "deployment.yaml").write_text("apiVersion: apps/v1\nkind: Deployment\n")
            yield repo

    @pytest.fixture
    def python_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "requirements.txt").write_text("flask==2.0.0\n")
            yield repo

    @pytest.fixture
    def node_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text('{"name": "test"}\n')
            yield repo

    @pytest.fixture
    def go_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "go.mod").write_text("module test\n")
            yield repo

    @pytest.fixture
    def java_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pom.xml").write_text("<project></project>\n")
            yield repo

    @pytest.fixture
    def empty_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_terraform_only(self, terraform_only_repo):
        app_map = get_scanner_applicability(terraform_only_repo, {"has_terraform": True})
        assert app_map["tfsec"].applicable is True
        assert app_map["checkov"].applicable is True
        assert app_map["kube_score"].applicable is False
        assert "No Kubernetes" in app_map["kube_score"].reason

    def test_docker_only(self, docker_only_repo):
        app_map = get_scanner_applicability(docker_only_repo, {"has_docker": True})
        assert app_map["hadolint"].applicable is True
        assert app_map["kube_score"].applicable is False
        assert "No Kubernetes" in app_map["kube_score"].reason
        assert app_map["tfsec"].applicable is False
        assert "No Terraform" in app_map["tfsec"].reason

    def test_kubernetes_only(self, kubernetes_only_repo):
        app_map = get_scanner_applicability(kubernetes_only_repo, {"has_kubernetes": True})
        assert app_map["kube_score"].applicable is True
        assert app_map["checkov"].applicable is True
        assert app_map["trivy_config"].applicable is True
        assert app_map["tfsec"].applicable is False

    def test_python_pip_audit(self, python_repo):
        app_map = get_scanner_applicability(python_repo, {})
        assert app_map["pip_audit"].applicable is True
        assert app_map["npm_audit"].applicable is False
        assert "package.json" in app_map["npm_audit"].reason
        assert app_map["govulncheck"].applicable is False

    def test_node_npm_audit(self, node_repo):
        app_map = get_scanner_applicability(node_repo, {})
        assert app_map["npm_audit"].applicable is True
        assert app_map["pip_audit"].applicable is False

    def test_go_govulncheck(self, go_repo):
        app_map = get_scanner_applicability(go_repo, {})
        assert app_map["govulncheck"].applicable is True

    def test_java_dependency_check(self, java_repo):
        app_map = get_scanner_applicability(java_repo, {})
        assert app_map["dependency_check"].applicable is True

    def test_always_run_scanners(self, empty_repo):
        """Gitleaks and trivy_filesystem should always be applicable."""
        app_map = get_scanner_applicability(empty_repo, {})
        assert app_map["gitleaks"].applicable is True
        assert app_map["trivy_filesystem"].applicable is True

    def test_get_scanners_for_stack_terraform(self, terraform_only_repo):
        scanners = get_scanners_for_stack(terraform_only_repo, {"has_terraform": True})
        assert "tfsec" in scanners
        assert "checkov" in scanners
        assert "kube_score" not in scanners
        assert "hadolint" not in scanners

    def test_get_scanners_for_stack_docker(self, docker_only_repo):
        scanners = get_scanners_for_stack(docker_only_repo, {"has_docker": True})
        assert "hadolint" in scanners
        assert "checkov" in scanners
        assert "tfsec" not in scanners

    def test_get_skipped_scanners(self, empty_repo):
        skipped = get_skipped_scanners(empty_repo, {})
        assert "kube_score" in skipped
        assert "No Kubernetes" in skipped["kube_score"]
        assert "tfsec" in skipped


class TestScannerRegistryExecution:
    """ScannerRegistry must track execution start/end, version, duration, and errors."""

    def test_disabled_scanner_records_disabled_status(self):
        """When CLI is unavailable, registry should return UNAVAILABLE status."""
        from app.scanners.registry import ScannerRegistry

        with patch.object(ScannerRegistry, "_register_adapters", return_value=None):
            registry = ScannerRegistry()

        # Register a mock adapter that says not available
        mock_adapter = MagicMock()
        mock_adapter.is_available.return_value = False
        mock_adapter.name = "MockScanner"
        mock_adapter.scanner_id = "mock_scanner"
        mock_adapter.get_version.return_value = None
        mock_adapter.get_files_scanned_count.return_value = None
        mock_adapter.get_rules_count.return_value = None
        mock_adapter.get_install_hint.return_value = "Install mock-scanner"
        registry._adapters["mock_scanner"] = mock_adapter

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            results = registry.run_scanners(["mock_scanner"], repo, {})

        assert len(results) == 1
        assert results[0].status == ScannerStatus.UNAVAILABLE
        assert results[0].scanner_id == "mock_scanner"

    def test_successful_scanner_records_completed(self):
        """When scanner succeeds, registry should return COMPLETED_WITH_FINDINGS or COMPLETED_NO_FINDINGS."""
        from app.rule_engine.base import Category, RuleFinding, Severity
        from app.scanners.registry import ScannerRegistry

        with patch.object(ScannerRegistry, "_register_adapters", return_value=None):
            registry = ScannerRegistry()

        mock_adapter = MagicMock()
        mock_adapter.is_available.return_value = True
        mock_adapter.name = "MockScanner"
        mock_adapter.scanner_id = "mock_scanner"
        mock_adapter.get_version.return_value = "1.0.0"
        mock_adapter.get_files_scanned_count.return_value = 10
        mock_adapter.get_rules_count.return_value = 25
        mock_adapter.scan.return_value = [
            RuleFinding(rule_id="TEST-001", rule_name="Test", severity=Severity.HIGH, category=Category.SECURITY, description="test", recommendation="fix"),
        ]
        registry._adapters["mock_scanner"] = mock_adapter

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            results = registry.run_scanners(["mock_scanner"], repo, {})

        assert len(results) == 1
        assert results[0].status == ScannerStatus.COMPLETED_WITH_FINDINGS
        assert results[0].version == "1.0.0"
        assert results[0].files_scanned == 10
        assert results[0].rules_executed == 25
        assert results[0].findings_count == 1
        assert results[0].execution_start is not None
        assert results[0].execution_end is not None
        assert results[0].duration_ms is not None

    def test_failed_scanner_records_failed(self):
        """When scanner raises, registry should return FAILED with error_message."""
        from app.scanners.registry import ScannerRegistry

        with patch.object(ScannerRegistry, "_register_adapters", return_value=None):
            registry = ScannerRegistry()

        mock_adapter = MagicMock()
        mock_adapter.is_available.return_value = True
        mock_adapter.name = "FailingScanner"
        mock_adapter.scanner_id = "failing_scanner"
        mock_adapter.get_version.return_value = None
        mock_adapter.get_files_scanned_count.return_value = None
        mock_adapter.get_rules_count.return_value = None
        mock_adapter.scan.side_effect = RuntimeError("Command timed out")
        registry._adapters["failing_scanner"] = mock_adapter

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            results = registry.run_scanners(["failing_scanner"], repo, {})

        assert len(results) == 1
        assert results[0].status == ScannerStatus.FAILED
        assert "Command timed out" in (results[0].error_message or "")

    def test_multiple_scanners_isolated_failures(self):
        """One failed scanner must not prevent others from completing."""
        from app.rule_engine.base import Category, RuleFinding, Severity
        from app.scanners.registry import ScannerRegistry

        with patch.object(ScannerRegistry, "_register_adapters", return_value=None):
            registry = ScannerRegistry()

        good = MagicMock()
        good.is_available.return_value = True
        good.name = "GoodScanner"
        good.scanner_id = "good"
        good.get_version.return_value = "1.0"
        good.get_files_scanned_count.return_value = 5
        good.get_rules_count.return_value = 10
        good.scan.return_value = [
            RuleFinding(rule_id="OK", rule_name="OK", severity=Severity.LOW, category=Category.SECURITY, description="ok", recommendation="ok"),
        ]

        bad = MagicMock()
        bad.is_available.return_value = True
        bad.name = "BadScanner"
        bad.scanner_id = "bad"
        bad.get_version.return_value = None
        bad.get_files_scanned_count.return_value = None
        bad.get_rules_count.return_value = None
        bad.scan.side_effect = RuntimeError("Crash")

        registry._adapters["good"] = good
        registry._adapters["bad"] = bad

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            results = registry.run_scanners(["good", "bad"], repo, {})

        assert len(results) == 2
        statuses = {r.scanner_id: r.status for r in results}
        assert statuses["good"] == ScannerStatus.COMPLETED_WITH_FINDINGS
        assert statuses["bad"] == ScannerStatus.FAILED


class TestScannerExecutionRecordSerialization:
    """Scanner execution records must serialize correctly in API responses."""

    def test_scanner_execution_record_to_api_dict(self):
        """Simulate the serialization used in API endpoints."""
        from datetime import timedelta

        from app.scanners.registry import ScannerRegistry

        start = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(seconds=3)

        result = ScannerExecutionResult(
            scanner_name="Hadolint",
            scanner_id="hadolint",
            status=ScannerStatus.COMPLETED_NO_FINDINGS,
            applicable=True,
            enabled=True,
            version="2.12.0",
            execution_start=start,
            execution_end=end,
            duration_ms=3000,
            files_scanned=3,
            rules_executed=15,
            findings_count=0,
        )

        api_dict = {
            "scanner_name": result.scanner_name,
            "scanner_id": result.scanner_id,
            "version": result.version,
            "status": result.status.value,
            "applicable": result.applicable,
            "enabled": result.enabled,
            "execution_start": result.execution_start.isoformat() if result.execution_start else None,
            "execution_end": result.execution_end.isoformat() if result.execution_end else None,
            "duration_ms": result.duration_ms,
            "files_scanned": result.files_scanned,
            "rules_executed": result.rules_executed,
            "findings_count": result.findings_count,
            "skipped_reason": result.skipped_reason,
            "error_message": result.error_message,
        }

        assert api_dict["scanner_name"] == "Hadolint"
        assert api_dict["status"] == "COMPLETED_NO_FINDINGS"
        assert api_dict["duration_ms"] == 3000
        assert api_dict["files_scanned"] == 3
        assert api_dict["rules_executed"] == 15
        assert api_dict["findings_count"] == 0

        # Should serialize to valid JSON
        json_str = json.dumps(api_dict)
        assert json_str is not None
        parsed = json.loads(json_str)
        assert parsed["scanner_name"] == "Hadolint"

    def test_skipped_scanner_serialization(self):
        result = ScannerExecutionResult(
            scanner_name="kube-score",
            scanner_id="kube_score",
            status=ScannerStatus.SKIPPED_NOT_APPLICABLE,
            applicable=False,
            skipped_reason="No Kubernetes manifests detected.",
        )

        api_dict = {
            "scanner_name": result.scanner_name,
            "scanner_id": result.scanner_id,
            "status": result.status.value,
            "applicable": result.applicable,
            "skipped_reason": result.skipped_reason,
        }

        assert api_dict["status"] == "SKIPPED_NOT_APPLICABLE"
        assert api_dict["applicable"] is False
        assert "No Kubernetes" in api_dict["skipped_reason"]

    def test_failed_scanner_serialization(self):
        result = ScannerExecutionResult(
            scanner_name="Trivy",
            scanner_id="trivy_filesystem",
            status=ScannerStatus.FAILED,
            error_message="Trivy scan failed: OCI runtime error",
        )

        api_dict = {
            "scanner_name": result.scanner_name,
            "scanner_id": result.scanner_id,
            "status": result.status.value,
            "error_message": result.error_message,
        }

        assert api_dict["status"] == "FAILED"
        assert "OCI runtime error" in api_dict["error_message"]


class TestEndToEndScannerExecution:
    """End-to-end validation of scanner execution flow."""

    def test_applicability_then_execution_flow(self):
        """Simulate the full flow: detect → check availability → run → record."""
        from app.rule_engine.base import Category, RuleFinding, Severity
        from app.scanners.registry import ScannerRegistry

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "Dockerfile").touch()
            (repo / "main.tf").touch()

            with patch.object(ScannerRegistry, "_register_adapters", return_value=None):
                registry = ScannerRegistry()

            hadolint = MagicMock()
            hadolint.is_available.return_value = True
            hadolint.name = "Hadolint"
            hadolint.scanner_id = "hadolint"
            hadolint.get_version.return_value = "2.12.0"
            hadolint.get_files_scanned_count.return_value = 1
            hadolint.get_rules_count.return_value = 30
            hadolint.scan.return_value = [
                RuleFinding(rule_id="DL3000", rule_name="Use WORKDIR", severity=Severity.MEDIUM, category=Category.SECURITY, description="Not using WORKDIR", recommendation="Use WORKDIR"),
            ]

            tfsec = MagicMock()
            tfsec.is_available.return_value = True
            tfsec.name = "tfsec"
            tfsec.scanner_id = "tfsec"
            tfsec.get_version.return_value = "1.28.0"
            tfsec.get_files_scanned_count.return_value = 2
            tfsec.get_rules_count.return_value = 50
            tfsec.scan.return_value = []

            registry._adapters["hadolint"] = hadolint
            registry._adapters["tfsec"] = tfsec

            detected_stack = {"has_docker": True, "has_terraform": True}

            # Step 1: Detect applicability
            app_map = get_scanner_applicability(repo, detected_stack)
            assert app_map["hadolint"].applicable is True
            assert app_map["tfsec"].applicable is True
            assert app_map["kube_score"].applicable is False

            # Step 2: Use explicit scanner IDs (not auto-detected, since auto-detection
            # would include other scanners like checkov, gitleaks, trivy_filesystem)
            scanner_ids = ["hadolint", "tfsec"]

            results = registry.run_scanners(scanner_ids, repo, detected_stack)

        # Step 3: Verify execution results
        result_map = {r.scanner_id: r for r in results}
        assert len(results) == 2

        # Hadolint should have findings
        hado = result_map["hadolint"]
        assert hado.status == ScannerStatus.COMPLETED_WITH_FINDINGS
        assert hado.findings_count == 1
        assert hado.version == "2.12.0"
        assert hado.duration_ms is not None

        # tfsec should have no findings
        tf = result_map["tfsec"]
        assert tf.status == ScannerStatus.COMPLETED_NO_FINDINGS
        assert tf.findings_count == 0
        assert tf.version == "1.28.0"
        assert tf.duration_ms is not None
