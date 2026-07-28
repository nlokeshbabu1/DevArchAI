"""AWS Trusted Advisor knowledge provider.

Retrieves recommendations from AWS Trusted Advisor via the Support API.
Trusted Advisor provides real-time guidance for cost optimization,
performance, security, and fault tolerance.

Requires AWS Support plan (Business or Enterprise) for full access.
Falls back to curated best practices when the API is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.knowledge.base import KnowledgeDocument, KnowledgeProvider

logger = logging.getLogger(__name__)

# Trusted Advisor check categories and their focus areas
_TA_CATEGORIES = {
    "cost_optimization": {
        "title": "Trusted Advisor — Cost Optimization",
        "checks": [
            "Low Utilization Amazon EC2 Instances",
            "Amazon EBS Snapshots Age",
            "Idle Load Balancers",
            "Unassociated Elastic IP Addresses",
            "Amazon RDS Idle DB Instances",
            "S3 Bucket Versioning",
        ],
        "url": "https://aws.amazon.com/premiumsupport/technology/trusted-advisor/",
    },
    "performance": {
        "title": "Trusted Advisor — Performance",
        "checks": [
            "Amazon EC2 Instance Performance",
            "Amazon EBS Volume Configuration",
            "Amazon RDS High CPU/Automatic Failover",
            "CloudFront CDN Optimization",
            "ELB Connection Draining",
        ],
        "url": "https://aws.amazon.com/premiumsupport/technology/trusted-advisor/",
    },
    "security": {
        "title": "Trusted Advisor — Security",
        "checks": [
            "IAM Use",
            "IAM Root Account Usage",
            "MFA on Root Account",
            "Security Groups — Specific Ports Unrestricted",
            "Amazon S3 Bucket Permissions",
            "AWS CloudTrail Logging",
            "Amazon EBS Public Snapshots",
            "Amazon RDS Public Snapshots",
        ],
        "url": "https://aws.amazon.com/premiumsupport/technology/trusted-advisor/",
    },
    "fault_tolerance": {
        "title": "Trusted Advisor — Fault Tolerance",
        "checks": [
            "Amazon EBS Availability Zone Coverage",
            "Amazon RDS Multi-AZ",
            "ELB Health Checks",
            "AWS CloudTrail Enabled",
            "Amazon Route 53 Health Checks",
        ],
        "url": "https://aws.amazon.com/premiumsupport/technology/trusted-advisor/",
    },
}


class AWSTrustedAdvisorProvider(KnowledgeProvider):
    """Retrieves AWS Trusted Advisor recommendations.

    Primary source: AWS Support API (boto3 client 'support').
    Fallback: curated best practice checklists per category.

    Provides context for recommendations aligned with AWS's own
    automated optimization checks.
    """

    def __init__(self, boto_session: Any | None = None):
        self._session = boto_session

    @property
    def name(self) -> str:
        return "aws_trusted_advisor"

    @property
    def description(self) -> str:
        return "AWS Trusted Advisor recommendations and best practices"

    async def retrieve(
        self,
        query: str,
        *,
        service: str = "",
        region: str = "",
        max_results: int = 5,
    ) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []

        # 1. Try live Trusted Advisor checks
        if self._session:
            try:
                live_doc = await self._fetch_live_checks(service)
                if live_doc:
                    documents.append(live_doc)
            except Exception as exc:
                logger.warning(
                    "TRUSTED_ADVISOR_API_FALLBACK",
                    error=str(exc),
                )

        # 2. Category-specific best practices
        query_lower = query.lower()
        for category, data in _TA_CATEGORIES.items():
            # Match by category name or check relevance
            if (
                category in query_lower
                or any(check.lower() in query_lower for check in data["checks"])
                or (service and service.lower() in query_lower)
            ):
                checks_text = "\n".join(f"  - {check}" for check in data["checks"])
                documents.append(
                    KnowledgeDocument(
                        source=self.name,
                        title=data["title"],
                        content=(
                            f"AWS Trusted Advisor checks for {category}:\n"
                            f"{checks_text}\n\n"
                            f"These are automated checks AWS performs to identify "
                            f"optimization opportunities."
                        ),
                        url=data["url"],
                        version="latest",
                        relevance_score=0.9,
                        metadata={
                            "category": category,
                            "checks": data["checks"],
                            "service": service,
                        },
                    )
                )

        # 3. General Trusted Advisor overview
        if not documents:
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title="AWS Trusted Advisor Overview",
                    content=(
                        "AWS Trusted Advisor helps optimize your AWS environment across "
                        "four categories:\n"
                        "1. Cost Optimization — Identify unused or underutilized resources.\n"
                        "2. Performance — Improve service performance and efficiency.\n"
                        "3. Security — Enhance security posture and compliance.\n"
                        "4. Fault Tolerance — Increase availability and redundancy.\n\n"
                        "Enterprise support provides full check access; basic is limited."
                    ),
                    url="https://aws.amazon.com/premiumsupport/technology/trusted-advisor/",
                    version="latest",
                    relevance_score=0.7,
                    metadata={"topic_type": "overview"},
                )
            )

        return documents[:max_results]

    async def _fetch_live_checks(
        self, service: str
    ) -> KnowledgeDocument | None:
        """Fetch live Trusted Advisor checks from the Support API."""
        if not self._session:
            return None

        def _fetch() -> dict[str, Any] | None:
            try:
                support_client = self._session.client(
                    "support", region_name="us-east-1"
                )
                # Describe Trusted Advisor checks
                response = support_client.describe_trusted_advisor_checks(
                    language="en"
                )
                checks = response.get("checks", [])

                # Filter by service if specified
                if service:
                    checks = [
                        c for c in checks
                        if service.lower() in str(c.get("category", "")).lower()
                        or service.lower() in str(c.get("name", "")).lower()
                    ]

                return {
                    "total_checks": len(checks),
                    "checks": [
                        {
                            "id": c.get("id", ""),
                            "name": c.get("name", ""),
                            "category": c.get("category", ""),
                            "description": c.get("description", "")[:200],
                        }
                        for c in checks[:10]
                    ],
                }
            except Exception:
                return None

        result = await asyncio.to_thread(_fetch)
        if not result or not result.get("checks"):
            return None

        checks_text = "\n".join(
            f"- [{c['category']}] {c['name']}: {c['description'][:100]}"
            for c in result["checks"]
        )

        return KnowledgeDocument(
            source=self.name,
            title=f"Live AWS Trusted Advisor Checks ({result['total_checks']} total)",
            content=(
                f"AWS Trusted Advisor checks retrieved from your account:\n"
                f"{checks_text}\n\n"
                f"Use these checks to align recommendations with AWS's own analysis."
            ),
            url="https://console.aws.amazon.com/trustedadvisor/home",
            version="live",
            relevance_score=1.0,
            metadata={
                "service": service,
                "live_data": result,
                "check_count": result["total_checks"],
            },
        )
