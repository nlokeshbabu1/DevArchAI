"""
Security Rules for Infrastructure Analysis
"""

from typing import Any

from app.rules.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule
class TerraformStateLockingRule(BaseRule):
    """Check if Terraform state backend has locking enabled."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SEC-001",
            name="Missing State Locking",
            description="Terraform state backend does not have locking enabled, which can lead to state corruption",
            recommendation="Enable state locking using DynamoDB (for S3 backend) or use a backend that supports locking",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["terraform", "state", "locking"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "terraform":
                continue

            if resource.get("resource_type") == "backend":
                backend = resource.get("properties", {})
                if not backend.get("has_locking"):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=self.rule.description,
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        metadata={"backend_type": backend.get("type")},
                    ))

        return findings


@register_rule
class PublicSecurityGroupRule(BaseRule):
    """Check for overly permissive security group rules."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SEC-002",
            name="Public Security Group",
            description="Security group allows unrestricted inbound access from 0.0.0.0/0",
            recommendation="Restrict security group rules to specific IP ranges or use VPC endpoints",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["terraform", "aws", "security-group", "networking"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("resource_type") != "aws_security_group":
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource_data.get("raw_body", "")

            # Check for 0.0.0.0/0 in ingress rules
            if "0.0.0.0/0" in raw_body or "::/0" in raw_body:
                # Check if it's for a sensitive port
                sensitive_ports = ["22", "3389", "5432", "3306", "27017", "6379"]
                for port in sensitive_ports:
                    if f'from_port.*{port}' in raw_body or f'to_port.*{port}' in raw_body:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Security group allows unrestricted access on port {port}",
                            recommendation=f"Restrict access to port {port} to specific IP ranges",
                            file_path=file_path,
                            resource_name=resource_data.get("name"),
                            metadata={"port": port},
                        ))
                        break

        return findings


@register_rule
class DockerSecretInEnvRule(BaseRule):
    """Check for secrets exposed in Dockerfile ENV variables."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SEC-003",
            name="Secret in Dockerfile ENV",
            description="Potential secrets are exposed in Dockerfile ENV variables",
            recommendation="Use Docker secrets, build arguments, or runtime environment variables instead of hardcoding secrets",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["docker", "secrets", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            security_issues = resource.get("security_issues", [])
            for issue in security_issues:
                if issue.get("issue") == "secret_in_env":
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=Severity.CRITICAL,
                        category=self.rule.category,
                        description=issue.get("description", self.rule.description),
                        recommendation=issue.get("recommendation", self.rule.recommendation),
                        file_path=file_path,
                        line_number=issue.get("line_number"),
                    ))

        return findings


@register_rule
class DockerRootUserRule(BaseRule):
    """Check if Docker container runs as root."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SEC-004",
            name="Container Running as Root",
            description="Docker container runs as root user, increasing security risk",
            recommendation="Add USER instruction to run container as non-root user",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["docker", "security", "user"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            security_issues = resource.get("security_issues", [])
            for issue in security_issues:
                if issue.get("issue") == "running_as_root":
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=issue.get("description", self.rule.description),
                        recommendation=issue.get("recommendation", self.rule.recommendation),
                        file_path=file_path,
                    ))

        return findings


@register_rule
class K8sMissingNetworkPolicyRule(BaseRule):
    """Check for missing Kubernetes NetworkPolicies."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SEC-005",
            name="Missing Network Policies",
            description="No Kubernetes NetworkPolicies found, allowing unrestricted pod-to-pod communication",
            recommendation="Implement NetworkPolicies to restrict traffic between pods",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["kubernetes", "networking", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        # This rule checks across all files, so we track if any network policy exists
        # For simplicity, we check if this file has network policies
        has_network_policy = any(
            r.get("kind") == "NetworkPolicy"
            for r in resources
            if r.get("file_type") == "kubernetes"
        )

        has_deployment = any(
            r.get("kind") == "Deployment"
            for r in resources
            if r.get("file_type") == "kubernetes"
        )

        findings = []

        if has_deployment and not has_network_policy:
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
class K8sMissingPodSecurityContextRule(BaseRule):
    """Check for missing pod security contexts."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SEC-006",
            name="Missing Pod Security Context",
            description="Pods do not have security contexts configured",
            recommendation="Configure podSecurityContext and securityContext to enforce least privilege",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["kubernetes", "security", "pod"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                security_context = container.get("security_context", {})
                if not security_context:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' has no security context",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name")},
                    ))

        return findings


@register_rule
class TerraformUnencryptedStorageRule(BaseRule):
    """Check for unencrypted S3 buckets or storage."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SEC-007",
            name="Unencrypted Storage",
            description="S3 bucket or storage resource does not have encryption enabled",
            recommendation="Enable server-side encryption (SSE) for all storage resources",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["terraform", "aws", "s3", "encryption"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("resource_type") != "aws_s3_bucket":
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource_data.get("raw_body", "")

            # Check for encryption configuration
            if "server_side_encryption" not in raw_body.lower() and "sse" not in raw_body.lower():
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                ))

        return findings


@register_rule
class CICDMissingOIDCRule(BaseRule):
    """Check for missing OIDC authentication in CI/CD."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SEC-008",
            name="Missing OIDC Authentication",
            description="CI/CD pipeline does not use OIDC for cloud authentication",
            recommendation="Use OIDC authentication instead of long-lived credentials",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["cicd", "security", "authentication"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            properties = resource.get("properties", {})
            security_features = properties.get("security_features", {})

            if not security_features.get("uses_oidc"):
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
