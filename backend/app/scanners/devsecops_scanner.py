"""
DevSecOps Scanner Engine

Production-grade security scanner for DevOps architectures.
Scans Dockerfile, Kubernetes YAML, Terraform, and CI/CD pipelines.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import structlog

from app.rules.base import RuleFinding, Severity
from app.rules.devsecops import RULE_COUNTS

logger = structlog.get_logger(__name__)


@dataclass
class ScanResult:
    """Result of a security scan."""
    repository: str
    scan_timestamp: str
    security_score: int
    total_rules: int
    rules_passed: int
    rules_failed: int
    findings: list[dict[str, Any]]
    findings_by_severity: dict[str, int]
    findings_by_category: dict[str, int]
    files_scanned: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "repository": self.repository,
            "scan_timestamp": self.scan_timestamp,
            "security_score": self.security_score,
            "total_rules": self.total_rules,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "findings": self.findings,
            "findings_by_severity": self.findings_by_severity,
            "findings_by_category": self.findings_by_category,
            "files_scanned": self.files_scanned,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class DevSecOpsScanner:
    """
    DevSecOps Security Scanner.

    Scans repositories for security and reliability issues across:
    - Dockerfiles
    - Kubernetes manifests
    - Terraform configurations
    - CI/CD pipelines (GitHub Actions, GitLab CI)
    """

    def __init__(self, rules_registry=None):
        """
        Initialize the scanner.

        Args:
            rules_registry: Rule registry instance. If None, uses global registry.
        """
        from app.rules.base import registry as global_registry
        self.registry = rules_registry or global_registry
        self._findings: list[RuleFinding] = []
        self._files_scanned: list[str] = []
        self._parsed_resources: list[dict[str, Any]] = []

    def scan_repository(
        self,
        repo_path: str,
        repo_name: Optional[str] = None,
    ) -> ScanResult:
        """
        Scan a repository for security issues.

        Args:
            repo_path: Path to the repository
            repo_name: Optional repository name (defaults to path basename)

        Returns:
            ScanResult with all findings
        """
        repo_path = Path(repo_path)
        repo_name = repo_name or repo_path.name

        logger.info("Starting repository scan", repo_path=str(repo_path), repo_name=repo_name)

        # Reset state
        self._findings = []
        self._files_scanned = []
        self._parsed_resources = []

        # Scan different file types
        self._scan_dockerfiles(repo_path)
        self._scan_kubernetes(repo_path)
        self._scan_terraform(repo_path)
        self._scan_cicd(repo_path)

        # Calculate results
        result = self._calculate_results(repo_name)

        logger.info(
            "Repository scan completed",
            repo_name=repo_name,
            security_score=result.security_score,
            total_findings=len(result.findings),
        )

        return result

    def scan_file(self, file_path: str) -> ScanResult:
        """
        Scan a single file for security issues.

        Args:
            file_path: Path to the file

        Returns:
            ScanResult with findings
        """
        file_path = Path(file_path)

        logger.info("Starting file scan", file_path=str(file_path))

        # Reset state
        self._findings = []
        self._files_scanned = []
        self._parsed_resources = []

        # Determine file type and scan
        file_name = file_path.name.lower()
        if file_name == "dockerfile" or file_name.endswith(".dockerfile"):
            self._scan_dockerfile_file(file_path)
        elif file_name.endswith((".yaml", ".yml")):
            # Could be K8s or CI/CD
            content = file_path.read_text()
            if "kind:" in content:
                self._scan_kubernetes_file(file_path)
            elif "jobs:" in content or "steps:" in content or "workflow" in content:
                self._scan_cicd_file(file_path)
        elif file_name.endswith(".tf"):
            self._scan_terraform_file(file_path)

        result = self._calculate_results(file_path.name)
        return result

    def _scan_dockerfiles(self, repo_path: Path) -> None:
        """Scan all Dockerfiles in repository."""
        dockerfile_patterns = [
            "Dockerfile",
            "Dockerfile.*",
            "*.dockerfile",
            "docker/Dockerfile",
            "dockerfiles/Dockerfile",
        ]

        for pattern in dockerfile_patterns:
            for file_path in repo_path.glob(pattern):
                if file_path.is_file():
                    self._scan_dockerfile_file(file_path)

    def _scan_dockerfile_file(self, file_path: Path) -> None:
        """Scan a single Dockerfile."""
        from app.parsers.dockerfile import parse_dockerfile

        try:
            content = file_path.read_text()
            relative_path = str(file_path)

            resources = parse_dockerfile(content, relative_path)
            self._parsed_resources.extend(resources)
            self._files_scanned.append(relative_path)

            # Run rules
            findings = self.registry.evaluate_all(resources, relative_path, file_type="dockerfile")
            self._findings.extend(findings)

            logger.debug("Dockerfile scanned", file=relative_path, findings=len(findings))
        except Exception as e:
            logger.error("Failed to scan Dockerfile", file=str(file_path), error=str(e))

    def _scan_kubernetes(self, repo_path: Path) -> None:
        """Scan all Kubernetes manifests in repository."""
        k8s_patterns = [
            "k8s/**/*.yaml",
            "k8s/**/*.yml",
            "kubernetes/**/*.yaml",
            "kubernetes/**/*.yml",
            "manifests/**/*.yaml",
            "manifests/**/*.yml",
            "deploy/**/*.yaml",
            "deploy/**/*.yml",
            "charts/**/*.yaml",
            "charts/**/*.yml",
            "*.yaml",
            "*.yml",
        ]

        for pattern in k8s_patterns:
            for file_path in repo_path.glob(pattern):
                if file_path.is_file() and self._is_kubernetes_file(file_path):
                    self._scan_kubernetes_file(file_path)

    def _is_kubernetes_file(self, file_path: Path) -> bool:
        """Check if file is a Kubernetes manifest."""
        try:
            content = file_path.read_text()
            return "apiVersion:" in content and "kind:" in content
        except Exception:
            return False

    def _scan_kubernetes_file(self, file_path: Path) -> None:
        """Scan a single Kubernetes manifest."""
        from app.parsers.kubernetes import parse_kubernetes_manifest

        try:
            content = file_path.read_text()
            relative_path = str(file_path)

            resources = parse_kubernetes_manifest(content, relative_path)
            self._parsed_resources.extend(resources)
            self._files_scanned.append(relative_path)

            # Run rules
            findings = self.registry.evaluate_all(resources, relative_path, file_type="kubernetes")
            self._findings.extend(findings)

            logger.debug("Kubernetes manifest scanned", file=relative_path, findings=len(findings))
        except Exception as e:
            logger.error("Failed to scan Kubernetes manifest", file=str(file_path), error=str(e))

    def _scan_terraform(self, repo_path: Path) -> None:
        """Scan all Terraform files in repository."""
        tf_patterns = [
            "**/*.tf",
            "**/*.tf.json",
        ]

        for pattern in tf_patterns:
            for file_path in repo_path.glob(pattern):
                if file_path.is_file():
                    self._scan_terraform_file(file_path)

    def _scan_terraform_file(self, file_path: Path) -> None:
        """Scan a single Terraform file."""
        from app.parsers.terraform import parse_terraform

        try:
            content = file_path.read_text()
            relative_path = str(file_path)

            resources = parse_terraform(content, relative_path)
            self._parsed_resources.extend(resources)
            self._files_scanned.append(relative_path)

            # Run rules
            findings = self.registry.evaluate_all(resources, relative_path, file_type="terraform")
            self._findings.extend(findings)

            logger.debug("Terraform file scanned", file=relative_path, findings=len(findings))
        except Exception as e:
            logger.error("Failed to scan Terraform file", file=str(file_path), error=str(e))

    def _scan_cicd(self, repo_path: Path) -> None:
        """Scan all CI/CD pipeline files in repository."""
        cicd_patterns = [
            ".github/workflows/**/*.yaml",
            ".github/workflows/**/*.yml",
            ".gitlab-ci.yml",
            ".gitlab-ci.yaml",
            "azure-pipelines.yml",
            "azure-pipelines.yaml",
            ".circleci/config.yml",
            ".travis.yml",
            "Jenkinsfile",
            "bitbucket-pipelines.yml",
        ]

        for pattern in cicd_patterns:
            for file_path in repo_path.glob(pattern):
                if file_path.is_file():
                    self._scan_cicd_file(file_path)

    def _scan_cicd_file(self, file_path: Path) -> None:
        """Scan a single CI/CD file."""
        from app.parsers.cicd import parse_cicd_pipeline

        try:
            content = file_path.read_text()
            relative_path = str(file_path)
            file_name = file_path.name.lower()

            # Determine CI/CD type
            cicd_type = "github_actions"
            if "gitlab" in file_name:
                cicd_type = "gitlab_ci"
            elif "azure" in file_name:
                cicd_type = "azure_pipelines"
            elif "circle" in file_name:
                cicd_type = "circleci"
            elif "jenkins" in file_name.lower():
                cicd_type = "jenkins"

            resources = parse_cicd_pipeline(content, relative_path, cicd_type)
            self._parsed_resources.extend(resources)
            self._files_scanned.append(relative_path)

            # Check if terraform exists in repo for CI/CD rules
            has_terraform = len(list(repo_path.glob("**/*.tf"))) > 0

            # Run rules
            findings = self.registry.evaluate_all(
                resources, relative_path, file_type="cicd", has_terraform=has_terraform
            )
            self._findings.extend(findings)

            logger.debug("CI/CD pipeline scanned", file=relative_path, findings=len(findings))
        except Exception as e:
            logger.error("Failed to scan CI/CD pipeline", file=str(file_path), error=str(e))

    def _calculate_results(self, repo_name: str) -> ScanResult:
        """Calculate scan results from findings."""
        # Count findings by severity
        findings_by_severity = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }

        findings_by_category = {
            "security": 0,
            "reliability": 0,
            "scalability": 0,
            "observability": 0,
            "cost": 0,
        }

        findings_list = []

        for finding in self._findings:
            severity = finding.severity.value
            category = finding.category.value

            findings_by_severity[severity] = findings_by_severity.get(severity, 0) + 1
            findings_by_category[category] = findings_by_category.get(category, 0) + 1

            findings_list.append(finding.to_dict())

        # Calculate security score (0-100)
        total_rules = RULE_COUNTS["total"]
        critical_weight = 10
        high_weight = 5
        medium_weight = 2
        low_weight = 1

        penalty = (
            findings_by_severity["critical"] * critical_weight +
            findings_by_severity["high"] * high_weight +
            findings_by_severity["medium"] * medium_weight +
            findings_by_severity["low"] * low_weight
        )

        # Max possible penalty
        max_penalty = total_rules * critical_weight

        # Score calculation
        security_score = max(0, 100 - int((penalty / max_penalty) * 100))

        # Count unique rules that failed
        failed_rule_ids = set(f.rule_id for f in self._findings)
        rules_failed = len(failed_rule_ids)
        rules_passed = total_rules - rules_failed

        return ScanResult(
            repository=repo_name,
            scan_timestamp=datetime.utcnow().isoformat() + "Z",
            security_score=security_score,
            total_rules=total_rules,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            findings=findings_list,
            findings_by_severity=findings_by_severity,
            findings_by_category=findings_by_category,
            files_scanned=self._files_scanned,
            metadata={
                "parsed_resources": len(self._parsed_resources),
                "rule_counts": RULE_COUNTS,
            },
        )


def scan_repository(repo_path: str, repo_name: Optional[str] = None) -> dict[str, Any]:
    """
    Convenience function to scan a repository.

    Args:
        repo_path: Path to the repository
        repo_name: Optional repository name

    Returns:
        Dictionary with scan results
    """
    scanner = DevSecOpsScanner()
    result = scanner.scan_repository(repo_path, repo_name)
    return result.to_dict()


def scan_file(file_path: str) -> dict[str, Any]:
    """
    Convenience function to scan a single file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with scan results
    """
    scanner = DevSecOpsScanner()
    result = scanner.scan_file(file_path)
    return result.to_dict()
