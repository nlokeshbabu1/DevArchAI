"""AWS Security knowledge provider.

Retrieves security context from AWS Security Hub, CIS Benchmark, and
NIST 800-53 references. Provides compliance framework mappings that the
LLM uses to generate compliance-aware recommendations.
"""

from __future__ import annotations

import logging

from app.knowledge.base import KnowledgeDocument, KnowledgeProvider

logger = logging.getLogger(__name__)

# CIS AWS Foundations Benchmark mappings
_CIS_BENCHMARKS: dict[str, dict[str, str]] = {
    "iam_root_mfa": {
        "title": "CIS 1.5 — Ensure MFA is enabled for root account",
        "control": "CIS AWS Foundations 1.5",
        "content": (
            "The root account has unrestricted access. MFA adds a second layer of "
            "authentication. Root MFA should use hardware tokens, not virtual MFA."
        ),
        "url": "https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cis-controls.html",
    },
    "iam_unused_credentials": {
        "title": "CIS 1.16 — Ensure credentials unused for 90 days are disabled",
        "control": "CIS AWS Foundations 1.16",
        "content": (
            "IAM credentials unused for 90+ days should be investigated and disabled. "
            "This reduces the attack surface from compromised or forgotten credentials."
        ),
    },
    "s3_bucket_public_access": {
        "title": "CIS 2.1.1 — Ensure S3 buckets have public access blocked",
        "control": "CIS AWS Foundations 2.1.1",
        "content": (
            "S3 buckets should have Block Public Access enabled at the account level. "
            "Public buckets expose data to the internet and are a common breach vector."
        ),
    },
    "security_groups_unrestricted": {
        "title": "CIS 5.2 — Ensure no security groups allow unrestricted ingress",
        "control": "CIS AWS Foundations 5.2",
        "content": (
            "Security groups should not allow 0.0.0.0/0 ingress on sensitive ports "
            "(22, 3389, 3306, 5432, 6379, 27017). Use bastion hosts or VPN."
        ),
    },
    "cloudtrail_enabled": {
        "title": "CIS 3.1 — Ensure CloudTrail is enabled",
        "control": "CIS AWS Foundations 3.1",
        "content": (
            "CloudTrail records API calls for auditing. It should be enabled in all "
            "regions with log file validation and integration with CloudWatch Logs."
        ),
    },
    "vpc_flow_logs": {
        "title": "CIS 3.9 — Ensure VPC Flow Logs are enabled",
        "control": "CIS AWS Foundations 3.9",
        "content": (
            "VPC Flow Logs capture network traffic metadata. They are essential for "
            "forensics, compliance, and detecting anomalous network activity."
        ),
    },
    "rds_encryption": {
        "title": "CIS 2.1.3 — Ensure RDS encryption is enabled",
        "control": "CIS AWS Foundations 2.1.3",
        "content": (
            "RDS instances should have encryption at rest enabled using AWS KMS. "
            "Encryption protects data if storage media are compromised."
        ),
    },
    "ebs_encryption": {
        "title": "CIS 2.1.2 — Ensure EBS volumes are encrypted",
        "control": "CIS AWS Foundations 2.1.2",
        "content": (
            "EBS volumes should be encrypted. Default EBS encryption should be "
            "enabled at the account level to ensure all new volumes are encrypted."
        ),
    },
}

# NIST 800-53 control mappings
_NIST_CONTROLS: dict[str, dict[str, str]] = {
    "access_control": {
        "title": "NIST AC-2: Account Management",
        "control": "NIST 800-53 AC-2",
        "content": (
            "Manage information system accounts including establishing, activating, "
            "modifying, reviewing, disabling, and removing accounts. Implement "
            "least privilege access and regular access reviews."
        ),
    },
    "audit_logging": {
        "title": "NIST AU-2: Audit Events",
        "control": "NIST 800-53 AU-2",
        "content": (
            "Audit events must include: access attempts, data changes, privilege "
            "escalation, system startup/shutdown, and security-relevant events. "
            "CloudTrail and CloudWatch provide AWS-native audit logging."
        ),
    },
    "encryption": {
        "title": "NIST SC-13: Cryptographic Protection",
        "control": "NIST 800-53 SC-13",
        "content": (
            "Implement FIPS-validated cryptography for data at rest and in transit. "
            "Use AWS KMS for key management. Ensure TLS 1.2+ for all connections."
        ),
    },
    "network_security": {
        "title": "NIST SC-7: Boundary Protection",
        "control": "NIST 800-53 SC-7",
        "content": (
            "Monitor and control communications at the external boundary. "
            "Implement defense-in-depth with security groups, NACLs, WAF, and "
            "VPC design. Restrict inbound and outbound traffic to minimum required."
        ),
    },
    "incident_response": {
        "title": "NIST IR-4: Incident Handling",
        "control": "NIST 800-53 IR-4",
        "content": (
            "Implement incident handling capabilities including detection, analysis, "
            "containment, eradication, and recovery. Use AWS GuardDuty, Security Hub, "
            "and EventBridge for automated incident detection and response."
        ),
    },
}

