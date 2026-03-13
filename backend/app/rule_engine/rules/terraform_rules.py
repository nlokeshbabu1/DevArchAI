"""Terraform rules for infrastructure analysis."""

import re
from typing import Any

from app.rule_engine.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule

# =============================================================================
# STATE MANAGEMENT RULES
# =============================================================================

@register_rule(file_types=["terraform"])
class TerraformLocalBackendRule(BaseRule):
    """Check if Terraform uses local backend (not allowed in production)."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-STATE-001",
            name="Local Backend Not Allowed",
            description="Terraform is configured to use local backend, which prevents collaboration and risks state loss",
            recommendation="Configure remote backend (S3, GCS, Azure Blob, Terraform Cloud) for production use",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            tags=["terraform", "backend", "state", "production"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("resource_type") == "backend":
                backend = resource.get("properties", {})
                backend_type = backend.get("type", "").lower()

                # Only check files that actually have a backend block
                if not backend_type:
                    continue

                # Local backend is not allowed
                if backend_type == "local":
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=self.rule.description,
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        metadata={"backend_type": backend_type},
                        risk="Terraform state stored locally cannot be shared across team members or CI/CD pipelines, leading to state drift, failed applies, and potential infrastructure corruption.",
                        impact="Multiple engineers running terraform apply simultaneously can corrupt state, causing infrastructure drift and deployment failures.",
                        fix_example='''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
                    ))

        return findings


@register_rule(file_types=["terraform"])
class TerraformRemoteBackendRequiredRule(BaseRule):
    """Check if Terraform has remote backend configured per module."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-STATE-002",
            name="Remote Backend Required",
            description="Terraform module does not have a remote backend configured, risking state loss and collaboration issues",
            recommendation="Configure remote backend (S3, GCS, Azure Blob, Consul, Terraform Cloud) with state locking",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["terraform", "backend", "state", "remote", "module"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        # This rule is now handled at module level in scan_service
        # Return empty - module-level check will handle it
        return []


@register_rule(file_types=["terraform"])
class TerraformStateLockingRule(BaseRule):
    """Check if Terraform state backend has locking enabled."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-STATE-003",
            name="Missing State Locking",
            description="Terraform state backend does not have locking enabled, which can lead to state corruption",
            recommendation="Enable state locking: for S3 add 'dynamodb_table' or 'use_lockfile = true' (Terraform 1.10+)",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            tags=["terraform", "state", "locking"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("resource_type") == "backend":
                backend = resource.get("properties", {})
                backend_type = backend.get("type", "unknown").lower()

                # Skip local backends (already caught by TF-STATE-001)
                if backend_type in ("local", ""):
                    continue

                # Skip backends with built-in locking
                builtin_locking = {"gcs", "azurerm", "consul", "remote", "pg", "etcdv3"}
                if backend_type in builtin_locking:
                    continue

                if not backend.get("has_locking", False):
                    if backend_type == "s3":
                        recommendation = "Add 'dynamodb_table' for team/CI environments or 'use_lockfile = true' (Terraform 1.10+)"
                    else:
                        recommendation = self.rule.recommendation

                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=self.rule.description,
                        recommendation=recommendation,
                        file_path=file_path,
                        metadata={"backend_type": backend_type},
                    ))

        return findings


@register_rule(file_types=["terraform"])
class TerraformBackendEncryptionRule(BaseRule):
    """Check if Terraform backend has encryption enabled for state."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-STATE-004",
            name="Backend State Encryption Required",
            description="Terraform backend does not have encryption enabled for state storage",
            recommendation="Enable encryption: for S3 add 'encrypt = true', for GCS encryption is automatic, for Azure use 'encrypt = true'",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["terraform", "backend", "encryption", "state"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("resource_type") == "backend":
                backend = resource.get("properties", {})
                backend_type = backend.get("type", "").lower()
                raw_config = backend.get("raw_config", "")

                # S3 backend must have encrypt = true
                if backend_type == "s3":
                    if "encrypt" not in raw_config or "encrypt = true" not in raw_config:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description="S3 backend does not have encryption enabled",
                            recommendation="Add 'encrypt = true' to S3 backend configuration",
                            file_path=file_path,
                            metadata={"backend_type": backend_type},
                        ))

                # COS backend (Tencent) should have encryption
                elif backend_type == "cos":
                    if "encrypt" not in raw_config:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=Severity.MEDIUM,
                            category=self.rule.category,
                            description="COS backend does not explicitly enable encryption",
                            recommendation="Add 'encrypt = true' to COS backend configuration",
                            file_path=file_path,
                            metadata={"backend_type": backend_type},
                        ))

        return findings


