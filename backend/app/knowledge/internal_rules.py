"""Internal DevArchAI rules knowledge provider.

Provides DevArchAI-specific security rules, cost optimization patterns,
and architectural guidelines. These are organization-specific standards
that complement AWS official guidance.
"""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge.base import KnowledgeDocument, KnowledgeProvider

logger = logging.getLogger(__name__)

# DevArchAI internal rule mappings — keyed by rule_id
_INTERNAL_RULES: dict[str, dict[str, Any]] = {
    "root_user_no_mfa": {
        "title": "DevArchAI Rule: Root Account MFA Required",
        "severity": "critical",
        "content": (
            "The AWS root account must have multi-factor authentication enabled. "
            "The root account has unrestricted access to all AWS services and billing. "
            "Use hardware MFA tokens (not virtual) for root accounts. "
            "Create IAM admin users for daily operations."
        ),
        "remediation": (
            "1. Sign in to the AWS Management Console as root. "
            "2. Navigate to IAM → Security credentials. "
            "3. Assign MFA device (hardware token recommended). "
            "4. Create IAM admin user with AdministratorAccess policy. "
            "5. Do not use root account for daily operations."
        ),
    },
    "public_s3_bucket": {
        "title": "DevArchAI Rule: S3 Bucket Public Access Prohibited",
        "severity": "critical",
        "content": (
            "S3 buckets must not be publicly accessible unless explicitly required "
            "and approved. Public S3 buckets are a leading cause of data breaches. "
            "Enable Block Public Access at the account level."
        ),
        "remediation": (
            "1. Enable Block Public Access for the account in S3 console. "
            "2. Audit existing bucket policies for public statements. "
            "3. Remove or restrict any public access. "
            "4. Use S3 Access Points for controlled access patterns."
        ),
    },
    "open_security_group": {
        "title": "DevArchAI Rule: Security Group Ingress Restricted",
        "severity": "high",
        "content": (
            "Security groups must not allow unrestricted ingress (0.0.0.0/0) on "
            "management ports (22, 3389) or database ports (3306, 5432, 6379). "
            "Use bastion hosts, SSM Session Manager, or VPN for access."
        ),
        "remediation": (
            "1. Audit all security groups for 0.0.0.0/0 ingress rules. "
            "2. Replace with specific CIDR blocks or security group references. "
            "3. Use SSM Session Manager instead of SSH/RDP. "
            "4. Implement just-in-time access for administrative ports."
        ),
    },
    "unencrypted_ebs": {
        "title": "DevArchAI Rule: EBS Volumes Must Be Encrypted",
        "severity": "high",
        "content": (
            "All EBS volumes must use encryption. Enable default EBS encryption "
            "at the account level to ensure new volumes are encrypted automatically. "
            "Existing unencrypted volumes should be migrated."
        ),
        "remediation": (
            "1. Enable default EBS encryption in EC2 settings. "
            "2. Create encrypted copies of unencrypted volumes. "
            "3. Update instance configurations to use encrypted volumes. "
            "4. Delete old unencrypted volumes after migration."
        ),
    },
    "unencrypted_rds": {
        "title": "DevArchAI Rule: RDS Instances Must Be Encrypted",
        "severity": "high",
        "content": (
            "All RDS instances must have encryption at rest enabled. "
            "Encryption must be configured at launch — it cannot be added later. "
            "Use AWS KMS for key management."
        ),
        "remediation": (
            "1. For new instances: enable encryption during launch. "
            "2. For existing instances: create an encrypted snapshot, "
            "then restore from the snapshot to a new encrypted instance. "
            "3. Update application connection strings."
        ),
    },
    "no_resource_limits": {
        "title": "DevArchAI Rule: Resource Limits Must Be Set",
        "severity": "medium",
        "content": (
            "AWS service quotas should be reviewed and appropriate limits set. "
            "Default limits may be too low for production or too high for cost control. "
            "Request increases proactively and set billing alerts."
        ),
    },
    "missing_tags": {
        "title": "DevArchAI Rule: Resources Must Be Tagged",
        "severity": "low",
        "content": (
            "All AWS resources must have standard tags: Environment, Team, Project, "
            "CostCenter, and Owner. Tags enable cost allocation, access control, "
            "and operational visibility."
        ),
    },
    "no_flow_logs": {
        "title": "DevArchAI Rule: VPC Flow Logs Required",
        "severity": "medium",
        "content": (
            "All VPCs must have Flow Logs enabled. Flow Logs capture network traffic "
            "metadata for security forensics, compliance, and troubleshooting. "
            "Send logs to CloudWatch Logs or S3."
        ),
    },
    "no_cloudtrail": {
        "title": "DevArchAI Rule: CloudTrail Required",
        "severity": "critical",
        "content": (
            "CloudTrail must be enabled in all regions with organization trail. "
            "Enable log file validation, integrate with CloudWatch Logs, "
            "and configure S3 bucket for log storage with MFA delete."
        ),
    },
}


class InternalRulesProvider(KnowledgeProvider):
    """Provides DevArchAI internal security rules and guidelines.

    These are organization-specific standards that complement AWS official
    guidance. They ensure recommendations align with company policy.
    """

    @property
    def name(self) -> str:
        return "internal_rules"

    @property
    def description(self) -> str:
        return "DevArchAI internal security rules and architectural guidelines"

    async def retrieve(
        self,
        query: str,
        *,
        service: str = "",
        region: str = "",
        max_results: int = 5,
    ) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []
        query_lower = query.lower()

        # Match rules by keyword overlap with query or service
        scored_rules: list[tuple[float, str, dict[str, Any]]] = []
        for key, rule in _INTERNAL_RULES.items():
            score = 0.0
            # Direct key match
            if any(word in query_lower for word in key.split("_")):
                score += 0.5
            # Service match in content
            if service and service.lower() in rule.get("content", "").lower():
                score += 0.3
            # Severity weight
            severity_weight = {"critical": 0.2, "high": 0.15, "medium": 0.1, "low": 0.05}
            score += severity_weight.get(rule.get("severity", ""), 0.0)

            if score > 0:
                scored_rules.append((score, key, rule))

        scored_rules.sort(key=lambda x: x[0], reverse=True)

        for score, key, rule in scored_rules[:max_results]:
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title=rule["title"],
                    content=rule["content"],
                    url="",
                    version="1.0",
                    relevance_score=min(score, 1.0),
                    metadata={
                        "rule_id": key,
                        "severity": rule.get("severity", "medium"),
                        "remediation": rule.get("remediation", ""),
                    },
                )
            )

        if not documents:
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title="DevArchAI General Guidelines",
                    content=(
                        "Follow the principle of least privilege. Encrypt all data "
                        "at rest and in transit. Enable comprehensive logging. "
                        "Tag all resources. Review access regularly."
                    ),
                    version="1.0",
                    relevance_score=0.5,
                    metadata={"topic_type": "general"},
                )
            )

        return documents[:max_results]
