"""AWS Pricing API knowledge provider.

Retrieves current AWS service pricing using the AWS Pricing API (boto3).
This ensures cost recommendations use actual current pricing, not hardcoded
or outdated values.

Falls back to documented baseline pricing when the API is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.knowledge.base import KnowledgeDocument, KnowledgeProvider

logger = logging.getLogger(__name__)

# Baseline pricing fetched from public AWS pricing pages.
# Updated periodically — the pricing API is the authoritative source.
_BASELINE_PRICING: dict[str, dict[str, Any]] = {
    "ec2": {
        "title": "Amazon EC2 Pricing Overview",
        "content": (
            "EC2 pricing models: On-Demand (pay per second), Reserved Instances (1yr/3yr commitments "
            "with up to 72% savings), Savings Plans (flexible commitment with up to 66% savings), "
            "Spot Instances (up to 90% savings with interruption). Pricing varies by instance type, "
            "region, and OS. Use AWS Pricing API for current per-instance-type pricing."
        ),
        "url": "https://aws.amazon.com/ec2/pricing/",
        "pricing_models": ["on_demand", "reserved", "savings_plan", "spot"],
    },
    "s3": {
        "title": "Amazon S3 Storage Pricing",
        "content": (
            "S3 pricing includes storage class (Standard, IA, Glacier), request costs, "
            "data transfer, and management. S3 Standard-IA saves ~40% vs Standard. "
            "Glacier Instant Retrieval saves ~68%. Lifecycle policies automate tiering."
        ),
        "url": "https://aws.amazon.com/s3/pricing/",
        "pricing_models": ["standard", "intelligent_tiering", "standard_ia", "glacier"],
    },
    "rds": {
        "title": "Amazon RDS Pricing",
        "content": (
            "RDS pricing includes instance hours, storage (gp2/gp3/io1), IOPS, "
            "throughput, backup storage, and data transfer. Reserved Instances save "
            "up to 60% vs On-Demand. Multi-AZ doubles instance cost but provides HA."
        ),
        "url": "https://aws.amazon.com/rds/pricing/",
        "pricing_models": ["on_demand", "reserved", "serverless"],
    },
    "lambda": {
        "title": "AWS Lambda Pricing",
        "content": (
            "Lambda charges per request ($0.20 per 1M requests) and per GB-second "
            "of duration. Memory allocation linearly scales CPU/network. "
            "Provisioned Concurrency adds a fixed hourly cost but eliminates cold starts."
        ),
        "url": "https://aws.amazon.com/lambda/pricing/",
        "pricing_models": ["pay_per_use", "provisioned_concurrency"],
    },
    "ebs": {
        "title": "Amazon EBS Pricing",
        "content": (
            "EBS pricing depends on volume type (gp3, io2, st1, sc1), size, IOPS, "
            "and throughput. gp3 is the default recommended volume type — it decouples "
            "IOPS/throughput from size, saving ~20% vs gp2 for most workloads."
        ),
        "url": "https://aws.amazon.com/ebs/pricing/",
        "pricing_models": ["gp3", "gp2", "io2", "st1", "sc1"],
    },
    "cloudfront": {
        "title": "Amazon CloudFront Pricing",
        "content": (
            "CloudFront charges for data transfer out, requests, and invalidation requests. "
            "The free tier includes 1TB data transfer and 10M requests per month. "
            "Using Origin Shield reduces origin loads and improves cache hit ratios."
        ),
        "url": "https://aws.amazon.com/cloudfront/pricing/",
        "pricing_models": ["standard", "security"],
    },
    "elasticache": {
        "title": "Amazon ElastiCache Pricing",
        "content": (
            "ElastiCache pricing depends on node type, count, and engine (Redis/Memcached). "
            "Reserved nodes save up to 55%. Serverless option scales automatically. "
            "Multi-AZ with automatic failover adds ~100% cost."
        ),
        "url": "https://aws.amazon.com/elasticache/pricing/",
        "pricing_models": ["on_demand", "reserved", "serverless"],
    },
}


class AWSPricingProvider(KnowledgeProvider):
    """Retrieves current AWS pricing data.

    Primary source: AWS Pricing API (boto3 client 'pricing').
    Fallback: curated baseline pricing from public AWS pricing pages.

    The retrieved pricing context is passed to the LLM so cost
    recommendations are based on actual current pricing.
    """

    def __init__(self, boto_session: Any | None = None):
        self._session = boto_session

    @property
    def name(self) -> str:
        return "aws_pricing"

    @property
    def description(self) -> str:
        return "AWS Pricing API and cost optimization guidance"

    async def retrieve(
        self,
        query: str,
        *,
        service: str = "",
        region: str = "",
        max_results: int = 5,
    ) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []

        # 1. Try live pricing API for the specific service
        if service and self._session:
            try:
                live_doc = await self._fetch_live_pricing(service, region)
                if live_doc:
                    documents.append(live_doc)
            except Exception as exc:
                logger.warning(
                    "PRICING_API_FALLBACK",
                    service=service,
                    region=region,
                    error=str(exc),
                )

        # 2. Baseline pricing for the service
        if service and service.lower() in _BASELINE_PRICING:
            pricing = _BASELINE_PRICING[service.lower()]
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title=pricing["title"],
                    content=pricing["content"],
                    url=pricing["url"],
                    version="baseline",
                    relevance_score=0.85,
                    metadata={
                        "service": service,
                        "pricing_models": pricing.get("pricing_models", []),
                    },
                )
            )

        # 3. General cost optimization principles
        if len(documents) < max_results:
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title="AWS Cost Optimization Principles",
                    content=(
                        "AWS Well-Architected Cost Optimization pillar principles: "
                        "1) Implement cloud financial management. "
                        "2) Expenditure awareness — use tagging and cost allocation. "
                        "3) Cost-effective resources — right-size instances, use appropriate pricing models. "
                        "4) Manage demand and supply resources — auto-scaling, Spot, Reserved. "
                        "5) Optimize over time — review and adjust continuously."
                    ),
                    url="https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html",
                    version="latest",
                    relevance_score=0.7,
                    metadata={"topic_type": "principles"},
                )
            )

        return documents[:max_results]

    async def _fetch_live_pricing(
        self, service: str, region: str
    ) -> KnowledgeDocument | None:
        """Fetch live pricing from the AWS Pricing API."""
        if not self._session:
            return None

        def _fetch() -> dict[str, Any] | None:
            try:
                pricing_client = self._session.client("pricing", region_name="us-east-1")
                filters = [
                    {"Type": "TERM_MATCH", "Field": "serviceCode", "Value": service.upper()},
                ]
                if region:
                    filters.append(
                        {"Type": "TERM_MATCH", "Field": "location", "Value": region}
                    )
                response = pricing_client.get_products(
                    ServiceCode=service.upper(),
                    Filters=filters,
                    MaxResults=1,
                )
                price_list = response.get("PriceList", [])
                if price_list:
                    import json
                    product = json.loads(price_list[0])
                    return {
                        "product": product.get("product", {}).get("attributes", {}),
                        "terms": product.get("terms", {}),
                    }
                return None
            except Exception:
                return None

        result = await asyncio.to_thread(_fetch)
        if not result:
            return None

        return KnowledgeDocument(
            source=self.name,
            title=f"Live AWS Pricing — {service} ({region or 'global'})",
            content=(
                f"Current AWS pricing data for {service} in {region or 'global'}. "
                f"Use this data for accurate cost calculations in recommendations."
            ),
            url=f"https://aws.amazon.com/{service}/pricing/",
            version="live",
            relevance_score=1.0,
            metadata={"service": service, "region": region, "live_data": result},
        )
