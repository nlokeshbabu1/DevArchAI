"""
Hadolint adapter — Dockerfile linter.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.rule_engine.base import Category, RuleFinding, Severity
from app.scanners.adapters.base import BaseScannerAdapter
from app.scanners.normalizer import detect_category, map_severity


class HadolintAdapter(BaseScannerAdapter):
    """Adapter for Hadolint Dockerfile linting."""

    @property
    def name(self) -> str:
        return "Hadolint"

    @property
    def scanner_id(self) -> str:
        return "hadolint"

    def is_available(self) -> bool:
        return shutil.which("hadolint") is not None

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []

        docker_files: list[str] = detection.get("docker_files", [])
        if not docker_files:
            docker_files = [str(p) for p in repo_path.rglob("*") if p.name.lower() in ("dockerfile", "containerfile")]

        for df_rel in docker_files:
            df_path = repo_path / df_rel
            if not df_path.exists():
                continue

            try:
                result = subprocess.run(
                    ["hadolint", "--no-color", "-f", "json", str(df_path)],
                    capture_output=True, text=True, timeout=60,
                )
                if result.returncode not in (0, 1):
                    continue

                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    rule_id = entry.get("code", "HADOLINT-UNKNOWN")
                    severity_str = entry.get("level", "warning")
                    message = entry.get("message", "")
                    line_number = entry.get("line")

                    findings.append(RuleFinding(
                        rule_id=f"Hadolint/{rule_id}",
                        rule_name=f"Hadolint: {rule_id}",
                        severity=map_severity(severity_str),
                        category=detect_category(message, rule_id),
                        description=message,
                        recommendation=f"Fix Dockerfile issue {rule_id}: {message}",
                        file_path=str(df_rel),
                        line_number=line_number,
                        scanner_name=self.name,
                        scanner_rule_id=rule_id,
                        references=[f"https://github.com/hadolint/hadolint/wiki/{rule_id}"],
                    ))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return findings
