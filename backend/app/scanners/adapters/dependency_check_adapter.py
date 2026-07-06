"""
OWASP Dependency-Check adapter — Java/JVM SCA vulnerability scanning.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.rule_engine.base import Category, RuleFinding, Severity
from app.scanners.adapters.base import BaseScannerAdapter
from app.scanners.normalizer import map_severity


class DependencyCheckAdapter(BaseScannerAdapter):
    """Adapter for OWASP Dependency-Check."""

    @property
    def name(self) -> str:
        return "Dependency-Check"

    @property
    def scanner_id(self) -> str:
        return "dependency_check"

    def is_available(self) -> bool:
        return shutil.which("dependency-check") is not None or shutil.which("dependency-check.sh") is not None

    def _get_binary(self) -> str | None:
        for name in ("dependency-check", "dependency-check.sh"):
            path = shutil.which(name)
            if path:
                return path
        return None

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []

        bin_path = self._get_binary()
        if not bin_path:
            return findings

        has_pom = (repo_path / "pom.xml").exists()
        has_gradle = any((repo_path / f).exists() for f in ("build.gradle", "build.gradle.kts", "gradle.lockfile"))
        if not has_pom and not has_gradle:
            return findings

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.json"
            try:
                result = subprocess.run(
                    [
                        bin_path, "--scan", str(repo_path),
                        "--format", "JSON",
                        "--out", str(report_path),
                        "--failOnCVSS", "0",
                        "--suppression", "/dev/null" if Path("/dev/null").exists() else "NUL",
                    ],
                    capture_output=True, text=True, timeout=300,
                )
            except subprocess.TimeoutExpired:
                return findings
            except FileNotFoundError:
                return findings

            if not report_path.exists():
                return findings

            try:
                data = json.loads(report_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return findings

            deps = data.get("dependencies", [])
            for dep in deps:
                pkg_name = dep.get("fileName", "")
                evidence = dep.get("evidenceCollected", {})
                versions_text = " ".join(e.get("text", "") for ev in evidence.values() for e in ev if isinstance(ev, list)) if isinstance(evidence, dict) else ""
                installed_version = versions_text.strip()[:100] if versions_text else ""

                for vuln in dep.get("vulnerabilities", []):
                    vuln_id = vuln.get("name", "DC-UNKNOWN")
                    severity_str = vuln.get("severity", "medium")
                    cvss_score = vuln.get("cvssv3", {}).get("baseScore")
                    description = vuln.get("description", "")
                    cve = next((ref.get("name", "") for ref in vuln.get("references", []) if ref.get("name", "").startswith("CVE-")), "")
                    cwe_list = [ref.get("name", "") for ref in vuln.get("references", []) if "CWE" in ref.get("name", "")]
                    cwe = cwe_list[0] if cwe_list else ""
                    refs = [ref.get("url", "") for ref in vuln.get("references", []) if ref.get("url")]
                    fix_version = vuln.get("fixedVersion", "")

                    findings.append(RuleFinding(
                        rule_id=f"Dependency-Check/{vuln_id}",
                        rule_name=f"Dependency-Check: {vuln_id}",
                        severity=map_severity(severity_str),
                        category=Category.SECURITY,
                        description=description or f"Vulnerability in {pkg_name}",
                        recommendation=f"Upgrade {pkg_name} to version {fix_version} or later."
                            if fix_version else f"No fix available for {pkg_name}.",
                        file_path=None,
                        scanner_name=self.name,
                        scanner_rule_id=vuln_id,
                        package=pkg_name,
                        installed_version=installed_version,
                        fixed_version=fix_version,
                        cve=cve,
                        cwe=cwe,
                        references=refs,
                        confidence=min((cvss_score or 5.0) / 10.0, 1.0) if cvss_score else 0.8,
                    ))
        return findings