# =============================================================================
# PROVIDER CONFIGURATION RULES
# =============================================================================

@register_rule(file_types=["terraform"])
class TerraformProviderVersionPinningRule(BaseRule):
    """Check if Terraform providers have version pinning."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-PROV-001",
            name="Provider Version Not Pinned",
            description="Terraform provider version is not pinned, risking breaking changes from upstream updates",
            recommendation="Pin provider versions using version constraints (e.g., version = \"~> 5.0\" or version = \">= 4.0, < 6.0\")",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["terraform", "provider", "versioning"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("resource_type") == "provider":
                provider = resource.get("properties", {})
                raw_config = provider.get("raw_config", "")

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
                        resource_name=provider.get("name"),
                        metadata={"provider_name": provider.get("name")},
                    ))

        return findings


@register_rule(file_types=["terraform"])
class TerraformTrustedProviderSourceRule(BaseRule):
    """Check if Terraform providers are from trusted sources."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-PROV-002",
            name="Untrusted Provider Source",
            description="Terraform provider is from an untrusted or unofficial source",
            recommendation="Use only official providers from the HashiCorp registry (hashicorp/*) or verified organization sources",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["terraform", "provider", "security", "supply-chain"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        # Trusted provider sources
        trusted_sources = [
            "hashicorp/",
            "terraform-providers/",
        ]

        for resource in resources:
            if resource.get("resource_type") == "provider":
                provider = resource.get("properties", {})
                raw_config = provider.get("raw_config", "")
                provider_name = provider.get("name", "")

                # Check for explicit source in required_providers or provider block
                has_trusted_source = False

                for trusted in trusted_sources:
                    if trusted in raw_config:
                        has_trusted_source = True
                        break

                # If no explicit source, check if it's a well-known provider
                if not has_trusted_source:
                    # Default providers without explicit source are assumed hashicorp
                    well_known = ["aws", "azurerm", "google", "kubernetes", "helm", "random", "null", "local", "template"]
                    if provider_name.lower() in well_known:
                        has_trusted_source = True

                if not has_trusted_source:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Provider '{provider_name}' may be from an untrusted source",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=provider_name,
                        metadata={"provider_name": provider_name},
                    ))

        return findings


# =============================================================================
# SECRETS DETECTION RULES
# =============================================================================

