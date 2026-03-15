"""
CI/CD Pipeline Analysis Rules
"""

from typing import Any

from app.rules.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule
class CICDNoSecurityScanRule(BaseRule):
    """Check for missing security scanning in CI/CD."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="cicd_no_security_scan",
            name="No Security Scanning Step",
            description="CI/CD pipeline does not include security scanning (SAST/DAST)",
            recommendation="Add security scanning steps using tools like Trivy, Snyk, or GitHub Advanced Security",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["cicd", "security", "scanning"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])

            security_tools = ["trivy", "snyk", "sonarqube", "semgrep", "gitleaks", "bandit", "safety", "zap", "security-scan"]
            has_security_scan = False

            for job in jobs:
                job_str = str(job).lower()
                if any(tool in job_str for tool in security_tools):
                    has_security_scan = True
                    break

            if not has_security_scan:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings


@register_rule
class CICDNoContainerScanRule(BaseRule):
    """Check for missing container image scanning."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="cicd_no_container_scan",
            name="No Container Image Scanning",
            description="CI/CD pipeline does not scan container images for vulnerabilities",
            recommendation="Add container scanning using Trivy, Snyk, Docker Scan, or Clair",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["cicd", "container", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])

            container_scan_tools = ["trivy", "snyk", "docker scan", "clair", "grype", "anchore"]
            has_container_scan = False

            for job in jobs:
                job_str = str(job).lower()
                if any(tool in job_str for tool in container_scan_tools):
                    has_container_scan = True
                    break

            if not has_container_scan:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings


@register_rule
class CICDNoTerraformValidationRule(BaseRule):
    """Check for missing Terraform validation."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="cicd_no_terraform_validation",
            name="No Terraform Validation",
            description="CI/CD pipeline does not validate Terraform configurations",
            recommendation="Add terraform fmt, terraform validate, and tflint steps",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["cicd", "terraform", "validation"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])

            terraform_commands = ["terraform fmt", "terraform validate", "tflint", "tfsec", "checkov", "terrascan"]
            has_terraform_validation = False

            for job in jobs:
                job_str = str(job).lower()
                if any(cmd in job_str for cmd in terraform_commands):
                    has_terraform_validation = True
                    break

            if not has_terraform_validation:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings


@register_rule
class CICDNoDependencyScanRule(BaseRule):
    """Check for missing dependency scanning."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="cicd_no_dependency_scan",
            name="No Dependency Scanning",
            description="CI/CD pipeline does not scan dependencies for vulnerabilities",
            recommendation="Add dependency scanning using npm audit, pip-audit, dependabot, or renovate",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["cicd", "dependencies", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])

            dependency_tools = ["npm audit", "yarn audit", "pip-audit", "safety", "dependabot", "renovate", "owasp dependency-check"]
            has_dependency_scan = False

            for job in jobs:
                job_str = str(job).lower()
                if any(tool in job_str for tool in dependency_tools):
                    has_dependency_scan = True
                    break

            if not has_dependency_scan:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings


@register_rule
class CICDNoBuildCacheRule(BaseRule):
    """Check for missing build caching."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="cicd_no_build_cache",
            name="No Build Caching",
            description="CI/CD pipeline does not use caching, resulting in slower builds",
            recommendation="Configure caching for dependencies and build artifacts",
            severity=Severity.LOW,
            category=Category.COST,
            tags=["cicd", "cache", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})

            # Check for caching configuration
            caching = properties.get("caching", [])
            has_cache = len(caching) > 0

            # Also check jobs for cache actions
            if not has_cache:
                jobs = properties.get("jobs", [])
                for job in jobs:
                    job_str = str(job).lower()
                    if "cache" in job_str or "actions/cache" in job_str:
                        has_cache = True
                        break

            if not has_cache:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings


@register_rule
class CICDNoTestStageRule(BaseRule):
    """Check for missing test stage."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="cicd_no_test_stage",
            name="Missing Test Stage",
            description="CI/CD pipeline does not include automated testing",
            recommendation="Add test stages with unit, integration, and end-to-end tests",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["cicd", "testing", "quality"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])
            stages = properties.get("stages", [])

            test_keywords = ["test", "spec", "pytest", "jest", "mocha", "junit", "go test", "cargo test", "mvn test"]
            has_test = False

            # Check stages
            for stage in stages:
                if "test" in str(stage).lower():
                    has_test = True
                    break

            # Check jobs
            if not has_test:
                for job in jobs:
                    job_str = str(job).lower()
                    job_name = str(job.get("name", "")).lower()
                    if any(keyword in job_str or keyword in job_name for keyword in test_keywords):
                        has_test = True
                        break

            if not has_test:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings


@register_rule
class CICDNoArtifactStorageRule(BaseRule):
    """Check for missing artifact storage."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="cicd_no_artifact_storage",
            name="No Artifact Storage",
            description="CI/CD pipeline does not store build artifacts",
            recommendation="Configure artifact storage using GitHub Actions artifacts, S3, or artifact registries",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["cicd", "artifacts", "storage"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            artifacts = properties.get("artifacts", [])

            has_artifacts = len(artifacts) > 0

            if not has_artifacts:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings


@register_rule
class CICDNoEnvironmentProtectionRule(BaseRule):
    """Check for missing environment protection."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="cicd_no_environment_protection",
            name="No Environment Protection Rules",
            description="CI/CD pipeline does not use environment protection rules for deployments",
            recommendation="Configure environment protection rules with required reviewers for production",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["cicd", "environment", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            security_features = properties.get("security_features", {})

            has_environment_protection = security_features.get("has_environment_protection", False)

            if not has_environment_protection:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings


@register_rule
class CICDNoRollbackStrategyRule(BaseRule):
    """Check for missing rollback strategy."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="cicd_no_rollback_strategy",
            name="No Rollback Strategy",
            description="CI/CD pipeline does not have a defined rollback strategy",
            recommendation="Implement blue-green or canary deployments with automatic rollback capabilities",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["cicd", "rollback", "deployment"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])

            rollback_keywords = ["rollback", "blue-green", "canary", "progressive", "staged", "manual approval"]
            has_rollback = False

            for job in jobs:
                job_str = str(job).lower()
                if any(keyword in job_str for keyword in rollback_keywords):
                    has_rollback = True
                    break

            if not has_rollback:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                ))

        return findings