# AWS Security Hub standard findings context
_SECURITY_HUB_FINDINGS: dict[str, dict[str, str]] = {
    "critical": {
        "severity_context": (
            "CRITICAL severity findings represent immediate risk to the organization. "
            "They require remediation within 24-48 hours. Examples: public S3 buckets "
            "with sensitive data, root account without MFA, security groups allowing "
            "0.0.0.0/0 on management ports."
        ),
    },
    "high": {
        "severity_context": (
            "HIGH severity findings represent significant risk. They should be "
            "remediated within 7 days. Examples: unencrypted databases, overly "
            "permissive IAM policies, missing CloudTrail logging."
        ),
    },
    "medium": {
        "severity_context": (
            "MEDIUM severity findings represent moderate risk. They should be "
            "remediated within 30 days. Examples: unused access keys, non-standard "
            "instance types, missing resource tags."
        ),
    },
    "low": {
        "severity_context": (
            "LOW severity findings represent minimal risk. They should be "
            "addressed within 90 days. Examples: informational findings about "
            "optional security best practices."
        ),
    },
}


class AWSSecurityProvider(KnowledgeProvider):
    """Retrieves security and compliance context from CIS, NIST, and AWS Security Hub.

    Provides compliance framework mappings that the LLM uses to generate
    compliance-aware recommendations with specific control references.
    """

    @property
    def name(self) -> str:
        return "aws_security"

    @property
    def description(self) -> str:
        return "AWS Security Hub, CIS Benchmark, and NIST 800-53 context"

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

        # 1. CIS benchmarks relevant to the query/service
        for key, bench in _CIS_BENCHMARKS.items():
            if (
                service.lower() in key
                or any(word in query_lower for word in key.split("_"))
                or service.lower() in bench.get("content", "").lower()
            ):
                documents.append(
                    KnowledgeDocument(
                        source=self.name,
                        title=bench["title"],
                        content=bench["content"],
                        url=bench.get("url", ""),
                        version="CIS AWS Foundations v1.5",
                        relevance_score=0.95,
                        metadata={
                            "framework": "CIS",
                            "control": bench["control"],
                            "service": service,
                        },
                    )
                )

        # 2. NIST controls relevant to the query
        for key, ctrl in _NIST_CONTROLS.items():
            if any(word in query_lower for word in key.split("_")):
                documents.append(
                    KnowledgeDocument(
                        source=self.name,
                        title=ctrl["title"],
                        content=ctrl["content"],
                        version="NIST 800-53 Rev 5",
                        relevance_score=0.85,
                        metadata={
                            "framework": "NIST",
                            "control": ctrl["control"],
                        },
                    )
                )

        # 3. Severity context if severity is mentioned
        for sev, ctx in _SECURITY_HUB_FINDINGS.items():
            if sev in query_lower:
                documents.append(
                    KnowledgeDocument(
                        source=self.name,
                        title=f"Security Severity: {sev.upper()}",
                        content=ctx["severity_context"],
                        version="AWS Security Hub",
                        relevance_score=0.75,
                        metadata={"severity": sev},
                    )
                )

        # If no specific matches, provide general security context
        if not documents:
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title="AWS Security Best Practices Overview",
                    content=(
                        "AWS security best practices include: enable MFA everywhere, "
                        "use IAM roles not access keys, encrypt data at rest and in transit, "
                        "enable CloudTrail and GuardDuty, follow least privilege principle, "
                        "regularly rotate credentials, and use AWS Security Hub for posture management."
                    ),
                    url="https://aws.amazon.com/security/",
                    version="latest",
                    relevance_score=0.6,
                    metadata={"topic_type": "general"},
                )
            )

        return documents[:max_results]
