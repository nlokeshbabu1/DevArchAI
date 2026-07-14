"""
govulncheck adapter — Go vulnerability scanning.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.rule_engine.base import Category, RuleFinding, Severity
from app.scanners.adapters.base import BaseScannerAdapter
from app.scanners.normalizer import map_severity


class GovulncheckAdapter(BaseScannerAdapter):
    """Adapter for govulncheck Go vulnerability scanning."""

    @property
    def name(self) -> str:
        return "govulncheck"

    @property
    def scanner_id(self) -> str:
        return "govulncheck"

    def is_available(self) -> bool:
        return shutil.which("govulncheck") is not None

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []

        go_mod = repo_path / "go.mod"
        if not go_mod.exists():
            return findings

        try:
            result = subprocess.run(
                ["govulncheck", "-json", "./..."],
                cwd=str(repo_path),
                capture_output=True, text=True, timeout=180,
            )
            output = result.stdout.strip()
            if not output:
                return findings

            data = json.loads(output)

            vulns = data.get("Vulnerabilities", []) if isinstance(data, dict) else data if isinstance(data, list) else []
            for vuln in vulns:
                vuln_id = vuln.get("ID", "GO-UNKNOWN")
                pkg_path = vuln.get("PkgPath", "")
                mod_path = vuln.get("ModPath", "")
                version = vuln.get("Version", "")
                fixed_version = vuln.get("FixedVersion", "")
                description = vuln.get("Description", "") or vuln.get("Summary", "")
                severity_str = vuln.get("Severity", "medium")
                aliases = vuln.get("Aliases", [])
                cve = next((a for a in aliases if a.startswith("CVE-")), "")

                findings.append(RuleFinding(
                    rule_id=f"govulncheck/{vuln_id}",
                    rule_name=f"govulncheck: {vuln_id}",
                    severity=map_severity(severity_str),
                    category=Category.SECURITY,
                    description=description or f"Vulnerability in {mod_path}",
                    recommendation=f"Upgrade {mod_path} from {version} to {fixed_version}" if fixed_version
                    else f"No patch available for {mod_path}. Monitor for updates.",
                    file_path=pkg_path or None,
                    scanner_name=self.name,
                    scanner_rule_id=vuln_id,
                    package=mod_path,
                    installed_version=version,
                    fixed_version=fixed_version,
                    cve=cve,
                    references=aliases + vuln.get("References", []),
                ))
        except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return findings
