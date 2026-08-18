"""
npm audit adapter — Node.js SCA vulnerability scanning.
Also runs OSV Scanner if available.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.rule_engine.base import Category, RuleFinding, Severity
from app.scanners.adapters.base import BaseScannerAdapter
from app.scanners.normalizer import detect_category, map_severity


class NpmAuditAdapter(BaseScannerAdapter):
    """Adapter for npm audit and OSV Scanner for Node.js projects."""

    @property
    def name(self) -> str:
        return "npm audit"

    @property
    def scanner_id(self) -> str:
        return "npm_audit"

    def is_available(self) -> bool:
        return shutil.which("npm") is not None

    def _run_npm_audit(self, project_path: Path) -> list[RuleFinding]:
        findings: list[RuleFinding] = []
        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=str(project_path),
                capture_output=True, text=True, timeout=120,
            )
            output = result.stdout or result.stderr
            if not output.strip():
                return findings

            data = json.loads(output)
            vulnerabilities = data.get("vulnerabilities", {})

            for pkg_name, vuln in vulnerabilities.items():
                via = vuln.get("via", [])
                severity_str = vuln.get("severity", "medium")
                cvss_score = vuln.get("cvss", {}).get("score")

                for item in via:
                    if isinstance(item, dict):
                        cve = item.get("cve", "")
                        cwe = item.get("cwe", "")
                        advisory_url = item.get("url", "")
                        title = item.get("title", "")
                        severity_str = item.get("severity", severity_str)

                        findings.append(RuleFinding(
                            rule_id=f"npm-audit/{cve or item.get('source', 'UNKNOWN')}",
                            rule_name=f"npm audit: {title or pkg_name}",
                            severity=map_severity(severity_str),
                            category=Category.SECURITY,
                            description=title or f"Vulnerability in {pkg_name}",
                            recommendation=vuln.get("fixAvailable", False)
                                and "Upgrade to the latest compatible version."
                                or "No fix is currently available. Consider removing or replacing the package.",
                            file_path=f"node_modules/{pkg_name}",
                            scanner_name=self.name,
                            scanner_rule_id=cve or item.get("source", ""),
                            package=pkg_name,
                            installed_version=vuln.get("version", ""),
                            fixed_version=vuln.get("fixAvailable", {}).get("name", "") if isinstance(vuln.get("fixAvailable"), dict) else "",
                            cve=cve,
                            cwe=cwe,
                            references=[advisory_url] if advisory_url else [],
                            confidence=min(cvss_score / 10.0, 1.0) if cvss_score else 0.8,
                        ))

            range_findings = data.get("auditReportMetadata", {}).get("vulnerabilities", {})
            for pkg_name, vulns in range_findings.items():
                pass
        except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return findings

    def _run_osv_scanner(self, project_path: Path) -> list[RuleFinding]:
        findings: list[RuleFinding] = []
        if not shutil.which("osv-scanner"):
            return findings

        try:
            result = subprocess.run(
                ["osv-scanner", "--format", "json", "--recursive", str(project_path)],
                capture_output=True, text=True, timeout=180,
            )
            output = result.stdout.strip()
            if not output:
                return findings

            data = json.loads(output)
            results_list = data.get("results", [])
            for res in results_list:
                for pkg in res.get("packages", []):
                    pkg_name = pkg.get("package", {}).get("name", "")
                    pkg_version = pkg.get("package", {}).get("version", "")
                    for vuln in pkg.get("vulnerabilities", []):
                        osv_id = vuln.get("id", "")
                        aliases = vuln.get("aliases", [])
                        cve = next((a for a in aliases if a.startswith("CVE-")), "")
                        summary = vuln.get("summary", "")
                        severity_str = vuln.get("severity", [{}])[0].get("score", "") if vuln.get("severity") else "medium"

                        findings.append(RuleFinding(
                            rule_id=f"OSV/{osv_id}",
                            rule_name=f"OSV: {summary or osv_id}",
                            severity=map_severity(severity_str),
                            category=Category.SECURITY,
                            description=summary or f"Vulnerability in {pkg_name}",
                            recommendation=f"Upgrade {pkg_name} to a patched version.",
                            file_path=None,
                            scanner_name=self.name,
                            scanner_rule_id=osv_id,
                            package=pkg_name,
                            installed_version=pkg_version,
                            fixed_version="",
                            cve=cve,
                            references=vuln.get("references", []),
                        ))
        except Exception:
            pass
        return findings

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []

        has_package_json = (repo_path / "package.json").exists()
        has_yarn_lock = (repo_path / "yarn.lock").exists()
        has_pnpm_lock = (repo_path / "pnpm-lock.yaml").exists()

        if has_package_json:
            findings.extend(self._run_npm_audit(repo_path))

        if has_package_json or has_yarn_lock or has_pnpm_lock:
            findings.extend(self._run_osv_scanner(repo_path))

        return findings
