"""
tfsec adapter — Terraform security scanning.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.rule_engine.base import RuleFinding
from app.scanners.adapters.base import BaseScannerAdapter
from app.scanners.normalizer import detect_category, map_severity


class TfsecAdapter(BaseScannerAdapter):
    """Adapter for tfsec Terraform security scanner."""

    @property
    def name(self) -> str:
        return "tfsec"

    @property
    def scanner_id(self) -> str:
        return "tfsec"

    def is_available(self) -> bool:
        return shutil.which("tfsec") is not None

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []

        if not detection.get("has_terraform", False):
            return findings

        try:
            result = subprocess.run(
                ["tfsec", str(repo_path), "--format", "json", "--no-colour", "--soft-fail"],
                capture_output=True, text=True, timeout=180,
            )
            output = result.stdout.strip()
            if not output:
                return findings

            data = json.loads(output)

            results = data.get("results", [])
            for res in results:
                rule_id = res.get("rule_id", "TFSEC-UNKNOWN")
                description = res.get("description", "")
                long_desc = res.get("long_description", "")
                file_path = res.get("location", {}).get("filename", "") if isinstance(res.get("location"), dict) else ""
                line_number = res.get("location", {}).get("start_line") if isinstance(res.get("location"), dict) else None
                severity_str = res.get("severity", "medium")
                resolution = res.get("resolution", "")
                links = res.get("links", [])

                display_path = file_path.replace(str(repo_path) + "/", "") if file_path else ""

                findings.append(RuleFinding(
                    rule_id=f"tfsec/{rule_id}",
                    rule_name=f"tfsec: {description or rule_id}",
                    severity=map_severity(severity_str),
                    category=detect_category(long_desc or description, rule_id),
                    description=long_desc or description or rule_id,
                    recommendation=resolution or description,
                    file_path=display_path or None,
                    line_number=line_number,
                    scanner_name=self.name,
                    scanner_rule_id=rule_id,
                    references=links,
                ))
        except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return findings
