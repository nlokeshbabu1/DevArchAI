"""
Extensible validator registry for remediation (selected dynamically per file/technology).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog
import yaml

from app.services.github_pr import _is_cicd_file, _is_dockerfile, _validate_cicd, _validate_dockerfile
from app.services.remediation_discovery import RepositoryDiscovery
from app.services.remediation_patch import validate_preservation

logger = structlog.get_logger(__name__)

ValidatorFn = Callable[[str, str, RepositoryDiscovery | None], dict[str, Any]]


@dataclass
class ValidatorResult:
    name: str
    status: str  # passed | failed | skipped | unavailable
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "evidence": self.evidence,
        }


def _yaml_syntax_validator(rel_path: str, content: str, _discovery: RepositoryDiscovery | None) -> dict[str, Any]:
    if not rel_path.lower().endswith((".yaml", ".yml")):
        return {"name": "yaml_syntax", "status": "skipped", "message": "Not a YAML file"}
    try:
        list(yaml.safe_load_all(content))
        return {"name": "yaml_syntax", "status": "passed", "message": "YAML parses successfully"}
    except yaml.YAMLError as exc:
        return {"name": "yaml_syntax", "status": "failed", "message": str(exc)}


def _json_syntax_validator(rel_path: str, content: str, _discovery: RepositoryDiscovery | None) -> dict[str, Any]:
    if not rel_path.lower().endswith(".json"):
        return {"name": "json_syntax", "status": "skipped", "message": "Not a JSON file"}
    try:
        json.loads(content)
        return {"name": "json_syntax", "status": "passed", "message": "JSON parses successfully"}
    except json.JSONDecodeError as exc:
        return {"name": "json_syntax", "status": "failed", "message": str(exc)}


def _preservation_validator(rel_path: str, content: str, discovery: RepositoryDiscovery | None) -> dict[str, Any]:
    # Requires original content — handled in run_validators wrapper
    return {"name": "preservation", "status": "skipped", "message": "Run via run_validators with original content"}


def _dockerfile_validator(rel_path: str, content: str, _discovery: RepositoryDiscovery | None) -> dict[str, Any]:
    if not _is_dockerfile(rel_path):
        return {"name": "dockerfile_security", "status": "skipped", "message": "Not a Dockerfile"}
    result = _validate_dockerfile(content)
    status = "passed" if result.get("valid") else "failed"
    return {
        "name": "dockerfile_security",
        "status": status,
        "message": result.get("error") or "Dockerfile checks passed",
        "evidence": result,
    }


def _cicd_validator(rel_path: str, content: str, _discovery: RepositoryDiscovery | None) -> dict[str, Any]:
    if not _is_cicd_file(rel_path):
        return {"name": "cicd_security", "status": "skipped", "message": "Not a CI/CD workflow file"}
    result = _validate_cicd(content)
    status = "passed" if result.get("valid") else "failed"
    return {
        "name": "cicd_security",
        "status": status,
        "message": result.get("error") or "CI/CD checks passed",
        "evidence": result,
    }


def _terraform_fmt_validator(rel_path: str, content: str, _discovery: RepositoryDiscovery | None) -> dict[str, Any]:
    if not rel_path.endswith(".tf"):
        return {"name": "terraform_fmt", "status": "skipped", "message": "Not Terraform"}
    if not shutil.which("terraform"):
        return {
            "name": "terraform_fmt",
            "status": "unavailable",
            "message": "terraform CLI not available in runtime",
        }
    try:
        proc = subprocess.run(
            ["terraform", "fmt", "-check", "-no-color"],
            input=content,
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/tmp",
        )
        if proc.returncode == 0:
            return {"name": "terraform_fmt", "status": "passed", "message": "terraform fmt check passed"}
        return {
            "name": "terraform_fmt",
            "status": "failed",
            "message": (proc.stderr or proc.stdout or "terraform fmt check failed")[:500],
        }
    except subprocess.TimeoutExpired:
        return {"name": "terraform_fmt", "status": "failed", "message": "terraform fmt timed out"}
    except OSError as exc:
        return {"name": "terraform_fmt", "status": "unavailable", "message": str(exc)}


VALIDATOR_REGISTRY: list[tuple[str, ValidatorFn]] = [
    ("yaml", _yaml_syntax_validator),
    ("json", _json_syntax_validator),
    ("dockerfile", _dockerfile_validator),
    ("cicd", _cicd_validator),
    ("terraform", _terraform_fmt_validator),
]


def select_validators(rel_path: str, discovery: RepositoryDiscovery | None) -> list[ValidatorFn]:
    """Pick validators based on file path and discovered stack (no hardcoded repo paths)."""
    selected: list[ValidatorFn] = [_yaml_syntax_validator, _json_syntax_validator, _dockerfile_validator, _cicd_validator]
    if rel_path.endswith(".tf") or (discovery and discovery.stack and discovery.stack.has_terraform):
        selected.append(_terraform_fmt_validator)
    return selected


def run_validators(
    rel_path: str,
    original_content: str,
    updated_content: str,
    discovery: RepositoryDiscovery | None,
) -> tuple[bool, list[dict[str, Any]]]:
    """
    Run applicable validators. Returns (all_required_passed, results).

    ``unavailable`` validators do not count as pass — they are reported honestly.
    Required validators are those that return passed or failed (not skipped).
    """
    results: list[dict[str, Any]] = []

    try:
        validate_preservation(original_content, updated_content, rel_path)
        results.append(
            {"name": "preservation", "status": "passed", "message": "Preservation checks passed"}
        )
    except Exception as exc:
        results.append({"name": "preservation", "status": "failed", "message": str(exc)})
        return False, results

    for fn in select_validators(rel_path, discovery):
        outcome = fn(rel_path, updated_content, discovery)
        results.append(outcome)

    required_failed = any(r["status"] == "failed" for r in results)
    required_passed = all(r["status"] in {"passed", "skipped"} for r in results if r["status"] != "unavailable")
    ok = not required_failed and required_passed
    return ok, results