@register_rule(file_types=["terraform"])
class TerraformHardcodedSecretsRule(BaseRule):
    """Check for hardcoded secrets in Terraform configurations."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-SEC-001",
            name="Hardcoded Secrets Detected",
            description="Potential secrets are hardcoded in Terraform configuration files",
            recommendation="Use AWS Secrets Manager, HashiCorp Vault, environment variables, or terraform.tfvars (gitignored) for secrets",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["terraform", "secrets", "security", "credentials"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        secret_patterns = [
            (r'password\s*=\s*"[^"]+"', "password"),
            (r'password\s*=\s*\'[^\']+\'', "password"),
            (r'secret\s*=\s*"[^"]+"', "secret"),
            (r'secret_key\s*=\s*"[^"]+"', "secret_key"),
            (r'api_key\s*=\s*"[^"]+"', "api_key"),
            (r'apikey\s*=\s*"[^"]+"', "apikey"),
            (r'token\s*=\s*"[^"]+"', "token"),
            (r'access_token\s*=\s*"[^"]+"', "access_token"),
            (r'auth_token\s*=\s*"[^"]+"', "auth_token"),
            (r'credential\s*=\s*"[^"]+"', "credential"),
            (r'private_key\s*=\s*"[^"]+"', "private_key"),
            (r'aws_secret_access_key\s*=\s*"[^"]+"', "aws_secret_access_key"),
        ]

        for resource in resources:
            if resource.get("file_type") != "terraform":
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource_data.get("raw_body", "")
            raw_config = resource_data.get("raw_config", "")

            # Combine all raw content for checking
            all_content = f"{raw_body} {raw_config}"

            for pattern, secret_type in secret_patterns:
                if re.search(pattern, all_content, re.IGNORECASE):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Hardcoded {secret_type} detected in configuration",
                        recommendation="Remove the secret and use a secrets manager or variable reference instead",
                        file_path=file_path,
                        resource_name=resource_data.get("name"),
                        metadata={"secret_type": secret_type},
                    ))
                    break  # Only report once per resource

        return findings


# =============================================================================
# ENCRYPTION RULES
# =============================================================================

@register_rule(file_types=["terraform"])
class TerraformS3EncryptionRule(BaseRule):
    """Check for S3 bucket encryption."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-ENC-001",
            name="S3 Bucket Encryption Required",
            description="S3 bucket does not have server-side encryption enabled",
            recommendation="Enable server-side encryption using SSE-S3, SSE-KMS, or SSE-C",
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
            raw_body = resource_data.get("raw_body", "").lower()

            # Check for encryption configuration
            has_encryption = (
                "server_side_encryption" in raw_body or
                "sse" in raw_body or
                "bucket_key_enabled" in raw_body or
                "kms_master_key_id" in raw_body
            )

            if not has_encryption:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                    metadata={"bucket_name": resource_data.get("name")},
                ))

        return findings


@register_rule(file_types=["terraform"])
class TerraformEBSEncryptionRule(BaseRule):
    """Check for EBS volume encryption."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-ENC-002",
            name="EBS Encryption Required",
            description="EBS volume or instance does not have encryption enabled",
            recommendation="Enable EBS encryption by setting 'encrypted = true' on volumes and launch templates",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["terraform", "aws", "ebs", "ec2", "encryption"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        ebs_resource_types = ["aws_ebs_volume", "aws_instance", "aws_launch_template", "aws_ami"]

        for resource in resources:
            resource_type = resource.get("resource_type", "")
            if resource_type not in ebs_resource_types:
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource.get("properties", {}).get("raw_body", "").lower()

            # Check for encryption
            has_encryption = (
                "encrypted" in raw_body and "encrypted = true" in raw_body or
                "encrypted =true" in raw_body
            )

            # For aws_ebs_volume, encryption is required
            if resource_type == "aws_ebs_volume" and not has_encryption:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description="EBS volume does not have encryption enabled",
                    recommendation="Add 'encrypted = true' to the EBS volume configuration",
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                ))

            # For instances, check root_block_device or ebs_block_device
            elif resource_type == "aws_instance":
                if "root_block_device" in raw_body and "encrypted" not in raw_body:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description="EC2 instance root block device does not have encryption enabled",
                        recommendation="Add 'encrypted = true' to root_block_device configuration",
                        file_path=file_path,
                        resource_name=resource_data.get("name"),
                    ))

        return findings


@register_rule(file_types=["terraform"])
class TerraformDatabaseEncryptionRule(BaseRule):
    """Check for database encryption."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-ENC-003",
            name="Database Encryption Required",
            description="Database instance does not have encryption at rest enabled",
            recommendation="Enable storage encryption using 'storage_encrypted = true' and specify KMS key",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["terraform", "aws", "rds", "database", "encryption"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        db_resource_types = ["aws_db_instance", "aws_rds_cluster", "aws_docdb_cluster"]

        for resource in resources:
            resource_type = resource.get("resource_type", "")
            if resource_type not in db_resource_types:
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource.get("properties", {}).get("raw_body", "").lower()

            has_encryption = (
                "storage_encrypted" in raw_body and "storage_encrypted = true" in raw_body or
                "storage_encrypted =true" in raw_body
            )

            if not has_encryption:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=f"{resource_type} does not have storage encryption enabled",
                    recommendation="Add 'storage_encrypted = true' and 'kms_key_id' to the database configuration",
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                    metadata={"resource_type": resource_type},
                ))

        return findings


