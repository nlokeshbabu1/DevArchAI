"""
Gitleaks adapter — secrets/credentials scanning.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.rule_engine.base import Category, RuleFinding, Severity
from app.scanners.adapters.base import BaseScannerAdapter
from app.scanners.normalizer import map_severity


class GitleaksAdapter(BaseScannerAdapter):
    """Adapter for Gitleaks secret scanning."""

    @property
    def name(self) -> str:
        return "Gitleaks"

    @property
    def scanner_id(self) -> str:
        return "gitleaks"

    def is_available(self) -> bool:
        return shutil.which("gitleaks") is not None

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []

        try:
            result = subprocess.run(
                ["gitleaks", "detect", "--source", str(repo_path), "--no-git", "-f", "json"],
                capture_output=True, text=True, timeout=120,
            )
            output = result.stdout.strip()
            if not output:
                return findings

            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                return findings

            entries = data if isinstance(data, list) else [data]

            for entry in entries:
                rule_id = entry.get("RuleID", "GITLEAKS-UNKNOWN")
                description = entry.get("Description", "") or entry.get("Match", "")
                file_path = entry.get("File", "")
                line_number = entry.get("StartLine")
                secret_type = entry.get("Tags", "")
                severity_str = entry.get("Severity", "high")

                evidence = entry.get("Match", "")
                commit = entry.get("Commit", "")

                findings.append(RuleFinding(
                    rule_id=f"Gitleaks/{rule_id}",
                    rule_name=f"Gitleaks: {description or rule_id}",
                    severity=map_severity(severity_str),
                    category=Category.SECURITY,
                    description=description or f"Secret detected: {rule_id}",
                    recommendation=f"Remove the secret from file {file_path}. "
                                   "Use environment variables or a secrets manager (e.g. HashiCorp Vault, AWS Secrets Manager).",
                    file_path=file_path or None,
                    line_number=line_number,
                    scanner_name=self.name,
                    scanner_rule_id=rule_id,
                    evidence=evidence,
                    references=entry.get("Link", "").split(",") if entry.get("Link") else [],
                ))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return findings
