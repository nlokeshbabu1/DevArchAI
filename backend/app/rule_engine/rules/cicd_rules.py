"""CI/CD rules for infrastructure analysis."""

from typing import Any

from app.rule_engine.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule(file_types=["cicd"])
class CICDMissingSecurityScanningRule(BaseRule):
    """Check for missing security scanning in CI/CD."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-001",
            name="Missing Security Scanning",
            description="CI/CD pipeline does not include security scanning steps",
            recommendation="Add security scanning steps (SAST, DAST, dependency scanning) to your pipeline",
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

            # Check for security-related steps
            security_keywords = [
                "security", "scan", "sast", "dast", "trivy", "sonarqube",
                "snyk", "dependabot", "gitleaks", "semgrep"
            ]

            has_security_scan = False
            for job in jobs:
                job_str = str(job).lower()
                if any(keyword in job_str for keyword in security_keywords):
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


@register_rule(file_types=["cicd"])
class CICDMissingContainerScanningRule(BaseRule):
    """Check for missing container scanning in CI/CD."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-002",
            name="Missing Container Scanning",
            description="CI/CD pipeline does not scan container images for vulnerabilities",
            recommendation="Add container image scanning (Trivy, Clair, Docker Scan) to your pipeline",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["cicd", "security", "container", "scanning"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            jobs = properties.get("jobs", [])

            # Check for container scanning steps
            container_scan_keywords = [
                "trivy", "clair", "docker scan", "grype", "anchore",
                "container scan", "image scan"
            ]

            has_container_scan = False
            for job in jobs:
                job_str = str(job).lower()
                if any(keyword in job_str for keyword in container_scan_keywords):
                    has_container_scan = True
                    break

            # Check if pipeline builds containers
            builds_containers = any(
                "docker build" in str(job).lower() or
                "buildx" in str(job).lower()
                for job in jobs
            )

            if builds_containers and not has_container_scan:
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


@register_rule(file_types=["cicd"])
class CICDMissingOIDCRule(BaseRule):
    """Check for missing OIDC authentication in CI/CD cloud deployments."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SEC-003",
            name="Missing OIDC Authentication",
            description="CI/CD pipeline uses cloud provider authentication without OIDC",
            recommendation="Use OIDC authentication instead of long-lived credentials (AWS IAM Roles Anywhere, Azure Federated Identity, GCP Workload Identity)",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["cicd", "security", "authentication", "cloud"],
        )

    def _uses_cloud_provider(self, resource: dict) -> bool:
        """Check if workflow interacts with cloud providers."""
        raw_content = str(resource.get("raw_content", "")).lower()
        jobs = resource.get("properties", {}).get("jobs", [])
        jobs_str = str(jobs).lower()

        # AWS indicators
        aws_indicators = [
            "aws-actions/configure-aws-credentials",
            "aws-actions/aws-cloudformation-github-deploy",
            "aws-actions/amazon-ecs",
            "aws-actions/amazon-ecr",
            "aws s3", "aws ec2", "aws lambda", "aws cloudformation",
            "aws_cli", "amazon aws",
        ]

        # Azure indicators
        azure_indicators = [
            "azure/login", "az login", "azure/cli",
            "azure/webapps-deploy", "azure/container-apps-deploy",
            "azure resource", "azurerm",
        ]

        # GCP indicators
        gcp_indicators = [
            "google-github-actions/auth", "google-github-actions/deploy-appengine",
            "gcloud auth", "gcloud deploy", "gcloud container",
            "google cloud", "gcp_",
        ]

        all_content = raw_content + " " + jobs_str

        # Check for any cloud provider usage
        for indicator in aws_indicators + azure_indicators + gcp_indicators:
            if indicator in all_content:
                return True

        return False

    def _has_oidc_permissions(self, resource: dict) -> bool:
        """Check if workflow has OIDC permissions configured."""
        raw_content = str(resource.get("raw_content", ""))

        # Check for id-token: write permissions
        has_id_token = (
            "id-token: write" in raw_content or
            "id-token:write" in raw_content or
            '"id-token": "write"' in raw_content or
            "'id-token': 'write'" in raw_content
        )

        # Check for AWS credentials action usage
        has_aws_credentials = "aws-actions/configure-aws-credentials" in raw_content

        # OIDC is properly configured if BOTH exist
        return has_id_token and has_aws_credentials

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            # Only check if workflow uses cloud providers
            if not self._uses_cloud_provider(resource):
                continue

            # OIDC passes if BOTH conditions are met:
            # 1. Has id-token: write permissions
            # 2. Uses aws-actions/configure-aws-credentials
            if self._has_oidc_permissions(resource):
                continue

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


@register_rule(file_types=["cicd"])
class CICDMissingCachingRule(BaseRule):
    """Check for missing artifact caching in CI/CD."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-SCALE-001",
            name="Missing Artifact Caching",
            description="CI/CD pipeline does not use caching for faster builds",
            recommendation="Configure caching for dependencies and build artifacts",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["cicd", "caching", "performance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            caching = properties.get("caching", [])

            if not caching:
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


@register_rule(file_types=["cicd"])
class CICDMissingApprovalRule(BaseRule):
    """Check for missing approval gates in CI/CD."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-REL-001",
            name="Missing Approval Gates",
            description="CI/CD pipeline does not have approval gates for production deployments",
            recommendation="Add manual approval gates for production deployments",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["cicd", "approval", "deployment"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            environments = properties.get("environments", [])

            # Check for environment protection
            has_protection = any(
                isinstance(env, dict) and env.get("protection_rules") or
                isinstance(env, str) and "prod" in env.lower()
                for env in environments
            )

            # Check for manual approval keywords
            jobs = properties.get("jobs", [])
            has_approval = any(
                "manual" in str(job).lower() or
                "approval" in str(job).lower() or
                "approve" in str(job).lower()
                for job in jobs
            )

            # Check if pipeline deploys to production
            deploys_to_prod = any(
                "prod" in str(job).lower() or
                "production" in str(job).lower()
                for job in jobs
            )

            if deploys_to_prod and not has_protection and not has_approval:
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


@register_rule(file_types=["cicd"])
class CICDMissingTestingRule(BaseRule):
    """Check for missing testing in CI/CD."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="CI-REL-002",
            name="Missing Testing",
            description="CI/CD pipeline does not include automated testing",
            recommendation="Add automated testing (unit, integration, E2E) to your pipeline",
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

            # Check for testing steps
            test_keywords = [
                "test", "pytest", "jest", "mocha", "rspec", "junit",
                "go test", "cargo test", "npm test", "yarn test"
            ]

            has_testing = False
            for job in jobs:
                job_str = str(job).lower()
                if any(keyword in job_str for keyword in test_keywords):
                    has_testing = True
                    break

            if not has_testing:
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