# =============================================================================
# NETWORKING RULES
# =============================================================================

@register_rule(file_types=["terraform"])
class TerraformOpenSecurityGroupRule(BaseRule):
    """Check for overly permissive security group rules."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-NET-001",
            name="Security Group Allows 0.0.0.0/0",
            description="Security group allows unrestricted inbound access from the internet (0.0.0.0/0 or ::/0)",
            recommendation="Restrict security group rules to specific IP ranges, VPC CIDR, or use VPC endpoints",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["terraform", "aws", "security-group", "networking"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        sensitive_ports = {
            "22": "SSH",
            "3389": "RDP",
            "5432": "PostgreSQL",
            "3306": "MySQL",
            "27017": "MongoDB",
            "6379": "Redis",
            "1433": "MSSQL",
            "11211": "Memcached",
            "9200": "Elasticsearch",
            "9300": "Elasticsearch",
        }

        for resource in resources:
            if resource.get("resource_type") != "aws_security_group":
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource_data.get("raw_body", "")

            # Check for 0.0.0.0/0 or ::/0 in ingress rules
            if "0.0.0.0/0" in raw_body or "::/0" in raw_body:
                for port, service in sensitive_ports.items():
                    # Check for port in raw body with various patterns
                    port_patterns = [
                        rf'from_port\s*=\s*{port}',
                        rf'to_port\s*=\s*{port}',
                        rf'from_port\s*=\s*"{port}"',
                        rf'to_port\s*=\s*"{port}"',
                    ]
                    for pattern in port_patterns:
                        if re.search(pattern, raw_body):
                            findings.append(RuleFinding(
                                rule_id=self.rule.id,
                                rule_name=self.rule.name,
                                severity=self.rule.severity,
                                category=self.rule.category,
                                description=f"Security group allows unrestricted {service} access (port {port}) from 0.0.0.0/0",
                                recommendation=f"Restrict {service} access to specific IP ranges or use VPC endpoints",
                                file_path=file_path,
                                resource_name=resource_data.get("name"),
                                metadata={"port": port, "service": service},
                            ))
                            break

        return findings


@register_rule(file_types=["terraform"])
class TerraformDatabasePublicAccessRule(BaseRule):
    """Check for publicly accessible databases."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-NET-002",
            name="Database Publicly Accessible",
            description="Database instance is configured to be publicly accessible",
            recommendation="Set 'publicly_accessible = false' and use VPC endpoints or bastion hosts for access",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["terraform", "aws", "rds", "database", "networking"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("resource_type") not in ["aws_db_instance", "aws_rds_cluster"]:
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource.get("properties", {}).get("raw_body", "").lower()

            # Check for publicly_accessible = true
            if "publicly_accessible" in raw_body and "publicly_accessible = true" in raw_body:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                    metadata={"resource_type": resource.get("resource_type")},
                ))

        return findings


# =============================================================================
# IAM RULES
# =============================================================================

@register_rule(file_types=["terraform"])
class TerraformIAMWildcardPermissionsRule(BaseRule):
    """Check for wildcard permissions in IAM policies."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-IAM-001",
            name="IAM Wildcard Permissions",
            description="IAM policy contains wildcard (*) permissions which violate least privilege principle",
            recommendation="Replace wildcard actions (e.g., 's3:*') with specific actions needed (e.g., 's3:GetObject', 's3:PutObject')",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["terraform", "aws", "iam", "permissions", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        iam_resource_types = ["aws_iam_policy", "aws_iam_role_policy", "aws_iam_user_policy", "aws_iam_group_policy"]

        for resource in resources:
            resource_type = resource.get("resource_type", "")
            if resource_type not in iam_resource_types:
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource.get("properties", {}).get("raw_body", "")

            # Check for wildcard actions
            wildcard_patterns = [
                r'"[^"]*:\*"',
                r"'[^']*:\*'",
                r'Action\s*=\s*"\*"',
                r'Action\s*=\s*\*',
            ]

            for pattern in wildcard_patterns:
                if re.search(pattern, raw_body):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=self.rule.description,
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=resource_data.get("name"),
                        metadata={"resource_type": resource_type},
                    ))
                    break

        return findings


@register_rule(file_types=["terraform"])
class TerraformIAMNotActionRule(BaseRule):
    """Check for NotAction in IAM policies (potential security risk)."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-IAM-002",
            name="IAM NotAction Usage",
            description="IAM policy uses NotAction which can lead to unintended permissions",
            recommendation="Use explicit Action statements instead of NotAction for clearer permission boundaries",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["terraform", "aws", "iam", "permissions", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        iam_resource_types = ["aws_iam_policy", "aws_iam_role_policy", "aws_iam_user_policy", "aws_iam_group_policy"]

        for resource in resources:
            resource_type = resource.get("resource_type", "")
            if resource_type not in iam_resource_types:
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource.get("properties", {}).get("raw_body", "").lower()

            if "notaction" in raw_body:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                    metadata={"resource_type": resource_type},
                ))

        return findings


