"""AWS Cost Explorer knowledge provider.

Retrieves actual cost and usage data from AWS Cost Explorer API.
This ensures cost recommendations use real spending data, not estimates.

Requires AWS Cost Explorer to be enabled in the account.
Falls back to general cost optimization guidance when unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.knowledge.base import KnowledgeDocument, KnowledgeProvider

logger = logging.getLogger(__name__)


class AWSCostExplorerProvider(KnowledgeProvider):
    """Retrieves cost and usage data from AWS Cost Explorer.

    Primary source: AWS Cost Explorer API (boto3 client 'ce').
    Fallback: general cost optimization guidance.

    Provides context for cost-aware recommendations with actual
    spending data from the customer's account.
    """

    def __init__(self, boto_session: Any | None = None):
        self._session = boto_session

    @property
    def name(self) -> str:
        return "aws_cost_explorer"

    @property
    def description(self) -> str:
        return "AWS Cost Explorer actual cost and usage data"

    async def retrieve(
        self,
        query: str,
        *,
        service: str = "",
        region: str = "",
        max_results: int = 5,
    ) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []

        # 1. Try live cost data from Cost Explorer
        if self._session:
            try:
                cost_doc = await self._fetch_cost_data(service, region)
                if cost_doc:
                    documents.append(cost_doc)
            except Exception as exc:
                logger.warning(
                    "COST_EXPLORER_API_FALLBACK",
                    service=service,
                    error=str(exc),
                )

            # 2. Fetch cost optimization recommendations
            try:
                reco_doc = await self._fetch_recommendations(service)
                if reco_doc:
                    documents.append(reco_doc)
            except Exception as exc:
                logger.warning(
                    "COST_EXPLORER_RECOMMENDATIONS_FALLBACK",
                    service=service,
                    error=str(exc),
                )

        # 3. General cost optimization guidance
        if len(documents) < max_results:
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title="AWS Cost Optimization Strategies",
                    content=(
                        "Key AWS cost optimization strategies:\n"
                        "1. Right-size instances based on actual utilization metrics.\n"
                        "2. Use Reserved Instances or Savings Plans for steady-state workloads.\n"
                        "3. Leverage Spot Instances for fault-tolerant workloads.\n"
                        "4. Enable S3 Intelligent-Tiering for unpredictable access patterns.\n"
                        "5. Delete unused resources (EBS snapshots, EIPs, idle LBs).\n"
                        "6. Use AWS Cost Explorer and Budgets for monitoring.\n"
                        "7. Implement resource tagging for cost allocation."
                    ),
                    url="https://aws.amazon.com/aws-cost-management/aws-cost-explorer/",
                    version="latest",
                    relevance_score=0.7,
                    metadata={"topic_type": "strategies"},
                )
            )

        return documents[:max_results]

    async def _fetch_cost_data(
        self, service: str, region: str
    ) -> KnowledgeDocument | None:
        """Fetch actual cost data from Cost Explorer."""
        if not self._session:
            return None

        def _fetch() -> dict[str, Any] | None:
            try:
                ce_client = self._session.client("ce", region_name="us-east-1")

                # Get last 30 days of costs
                end_date = datetime.now(UTC).strftime("%Y-%m-%d")
                start_date = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")

                # Build filters
                filters = {}
                if service:
                    filters = {
                        "Dimensions": {
                            "Key": "SERVICE",
                            "Values": [service.upper()],
                        }
                    }

                response = ce_client.get_cost_and_usage(
                    TimePeriod={"Start": start_date, "End": end_date},
                    Granularity="MONTHLY",
                    Metrics=["BlendedCost", "UsageQuantity"],
                    GroupBy=[
                        {"Type": "DIMENSION", "Key": "SERVICE"},
                    ],
                    Filter=filters if filters else None,
                )

                results = response.get("ResultsByTime", [])
                if not results:
                    return None

                # Extract cost data
                cost_data = []
                for result in results:
                    for group in result.get("Groups", []):
                        service_name = group["Keys"][0] if group["Keys"] else "Unknown"
                        amount = group["Metrics"]["BlendedCost"]["Amount"]
                        unit = group["Metrics"]["BlendedCost"]["Unit"]
                        cost_data.append({
                            "service": service_name,
                            "amount": float(amount),
                            "unit": unit,
                        })

                return {
                    "period": f"{start_date} to {end_date}",
                    "costs": cost_data,
                    "total_amount": sum(c["amount"] for c in cost_data),
                }
            except Exception:
                return None

        result = await asyncio.to_thread(_fetch)
        if not result:
            return None

        costs_text = "\n".join(
            f"- {c['service']}: ${c['amount']:.2f} {c['unit']}"
            for c in result.get("costs", [])[:10]
        )

        return KnowledgeDocument(
            source=self.name,
            title=f"AWS Cost Data — Last 30 Days ({service or 'All Services'})",
            content=(
                f"AWS cost data for {result['period']}:\n"
                f"{costs_text}\n\n"
                f"Total: ${result['total_amount']:.2f}\n\n"
                f"Use this actual spending data to calculate optimization savings."
            ),
            url="https://console.aws.amazon.com/costexplorer/home",
            version="live",
            relevance_score=1.0,
            metadata={
                "service": service,
                "region": region,
                "live_data": result,
                "period": result["period"],
            },
        )

    async def _fetch_recommendations(
        self, service: str
    ) -> KnowledgeDocument | None:
        """Fetch cost optimization recommendations from Cost Explorer."""
        if not self._session:
            return None

        def _fetch() -> dict[str, Any] | None:
            try:
                ce_client = self._session.client("ce", region_name="us-east-1")

                # Get cost optimization recommendations
                response = ce_client.get_cost_recommendations(
                    AccountScope="LINKED",
                )

                recommendations = response.get("CostRecommendations", [])
                if not recommendations:
                    return None

                # Filter by service if specified
                if service:
                    recommendations = [
                        r for r in recommendations
                        if service.lower() in str(r.get("Service", "")).lower()
                    ]

                return {
                    "recommendations": [
                        {
                            "service": r.get("Service", ""),
                            "recommendation": r.get("RecommendationSummary", {}).get(
                                "Description", ""
                            )[:200],
                            "estimated_savings": r.get("RecommendationSummary", {}).get(
                                "EstimatedSavings", {}
                            ),
                        }
                        for r in recommendations[:10]
                    ],
                }
            except Exception:
                return None

        result = await asyncio.to_thread(_fetch)
        if not result:
            return None

        recs_text = "\n".join(
            f"- {r['service']}: {r['recommendation']}"
            for r in result["recommendations"]
        )

        return KnowledgeDocument(
            source=self.name,
            title="AWS Cost Optimization Recommendations",
            content=(
                f"AWS Cost Explorer recommendations:\n"
                f"{recs_text}\n\n"
                f"These are AWS's own recommendations for reducing costs."
            ),
            url="https://console.aws.amazon.com/costexplorer/home#/recommendations",
            version="live",
            relevance_score=0.95,
            metadata={
                "service": service,
                "live_data": result,
                "recommendation_count": len(result["recommendations"]),
            },
        )
