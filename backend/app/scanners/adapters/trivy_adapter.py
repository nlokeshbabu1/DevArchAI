"""
Trivy adapter — vulnerability scanning, filesystem scanning, config scanning, SBOM.

Provides two adapter variants:
- TrivyFilesystemAdapter: scans repo filesystem for vulnerabilities + secrets
- TrivyConfigAdapter: scans Kubernetes/Terraform/Docker configs for misconfigurations
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.rule_engine.base import Category, RuleFinding, Severity
from app.scanners.adapters.base import BaseScannerAdapter
from app.scanners.normalizer import detect_category, map_severity


class _TrivyBaseAdapter(BaseScannerAdapter):
    """Shared logic for Trivy-based scanners."""

    TRIVY_SEVERITY_MAP = {
        "CRITICAL": Severity.CRITICAL,
        "HIGH": Severity.HIGH,
        "MEDIUM": Severity.MEDIUM,
        "LOW": Severity.LOW,
        "UNKNOWN": Severity.INFO,
    }

    def _map_trivy_severity(self, sev: str) -> Severity:
        return self.TRIVY_SEVERITY_MAP.get(sev.upper(), Severity.INFO)

    def _parse_trivy_output(self, output: str) -> list[RuleFinding]:
        findings: list[RuleFinding] = []

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return findings

        # Trivy results can be in various formats depending on scan type
        results_list = data.get("Results", []) if isinstance(data, dict) else data if isinstance(data, list) else []

        for result in results_list:
            target = result.get("Target", "")
            result_type = result.get("Type", "")
            file_path = result.get("FilePath", target) if result.get("FilePath") else target

            # Vulnerabilities
            for vuln in result.get("Vulnerabilities", []):
                vuln_id = vuln.get("VulnerabilityID", "TRIVY-UNKNOWN")
                pkg_name = vuln.get("PkgName", "")
                installed_ver = vuln.get("InstalledVersion", "")
                fixed_ver = vuln.get("FixedVersion", "")
                severity_str = vuln.get("Severity", "UNKNOWN")
                title = vuln.get("Title", "")
                description = vuln.get("Description", "") or title
                cwe_ids = vuln.get("CweIDs", [])
                references = vuln.get("References", [])
                cvss_score = None
                for source in ("cvss", "CVSS"):
                    cvss_data = vuln.get(source, {})
                    if isinstance(cvss_data, dict):
                        for vendor_data in cvss_data.values():
                            if isinstance(vendor_data, dict) and "V3Score" in vendor_data:
                                cvss_score = vendor_data["V3Score"]
                            elif isinstance(vendor_data, dict) and "Score" in vendor_data:
                                cvss_score = vendor_data["Score"]

                confidence = min((cvss_score or 5.0) / 10.0, 1.0) if cvss_score else 0.8

                evidence_parts = []
                if vuln.get("PrimaryURL"):
                    evidence_parts.append(f"URL: {vuln['PrimaryURL']}")
                if vuln.get("PublishedDate"):
                    evidence_parts.append(f"Published: {vuln['PublishedDate']}")
                evidence = "; ".join(evidence_parts) if evidence_parts else None

                findings.append(RuleFinding(
                    rule_id=f"Trivy/{vuln_id}",
                    rule_name=f"Trivy: {title or vuln_id}",
                    severity=self._map_trivy_severity(severity_str),
                    category=Category.SECURITY,
                    description=description or f"Vulnerability {vuln_id} in {pkg_name}",
                    recommendation=f"Upgrade {pkg_name} from {installed_ver} to {fixed_ver}."
                        if fixed_ver else f"No fix available for {pkg_name}. Monitor for updates.",
                    file_path=file_path or None,
                    scanner_name=self.name,
                    scanner_rule_id=vuln_id,
                    package=pkg_name or None,
                    installed_version=installed_ver or None,
                    fixed_version=fixed_ver or None,
                    cve=vuln_id if vuln_id.startswith("CVE-") else "",
                    cwe=cwe_ids[0] if cwe_ids else "",
                    references=references,
                    evidence=evidence,
                    confidence=confidence,
                ))

            # Secrets (Trivy's built-in secret scanner)
            for secret in result.get("Secrets", []):
                rule_id = secret.get("RuleID", "TRIVY-SECRET")
                title = secret.get("Title", "") or rule_id
                match_str = secret.get("Match", "")
                severity_str = secret.get("Severity", "HIGH")
                start_line = secret.get("StartLine")
                end_line = secret.get("EndLine")
                code = secret.get("Code", "")

                findings.append(RuleFinding(
                    rule_id=f"Trivy/{rule_id}",
                    rule_name=f"Trivy Secret: {title}",
                    severity=self._map_trivy_severity(severity_str),
                    category=Category.SECURITY,
                    description=title,
                    recommendation=f"Remove the secret from {file_path}. Use environment variables or a secrets manager.",
                    file_path=file_path or None,
                    line_number=start_line or end_line,
                    scanner_name=self.name,
                    scanner_rule_id=rule_id,
                    evidence=code or match_str,
                ))

            # Misconfigurations (IaC scanning)
            for misconfig in result.get("Misconfigurations", []):
                mc_id = misconfig.get("ID", "TRIVY-CONFIG")
                mc_title = misconfig.get("Title", "") or mc_id
                mc_severity = misconfig.get("Severity", "MEDIUM")
                mc_description = misconfig.get("Description", "")
                mc_message = misconfig.get("Message", "")
                mc_resolution = misconfig.get("Resolution", "")
                mc_links = misconfig.get("References", [])
                mc_start = misconfig.get("StartLine") or misconfig.get("CauseMetadata", {}).get("StartLine")
                mc_file = misconfig.get("CauseMetadata", {}).get("File", file_path) if isinstance(misconfig.get("CauseMetadata"), dict) else file_path

                display_path = mc_file.replace(str(self._last_repo_path) + "/", "") if hasattr(self, '_last_repo_path') and mc_file else mc_file

                findings.append(RuleFinding(
                    rule_id=f"Trivy/{mc_id}",
                    rule_name=f"Trivy Config: {mc_title}",
                    severity=self._map_trivy_severity(mc_severity),
                    category=detect_category(mc_description, mc_id),
                    description=mc_description or mc_message or mc_title,
                    recommendation=mc_resolution or f"Fix misconfiguration: {mc_title}",
                    file_path=display_path or None,
                    line_number=mc_start,
                    scanner_name=self.name,
                    scanner_rule_id=mc_id,
                    references=mc_links,
                ))

        return findings

    def _run_trivy(self, args: list[str], timeout: int = 300) -> list[RuleFinding]:
        try:
            result = subprocess.run(
                ["trivy"] + args,
                capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode not in (0, 1):
                return []
            return self._parse_trivy_output(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []


class TrivyFilesystemAdapter(_TrivyBaseAdapter):
    """Trivy filesystem scanner for vulnerabilities + secrets."""

    @property
    def name(self) -> str:
        return "Trivy"

    @property
    def scanner_id(self) -> str:
        return "trivy_filesystem"

    def is_available(self) -> bool:
        return shutil.which("trivy") is not None

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []
        self._last_repo_path = repo_path  # For path normalization

        # Filesystem vulnerability scan
        fs_findings = self._run_trivy([
            "fs", "--format", "json",
            "--severity", "CRITICAL,HIGH,MEDIUM,LOW",
            "--scanners", "vuln,secret",
            str(repo_path),
        ], timeout=300)
        findings.extend(fs_findings)

        return findings


class TrivyConfigAdapter(_TrivyBaseAdapter):
    """Trivy config scanner for IaC misconfigurations."""

    @property
    def name(self) -> str:
        return "Trivy Config"

    @property
    def scanner_id(self) -> str:
        return "trivy_config"

    def is_available(self) -> bool:
        return shutil.which("trivy") is not None

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []
        self._last_repo_path = repo_path

        # Config scanning for misconfigurations
        config_findings = self._run_trivy([
            "config", "--format", "json",
            "--severity", "CRITICAL,HIGH,MEDIUM,LOW",
            str(repo_path),
        ], timeout=300)
        findings.extend(config_findings)

        return findings