# =============================================================================
# TAGGING RULES
# =============================================================================

@register_rule(file_types=["terraform"])
class TerraformRequiredTagsRule(BaseRule):
    """Check if resources have required tags."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-TAG-001",
            name="Missing Required Tags",
            description="Resource does not have all required tags for organization and cost tracking",
            recommendation="Add required tags: Environment, Owner, Project, CostCenter, ManagedBy",
            severity=Severity.MEDIUM,
            category=Category.COST,
            tags=["terraform", "tags", "governance", "cost"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        required_tags = ["environment", "owner", "project", "costcenter", "managedby"]
        taggable_resources = [
            "aws_instance", "aws_s3_bucket", "aws_db_instance", "aws_security_group",
            "aws_vpc", "aws_subnet", "aws_ecs_cluster", "aws_ecs_service", "aws_lambda_function",
            "aws_elasticache_cluster", "aws_lb", "aws_ebs_volume", "aws_rds_cluster",
            "aws_iam_role", "aws_iam_policy", "aws_kms_key", "aws_dynamodb_table",
        ]

        for resource in resources:
            resource_type = resource.get("resource_type", "")
            if resource_type not in taggable_resources:
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource.get("properties", {}).get("raw_body", "").lower()

            # Check if resource has tags block
            if "tags" not in raw_body:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=f"Resource '{resource_data.get('name')}' has no tags block",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                    metadata={"resource_type": resource_type, "missing_tags": required_tags},
                ))
                continue

            # Check for required tags
            missing_tags = []
            for tag in required_tags:
                # Check for tag in various formats
                tag_patterns = [
                    rf'{tag}\s*=',
                    rf'"{tag}"',
                    rf"'{tag}'",
                ]
                has_tag = any(re.search(pattern, raw_body) for pattern in tag_patterns)
                if not has_tag:
                    missing_tags.append(tag)

            if missing_tags:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=f"Resource '{resource_data.get('name')}' is missing required tags: {', '.join(missing_tags)}",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                    metadata={"resource_type": resource_type, "missing_tags": missing_tags},
                ))

        return findings


# =============================================================================
# MODULE RULES
# =============================================================================

@register_rule(file_types=["terraform"])
class TerraformModuleUsageRule(BaseRule):
    """Check if Terraform uses modules for reusability."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-MOD-001",
            name="No Module Usage",
            description="Terraform configuration does not use modules, reducing reusability and maintainability",
            recommendation="Use Terraform modules for reusable components (VPC, ECS, RDS, etc.)",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["terraform", "modules", "best-practices"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        # Skip files inside modules/ directories - these ARE the modules
        # Files like modules/vpc/main.tf don't need to use modules themselves
        if "/modules/" in file_path or file_path.startswith("modules/"):
            return findings

        has_modules = False

        for resource in resources:
            if resource.get("resource_type") == "module":
                has_modules = True
                break

        if not has_modules:
            # Only flag if there are significant resources (more than just basic config)
            resource_count = sum(
                1 for r in resources
                if r.get("resource_type") not in ["backend", "provider", "variable", "output"]
            )
            if resource_count > 5:  # Significant infrastructure without modules
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={"resource_count": resource_count},
                ))

        return findings


