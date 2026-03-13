"""
Terraform Analysis Rules
"""

import re
from typing import Any

from app.rules.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule
class TerraformNoRemoteStateRule(BaseRule):
    """Check if Terraform has remote backend configured."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="terraform_no_remote_state",
            name="No Remote State Backend",
            description="Terraform state is stored locally instead of remote backend, risking state loss and collaboration issues",
            recommendation="Configure remote backend (e.g., S3, GCS, Azure Blob) for state storage with locking",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["terraform", "backend", "state"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        # Only evaluate this rule for Terraform files
        if not file_path.endswith(('.tf', '.tf.json')):
            return findings

        has_backend = False
        backend_files: list[str] = []

        for resource in resources:
            if resource.get("file_type") != "terraform":
                continue
            if resource.get("resource_type") == "backend":
                properties = resource.get("properties", {})
                # Check if it's a remote backend
                if properties.get("has_remote_state", False):
                    has_backend = True
                    backend_files.append(file_path)
                    break

        # Only report finding if this is a Terraform file and no backend found
        if not has_backend:
            findings.append(RuleFinding(
                rule_id=self.rule.id,
                rule_name=self.rule.name,
                severity=self.rule.severity,
                category=self.rule.category,
                description=self.rule.description,
                recommendation=self.rule.recommendation,
                file_path=file_path,
                metadata={"affected_files": [file_path]},
            ))

        return findings


@register_rule
class TerraformStateLockingRule(BaseRule):
    """Check if Terraform backend has state locking configured."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="terraform_state_locking",
            name="State Locking Not Configured",
            description="Terraform backend does not have state locking enabled, risking state corruption from concurrent operations",
            recommendation="Enable state locking: for S3 add 'dynamodb_table' or 'use_lockfile = true'; other backends have built-in locking",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["terraform", "backend", "locking", "state"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "terraform":
                continue
            if resource.get("resource_type") != "backend":
                continue

            properties = resource.get("properties", {})
            backend_type = properties.get("type", "").lower()
            has_locking = properties.get("has_locking", False)
            has_remote_state = properties.get("has_remote_state", False)

            # Only check locking for remote backends
            if not has_remote_state:
                continue

            # Skip backends with built-in locking (gcs, azurerm, consul, remote, pg)
            built_in_locking_backends = {"gcs", "azurerm", "consul", "remote", "pg", "etcdv3"}
            if backend_type in built_in_locking_backends:
                continue

            # For S3 backend, check for locking configuration
            if backend_type == "s3" and not has_locking:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description="S3 backend does not have state locking configured. Add 'dynamodb_table' or 'use_lockfile = true'",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={
                        "backend_type": backend_type,
                        "raw_config": properties.get("raw_config", ""),
                    },
                ))
            # For HTTP backend (no locking support)
            elif backend_type == "http":
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description="HTTP backend does not support state locking. Consider using S3, GCS, or Terraform Cloud",
                    recommendation="Migrate to a backend with built-in locking support",
                    file_path=file_path,
                    metadata={"backend_type": backend_type},
                ))

        return findings


@register_rule
class TerraformOpenSecurityGroupRule(BaseRule):
    """Check for overly permissive security group rules."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="terraform_open_security_group",
            name="Security Group Allows 0.0.0.0/0",
            description="Security group allows unrestricted inbound access from the internet",
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
class TerraformNoEncryptionRule(BaseRule):
    """Check for unencrypted S3 buckets or storage."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="terraform_no_encryption",
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
            # Use the encryption field from parser
            if not resource_data.get("encryption", False):
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
class TerraformNoVersionPinningRule(BaseRule):
    """Check if Terraform providers have version pinning."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="terraform_no_version_pinning",
            name="Provider Version Not Pinned",
            description="Terraform provider version is not pinned, risking breaking changes",
            recommendation="Pin provider versions using version constraints (e.g., ~> 4.0)",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["terraform", "provider", "versioning"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "terraform":
                continue
            if resource.get("resource_type") != "provider":
                continue

            provider_data = resource.get("properties", {})
            raw_config = provider_data.get("raw_config", "")

            # Check for version constraint
            if "version" not in raw_config.lower():
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=provider_data.get("name"),
                ))

        return findings


@register_rule
class TerraformNoTagsRule(BaseRule):
    """Check if Terraform resources have tags."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="terraform_no_tags",
            name="Resources Missing Tags",
            description="Terraform resources do not have tags for organization and cost tracking",
            recommendation="Add standard tags (e.g., Environment, Owner, Project) to all resources",
            severity=Severity.LOW,
            category=Category.COST,
            tags=["terraform", "tags", "governance"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "terraform":
                continue
            if resource.get("resource_type") in ["backend", "provider"]:
                continue

            resource_data = resource.get("properties", {})
            if not resource_data.get("has_tags"):
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
class TerraformHardcodedSecretsRule(BaseRule):
    """Check for hardcoded secrets in Terraform."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="terraform_hardcoded_secrets",
            name="Hardcoded Secrets Detected",
            description="Potential secrets are hardcoded in Terraform configuration",
            recommendation="Use AWS Secrets Manager, HashiCorp Vault, or environment variables for secrets",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["terraform", "secrets", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        secret_patterns = [
            r'password\s*=\s*"[^"]+"',
            r'secret\s*=\s*"[^"]+"',
            r'api_key\s*=\s*"[^"]+"',
            r'token\s*=\s*"[^"]+"',
            r'credential\s*=\s*"[^"]+"',
        ]

        for resource in resources:
            if resource.get("file_type") != "terraform":
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource_data.get("raw_body", "")

            for pattern in secret_patterns:
                if re.search(pattern, raw_body, re.IGNORECASE):
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
                    break

        return findings


@register_rule
class TerraformNoLoggingRule(BaseRule):
    """Check if cloud resources have logging enabled."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="terraform_no_logging",
            name="Missing Logging Configuration",
            description="Cloud resource does not have logging enabled for audit and troubleshooting",
            recommendation="Enable logging and monitoring for all critical resources",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["terraform", "logging", "observability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        logging_resources = ["aws_s3_bucket", "aws_lambda_function", "aws_api_gateway", "aws_ecs_service"]

        for resource in resources:
            resource_type = resource.get("resource_type")
            if resource_type not in logging_resources:
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource_data.get("raw_body", "")

            # Check for logging configuration
            has_logging = any(keyword in raw_body.lower() for keyword in [
                "logging", "access_log", "cloudwatch", "log_group", "audit"
            ])

            if not has_logging:
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
class TerraformNoLifecycleRule(BaseRule):
    """Check if Terraform resources have lifecycle rules."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="terraform_no_lifecycle",
            name="Missing Lifecycle Configuration",
            description="Resource does not have lifecycle configuration for safe updates",
            recommendation="Add lifecycle block with create_before_destroy or prevent_destroy as appropriate",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["terraform", "lifecycle", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "terraform":
                continue
            if resource.get("resource_type") in ["backend", "provider"]:
                continue

            resource_data = resource.get("properties", {})
            if not resource_data.get("has_lifecycle"):
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
