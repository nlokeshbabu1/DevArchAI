"""
kube-score adapter — Kubernetes manifest scoring and analysis.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.rule_engine.base import RuleFinding
from app.scanners.adapters.base import BaseScannerAdapter
from app.scanners.normalizer import detect_category, map_severity


class KubeScoreAdapter(BaseScannerAdapter):
    """Adapter for kube-score Kubernetes manifest analysis."""

    @property
    def name(self) -> str:
        return "kube-score"

    @property
    def scanner_id(self) -> str:
        return "kube_score"

    def is_available(self) -> bool:
        return shutil.which("kube-score") is not None

    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        findings: list[RuleFinding] = []

        if not detection.get("has_kubernetes", False):
            return findings

        k8s_files = detection.get("kubernetes_files", [])
        if not k8s_files:
            k8s_files = [str(p.relative_to(repo_path)) for p in repo_path.rglob("*")
                         if p.suffix in (".yaml", ".yml")
                         and any(kw in str(p).lower() for kw in ("kubernetes", "k8s", "deployment", "service", "pod", "configmap", "secret", "ingress"))]

        for kf_rel in k8s_files:
            kf_path = repo_path / kf_rel
            if not kf_path.exists():
                continue

            try:
                result = subprocess.run(
                    ["kube-score", "score", str(kf_path), "--output-format", "json"],
                    capture_output=True, text=True, timeout=60,
                )
                output = result.stdout.strip()
                if not output:
                    continue

                data = json.loads(output)
                entries = data if isinstance(data, list) else [data]

                for entry in entries:
                    checks = entry.get("checks", []) if isinstance(entry, dict) else entry.get("results", [])
                    for check in checks:
                        check_id = check.get("check", {}).get("name", "KUBE-UNKNOWN") if isinstance(check.get("check"), dict) else check.get("name", "KUBE-UNKNOWN")
                        comment = check.get("comment", "")
                        severity_str = check.get("grade") or check.get("severity", "warning")
                        file_ref = check.get("file", {}).get("path", str(kf_rel)) if isinstance(check.get("file"), dict) else str(kf_rel)

                        grade = check.get("grade", "")
                        if grade in ("A+", "A", "A-", "B+"):
                            continue

                        findings.append(RuleFinding(
                            rule_id=f"kube-score/{check_id}",
                            rule_name=f"kube-score: {check_id}",
                            severity=map_severity(severity_str),
                            category=detect_category(comment, check_id),
                            description=comment or check_id,
                            recommendation=f"Review and fix Kubernetes manifest issue: {check_id}",
                            file_path=file_ref or str(kf_rel),
                            scanner_name=self.name,
                            scanner_rule_id=check_id,
                        ))
            except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return findings