@register_rule(file_types=["terraform"])
class TerraformUntrustedModuleSourceRule(BaseRule):
    """Check for untrusted module sources."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-MOD-002",
            name="Untrusted Module Source",
            description="Terraform module is from an untrusted or unverified source",
            recommendation="Use modules from trusted sources: official Terraform Registry, verified organizations, or internal repositories",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["terraform", "modules", "security", "supply-chain"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        trusted_sources = [
            "terraform-aws-modules/",
            "hashicorp/",
            "terraform-google-modules/",
            "Azure/",
            "google-cloud-platform/",
            "github.com/terraform-aws-modules/",
            "github.com/terraform-google-modules/",
            "git::https://github.com/terraform-aws-modules/",
            "git::https://github.com/terraform-google-modules/",
        ]

        for resource in resources:
            if resource.get("resource_type") != "module":
                continue

            module_data = resource.get("properties", {})
            source = module_data.get("source", "")
            raw_body = module_data.get("raw_body", "")

            # Extract source from raw body if not in properties
            if not source:
                source_match = re.search(r'source\s*=\s*"([^"]+)"', raw_body)
                if source_match:
                    source = source_match.group(1)

            # Check if source is trusted
            is_trusted = any(source.startswith(trusted) for trusted in trusted_sources)

            # Local paths are acceptable
            is_local = source.startswith("./") or source.startswith("../") or source.startswith("/modules")

            # Registry modules without explicit source prefix
            is_registry = source.count("/") == 1 and not source.startswith("http")

            if not is_trusted and not is_local and not is_registry:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=f"Module source '{source}' may be from an untrusted source",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=module_data.get("name"),
                    metadata={"source": source},
                ))

        return findings


# =============================================================================
# ENVIRONMENT SEPARATION RULES
# =============================================================================

@register_rule(file_types=["terraform"])
class TerraformEnvironmentSeparationRule(BaseRule):
    """Check for proper environment separation."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-ENV-001",
            name="Missing Environment Separation",
            description="Terraform configuration does not properly separate dev/staging/prod environments",
            recommendation="Use separate state files, workspaces, or directories for each environment (dev, staging, prod)",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["terraform", "environment", "separation", "best-practices"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        env_indicators = ["dev", "development", "staging", "stage", "prod", "production", "test", "qa"]
        has_env_separation = False

        for resource in resources:
            resource_data = resource.get("properties", {})
            raw_body = resource.get("properties", {}).get("raw_body", "")
            raw_config = resource_data.get("raw_config", "")

            all_content = f"{raw_body} {raw_config}"

            # Check for environment variable usage
            if "var.environment" in all_content or "environment" in all_content.lower():
                has_env_separation = True

            # Check for workspace usage
            if "terraform.workspace" in all_content:
                has_env_separation = True

            # Check for env-specific state paths
            for env in ["dev", "staging", "prod"]:
                if env in all_content.lower():
                    has_env_separation = True
                    break

        # Also check file path for environment indicators
        file_path_lower = file_path.lower()
        for env in ["dev", "staging", "prod", "environments"]:
            if env in file_path_lower:
                has_env_separation = True
                break

        if not has_env_separation:
            findings.append(RuleFinding(
                rule_id=self.rule.id,
                rule_name=self.rule.name,
                severity=self.rule.severity,
                category=self.rule.category,
                description=self.rule.description,
                recommendation=self.rule.recommendation,
                file_path=file_path,
                metadata={"file_path": file_path},
            ))

        return findings


@register_rule(file_types=["terraform"])
class TerraformProdEnvironmentProtectionRule(BaseRule):
    """Check for production environment protections."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-ENV-002",
            name="Production Environment Not Protected",
            description="Production environment lacks protective measures (deletion protection, multi-AZ, backups)",
            recommendation="Enable deletion_protection, multi_az, backup_retention_period for production resources",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["terraform", "production", "protection", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        # Check if this is a production configuration
        is_prod = False
        for resource in resources:
            raw_body = resource.get("properties", {}).get("raw_body", "").lower()
            if 'environment.*=.*"prod' in raw_body or 'environment.*=.*"production' in raw_body:
                is_prod = True
                break

        if not is_prod:
            return findings

        # Check for production protections
        for resource in resources:
            resource_type = resource.get("resource_type", "")
            resource_data = resource.get("properties", {})
            raw_body = resource.get("properties", {}).get("raw_body", "").lower()

            # RDS protections
            if resource_type == "aws_db_instance":
                if "deletion_protection" not in raw_body or "deletion_protection = false" in raw_body:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description="RDS instance in production lacks deletion protection",
                        recommendation="Set deletion_protection = true for production databases",
                        file_path=file_path,
                        resource_name=resource_data.get("name"),
                    ))

                if "multi_az" not in raw_body or "multi_az = false" in raw_body:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description="RDS instance in production lacks multi-AZ configuration",
                        recommendation="Set multi_az = true for production databases",
                        file_path=file_path,
                        resource_name=resource_data.get("name"),
                    ))

        return findings


# =============================================================================
# CI/CD VALIDATION RULES
# =============================================================================

@register_rule(file_types=["cicd"])
class TerraformCIFormatValidationRule(BaseRule):
    """Check if CI pipeline includes terraform fmt validation."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-CICD-001",
            name="Missing Terraform Format Check",
            description="CI/CD pipeline does not validate Terraform formatting",
            recommendation="Add 'terraform fmt -check' step to CI pipeline to enforce consistent formatting",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["terraform", "cicd", "formatting", "validation"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str, has_terraform: bool = False) -> list[RuleFinding]:
        findings = []

        # Skip if repository doesn't have Terraform files
        if not has_terraform:
            return findings

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            raw_content = resource.get("raw_content", "")

            # Check for terraform fmt with optional -chdir flag
            # Patterns: terraform fmt, terraform -chdir=xxx fmt, terraform fmt -check
            has_fmt = bool(re.search(r'terraform\s+(-chdir=\S+\s+)?fmt', raw_content))

            if not has_fmt:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={"ci_file": file_path},
                ))

        return findings


