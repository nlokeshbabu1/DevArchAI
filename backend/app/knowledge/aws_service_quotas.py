"""AWS Service Quotas knowledge provider.

Retrieves service quotas and usage data from AWS Service Quotas API.
This ensures recommendations about resource limits use actual account
quotas rather than hardcoded defaults.

Falls back to documented default quotas when the API is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.knowledge.base import KnowledgeDocument, KnowledgeProvider

logger = logging.getLogger(__name__)

# Default AWS service quotas (us-east-1, may vary by account/region)
_DEFAULT_QUOTAS: dict[str, dict[str, Any]] = {
    "ec2": {
        "title": "Amazon EC2 Default Quotas",
        "quotas": {
            "Running On-Demand Standard instances": "1,120 vCPUs",
            "Running On-Demand Dedicated hosts": "112",
            "Elastic IP addresses per region": "5",
            "Security groups per VPC": "5",
            "Rules per security group": "60",
        },
        "url": "https://docs.aws.amazon.com/general/latest/gr/ec2.html",
    },
    "s3": {
        "title": "Amazon S3 Default Quotas",
        "quotas": {
            "Buckets per account": "100 (soft limit, adjustable)",
            "Prefixes per bucket": "No limit",
            "Objects per bucket": "No limit",
            "Maximum object size": "5 TB",
        },
        "url": "https://docs.aws.amazon.com/general/latest/gr/s3.html",
    },
    "rds": {
        "title": "Amazon RDS Default Quotas",
        "quotas": {
            "DB instances per region": "40",
            "Storage per DB instance": "64 TB",
            "Max databases per instance": "5,000",
            "Read replicas per source": "5",
        },
        "url": "https://docs.aws.amazon.com/general/latest/gr/rds.html",
    },
    "lambda": {
        "title": "AWS Lambda Default Quotas",
        "quotas": {
            "Concurrent executions": "1,000",
            "Function storage": "75 GB total",
            "Ephemeral storage": "10,240 MB max",
            "Package size (compressed)": "50 MB",
            "Package size (uncompressed)": "250 MB",
        },
        "url": "https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html",
    },
    "vpc": {
        "title": "Amazon VPC Default Quotas",
        "quotas": {
            "VPCs per region": "5",
            "Subnets per VPC": "200",
            "Security groups per VPC": "5",
            "NACLs per VPC": "5",
            "Route tables per VPC": "200",
        },
        "url": "https://docs.aws.amazon.com/vpc/latest/userguide/vpc-limits.html",
    },
    "eks": {
        "title": "Amazon EKS Default Quotas",
        "quotas": {
            "Clusters per region": "10",
            "Managed node groups per cluster": "100",
            "Fargate profiles per cluster": "100",
        },
        "url": "https://docs.aws.amazon.com/eks/latest/userguide/service-quotas.html",
    },
}


class AWSServiceQuotasProvider(KnowledgeProvider):
    """Retrieves service quotas and usage from AWS Service Quotas API.

    Primary source: AWS Service Quotas API (boto3 client 'service-quotas').
    Fallback: documented default quotas per service.

    Provides context for recommendations about resource limits, capacity
    planning, and quota increase requests.
    """

    def __init__(self, boto_session: Any | None = None):
        self._session = boto_session

    @property
    def name(self) -> str:
        return "aws_service_quotas"

    @property
    def description(self) -> str:
        return "AWS Service Quotas and usage limits"

    async def retrieve(
        self,
        query: str,
        *,
        service: str = "",
        region: str = "",
        max_results: int = 5,
    ) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []

        # 1. Try live quotas API for the specific service
        if service and self._session:
            try:
                live_doc = await self._fetch_live_quotas(service, region)
                if live_doc:
                    documents.append(live_doc)
            except Exception as exc:
                logger.warning(
                    "SERVICE_QUOTAS_API_FALLBACK",
                    service=service,
                    region=region,
                    error=str(exc),
                )

        # 2. Default quotas for the service
        if service and service.lower() in _DEFAULT_QUOTAS:
            quota_data = _DEFAULT_QUOTAS[service.lower()]
            quota_text = "\n".join(
                f"- {k}: {v}" for k, v in quota_data["quotas"].items()
            )
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title=quota_data["title"],
                    content=(
                        f"Default AWS service quotas for {service.upper()}:\n"
                        f"{quota_text}\n\n"
                        f"Note: These are default limits. Actual quotas may differ by "
                        f"account. Use AWS Service Quotas console to check your "
                        f"specific limits."
                    ),
                    url=quota_data["url"],
                    version="default",
                    relevance_score=0.85,
                    metadata={
                        "service": service,
                        "quotas": quota_data["quotas"],
                        "quota_type": "default",
                    },
                )
            )

        # 3. General quota management guidance
        if len(documents) < max_results:
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title="AWS Service Quotas Best Practices",
                    content=(
                        "AWS Service Quotas management best practices:\n"
                        "1. Monitor quota usage proactively to avoid service disruptions.\n"
                        "2. Request quota increases before hitting limits in production.\n"
                        "3. Use CloudWatch alarms on quota utilization metrics.\n"
                        "4. Tag resources for cost allocation and quota tracking.\n"
                        "5. Review quotas regularly as AWS adjusts defaults."
                    ),
                    url="https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html",
                    version="latest",
                    relevance_score=0.7,
                    metadata={"topic_type": "best_practices"},
                )
            )

        return documents[:max_results]

    async def _fetch_live_quotas(
        self, service: str, region: str
    ) -> KnowledgeDocument | None:
        """Fetch live quota data from the AWS Service Quotas API."""
        if not self._session:
            return None

        def _fetch() -> dict[str, Any] | None:
            try:
                client = self._session.client(
                    "service-quotas",
                    region_name=region or "us-east-1",
                )
                # List services to get the service code
                response = client.list_services(
                    Filters=[{"Name": "SERVICE_CODE", "Values": [service.upper()]}]
                )
                services = response.get("Services", [])
                if not services:
                    return None

                service_code = services[0]["ServiceCode"]

                # List quotas for the service
                quotas_response = client.list_aws_service_quotas(
                    ServiceCode=service_code, MaxResults=10
                )
                quotas = quotas_response.get("Quotas", [])

                return {
                    "service_code": service_code,
                    "quotas": [
                        {
                            "name": q.get("QuotaName", ""),
                            "value": str(q.get("Value", {}).get("Value", "")),
                            "unit": q.get("Value", {}).get("Unit", ""),
                            "adjustable": q.get("Adjustable", False),
                        }
                        for q in quotas[:10]
                    ],
                }
            except Exception:
                return None

        result = await asyncio.to_thread(_fetch)
        if not result:
            return None

        quota_text = "\n".join(
            f"- {q['name']}: {q['value']} {q['unit']} (adjustable: {q['adjustable']})"
            for q in result.get("quotas", [])
        )

        return KnowledgeDocument(
            source=self.name,
            title=f"Live AWS Service Quotas — {service} ({region or 'global'})",
            content=(
                f"Current AWS service quotas for {service} in {region or 'global'}:\n"
                f"{quota_text}\n\n"
                f"Use this data to assess capacity and recommend quota increases."
            ),
            url=f"https://console.aws.amazon.com/servicequotas/home/services/{service.upper()}/quotas",
            version="live",
            relevance_score=1.0,
            metadata={
                "service": service,
                "region": region,
                "live_data": result,
                "quota_type": "live",
            },
        )
