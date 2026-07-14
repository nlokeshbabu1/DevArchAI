"""
pip-audit adapter — Python SCA vulnerability scanning.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.rule_engine.base import Category, RuleFinding
from app.scanners.adapters.base import BaseScannerAdapter
from app.scanners.normalizer import map_severity


class PipAuditAdapter(BaseScannerAdapter):
    """Adapter for pip-audit Python dependency scanning."""

    @property
    def name(self) -> str:
        return "pip-audit"

    @property
    def scanner_id(self) -> str:
        return "pip_audit"

    def is_available(self) -> bool:
        return shutil.which("pip-audit") is not None

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []

        req_file = repo_path / "requirements.txt"
        req_file_alt = repo_path / "requirement.txt"  # common misspelling
        pipfile = repo_path / "Pipfile"
        pyproject = repo_path / "pyproject.toml"

        if not any(f.exists() for f in [req_file, req_file_alt, pipfile, pyproject]):
            return findings

        # Determine which requirement file to use (prefer exact match, fallback to misspelling)
        if req_file.exists():
            requirements_arg = str(req_file)
        elif req_file_alt.exists():
            requirements_arg = str(req_file_alt)
        elif pyproject.exists():
            requirements_arg = str(pyproject)
        elif pipfile.exists():
            requirements_arg = str(pipfile)
        else:
            requirements_arg = ""

        if not requirements_arg:
            return findings

        try:
            result = subprocess.run(
                ["pip-audit", "--requirement", requirements_arg, "--format", "json"],
                capture_output=True, text=True, timeout=120,
            )
            output = result.stdout.strip()
            if not output:
                return findings

            data = json.loads(output)
            deps = data.get("dependencies", [])

            for dep in deps:
                pkg_name = dep.get("name", "")
                pkg_version = dep.get("version", "")
                for vuln in dep.get("vulns", []):
                    vuln_id = vuln.get("id", "PIP-UNKNOWN")
                    description = vuln.get("description", "")
                    severity_str = vuln.get("severity", "medium")
                    fix_versions = vuln.get("fix_versions", [])

                    findings.append(RuleFinding(
                        rule_id=f"pip-audit/{vuln_id}",
                        rule_name=f"pip-audit: {description or vuln_id}",
                        severity=map_severity(severity_str),
                        category=Category.SECURITY,
                        description=description or f"Vulnerability in {pkg_name} {pkg_version}",
                        recommendation=f"Upgrade {pkg_name} from {pkg_version} to {' or '.join(fix_versions)}."
                            if fix_versions
                            else f"No fix available for {pkg_name}. Consider removing or replacing.",
                        file_path=requirements_arg,
                        scanner_name=self.name,
                        scanner_rule_id=vuln_id,
                        package=pkg_name,
                        installed_version=pkg_version,
                        fixed_version=fix_versions[0] if fix_versions else "",
                        cve=vuln_id if vuln_id.startswith("CVE-") else "",
                        references=vuln.get("aliases", []),
                    ))
        except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return findings