@register_rule(file_types=["cicd"])
class TerraformCIValidateRule(BaseRule):
    """Check if CI pipeline includes terraform validate."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-CICD-002",
            name="Missing Terraform Validate",
            description="CI/CD pipeline does not validate Terraform configuration syntax",
            recommendation="Add 'terraform validate' or 'terraform init && terraform validate' step to CI pipeline",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["terraform", "cicd", "validation", "syntax"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str, has_terraform: bool = False) -> list[RuleFinding]:
        findings = []

        # Skip if repository doesn't have Terraform files
        if not has_terraform:
            return findings

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            raw_content = resource.get("raw_content", "")

            # Check for terraform validate with optional -chdir flag
            # Patterns: terraform validate, terraform -chdir=xxx validate
            has_validate = bool(re.search(r'terraform\s+(-chdir=\S+\s+)?validate', raw_content))

            if not has_validate:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={"ci_file": file_path},
                ))

        return findings


@register_rule(file_types=["cicd"])
class TerraformCIPlanRule(BaseRule):
    """Check if CI pipeline includes terraform plan."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="TF-CICD-003",
            name="Missing Terraform Plan",
            description="CI/CD pipeline does not generate Terraform plan for review",
            recommendation="Add 'terraform plan' step to CI pipeline to preview infrastructure changes",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["terraform", "cicd", "plan", "review"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str, has_terraform: bool = False) -> list[RuleFinding]:
        findings = []

        # Skip if repository doesn't have Terraform files
        if not has_terraform:
            return findings

        for resource in resources:
            if resource.get("file_type") != "cicd":
                continue

            raw_content = resource.get("raw_content", "")

            # Check for terraform plan with optional -chdir flag
            # Patterns: terraform plan, terraform -chdir=xxx plan, terraform plan -out=tfplan
            has_plan = bool(re.search(r'terraform\s+(-chdir=\S+\s+)?plan', raw_content))

            if not has_plan:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={"ci_file": file_path},
                ))

        return findings
