"""
Checkov adapter — Terraform and cloud infrastructure scanning.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.rule_engine.base import RuleFinding
from app.scanners.adapters.base import BaseScannerAdapter
from app.scanners.normalizer import detect_category, map_severity


class CheckovAdapter(BaseScannerAdapter):
    """Adapter for Checkov infrastructure as code scanning."""

    @property
    def name(self) -> str:
        return "Checkov"

    @property
    def scanner_id(self) -> str:
        return "checkov"

    def is_available(self) -> bool:
        return shutil.which("checkov") is not None

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []

        has_terraform = detection.get("has_terraform", False)
        has_kubernetes = detection.get("has_kubernetes", False)
        has_docker = detection.get("has_docker", False)
        has_cicd = detection.get("has_github_actions", False) or detection.get("has_gitlab_ci", False)

        if not any([has_terraform, has_kubernetes, has_docker, has_cicd]):
            return findings

        frameworks = []
        if has_terraform:
            frameworks.append("terraform")
        if has_kubernetes:
            frameworks.append("kubernetes")
        if has_docker:
            frameworks.append("dockerfile")
        if has_cicd:
            frameworks.append("github_actions")

        try:
            result = subprocess.run(
                [
                    "checkov", "--directory", str(repo_path),
                    "--framework", ",".join(frameworks),
                    "--output", "json",
                    "--compact",
                ],
                capture_output=True, text=True, timeout=180,
            )
            output = result.stdout.strip()
            if not output:
                return findings

            raw = json.loads(output)
            results_list: list[dict] = []

            if isinstance(raw, list):
                for result_group in raw:
                    group_results = result_group.get("results", {})
                    failed = group_results.get("failed_checks", [])
                    results_list.extend(failed)
            elif isinstance(raw, dict):
                group_results = raw.get("results", {})
                if isinstance(group_results, dict):
                    results_list = group_results.get("failed_checks", [])
                if not results_list:
                    for key in ("failed_checks", "checks"):
                        if key in raw:
                            results_list = raw.get(key, [])
                            break

            for check in results_list:
                    check_id = check.get("check_id", "CKV-UNKNOWN")
                    check_name = check.get("check_name", "")
                    file_path = check.get("file_path", "").replace(str(repo_path) + "/", "")
                    resource = check.get("resource", "")
                    guideline = check.get("guideline", "")
                    severity_str = check.get("severity", "medium")

                    description = check_name or check.get("check_name", check_id)
                    if resource:
                        description = f"{description} in {resource}"

                    findings.append(RuleFinding(
                        rule_id=f"Checkov/{check_id}",
                        rule_name=f"Checkov: {check_name or check_id}",
                        severity=map_severity(severity_str),
                        category=detect_category(description, check_id),
                        description=description,
                        recommendation=check.get("check_name", ""),
                        file_path=file_path or None,
                        scanner_name=self.name,
                        scanner_rule_id=check_id,
                        references=[guideline] if guideline else [],
                        evidence=json.dumps({"resource": resource}) if resource else None,
                    ))
        except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return findings
