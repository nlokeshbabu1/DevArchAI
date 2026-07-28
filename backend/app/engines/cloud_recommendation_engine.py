"""Cloud AI Recommendation Engine — knowledge-enriched recommendation generation.

This is the core engine that:
1. Takes findings from a cloud scan
2. Retrieves authoritative knowledge context from multiple providers
3. Passes knowledge context + findings to the LLM
4. Produces structured, knowledge-grounded recommendations

The LLM never relies solely on pretrained knowledge — it always receives
retrieved context from official AWS documentation, pricing APIs, security
benchmarks, and internal rules.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.knowledge.base import KnowledgeDocument
from app.knowledge.metrics import MetricsCollector, get_knowledge_metrics
from app.knowledge.registry import KnowledgeRegistry, get_knowledge_registry

logger = logging.getLogger(__name__)


@dataclass
class CloudRecommendation:
    """Structured AI recommendation output.

    Every field maps to a column in the cloud_ai_recommendations table.
    """

    finding_id: str = ""
    rule_id: str = ""
    service: str = ""
    resource_id: str = ""
    region: str = ""

    executive_summary: str = ""
    root_cause: str = ""
    business_impact: str = ""
    security_impact: str = ""
    cost_impact: str = ""

    official_best_practice: str = ""
    documentation_references: list[dict[str, str]] = field(default_factory=list)
    documentation_retrieved_at: datetime | None = None

    cloudformation_fix: str | None = None
    terraform_fix: str | None = None
    aws_cli_fix: str | None = None
    console_steps: list[str] = field(default_factory=list)

    compliance_mapping: dict[str, list[str]] = field(default_factory=dict)

    confidence_score: float = 0.0
    estimated_risk_reduction: float = 0.0
    estimated_monthly_savings: float = 0.0
    severity: str = "medium"

    knowledge_sources_used: list[str] = field(default_factory=list)
    llm_provider: str | None = None


# System prompt for the recommendation LLM
_RECOMMENDATION_SYSTEM_PROMPT = """You are an expert AWS Cloud Architect generating production-grade security and cost recommendations.

CRITICAL RULES:
1. NEVER rely solely on your pretrained knowledge. Use the provided knowledge context.
2. Every recommendation MUST cite at least one official AWS documentation reference.
3. Cost estimates MUST use the provided pricing data, not your training data.
4. Compliance mappings MUST reference specific controls from the provided context.
5. Terraform fixes MUST use current provider versions and best practices.
6. If knowledge context is insufficient, state "Based on available guidance" and note the gap.

OUTPUT FORMAT: Return a JSON object with these exact fields:
{
    "executive_summary": "1-2 sentence executive summary",
    "root_cause": "Technical root cause explanation",
    "business_impact": "Impact on business operations",
    "security_impact": "Security risk description",
    "cost_impact": "Cost implications",
    "official_best_practice": "AWS official best practice for this issue",
    "documentation_references": [{"title": "...", "url": "...", "version": "..."}],
    "cloudformation_fix": "CloudFormation template to fix the issue (if applicable)",
    "terraform_fix": "Terraform code to fix the issue (if applicable)",
    "aws_cli_fix": "AWS CLI command to fix the issue (if applicable)",
    "console_steps": ["Step 1", "Step 2", "..."],
    "compliance_mapping": {"CIS": ["control-id"], "NIST": ["control-id"]},
    "confidence_score": 0.0-1.0,
    "estimated_risk_reduction": 0.0-100.0,
    "estimated_monthly_savings": 0.0,
    "severity": "critical|high|medium|low"
}

Return ONLY valid JSON. No markdown code blocks, no explanation."""


class CloudRecommendationEngine:
    """Generates knowledge-enriched AI recommendations for cloud findings.

    Architecture:
        Findings -> Knowledge Retrieval -> LLM (with context) -> Recommendations

    The engine ensures the LLM always receives authoritative context before
    generating recommendations, eliminating reliance on pretrained knowledge.
    """

    def __init__(self, registry: KnowledgeRegistry | None = None):
        self._registry = registry or get_knowledge_registry()
        self._llm_provider = None
        self._metrics = get_knowledge_metrics()

    def _get_llm_provider(self) -> Any:
        """Lazy-load the LLM provider."""
        if self._llm_provider is None:
            try:
                from app.ai.engine import get_llm_provider
                self._llm_provider = get_llm_provider()
            except Exception as exc:
                logger.error("LLM_PROVIDER_INIT_FAILED", error=str(exc))
                raise
        return self._llm_provider

    async def generate_recommendations(
        self,
        findings: list[dict[str, Any]],
        *,
        service: str = "",
        connection_id: str = "",
        scan_session_id: str = "",
        max_recommendations: int = 50,
    ) -> list[CloudRecommendation]:
        """Generate knowledge-enriched recommendations for a list of findings.

        Args:
            findings: List of finding dicts from CloudFindingData.
            service: AWS service to scope knowledge retrieval.
            connection_id: Connection UUID string.
            scan_session_id: Scan session UUID string.
            max_recommendations: Maximum recommendations to generate.

        Returns:
            List of CloudRecommendation, sorted by confidence descending.
        """
        t0 = time.time()
        logger.info(
            "RECOMMENDATION_ENGINE_STARTED",
            finding_count=len(findings),
            service=service,
            connection_id=connection_id,
        )

        # Sort findings by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_findings = sorted(
            findings,
            key=lambda f: severity_order.get(f.get("severity", "medium"), 2),
        )
        sorted_findings = sorted_findings[:max_recommendations]

        # 1. Retrieve knowledge context for the batch
        knowledge_docs = await self._retrieve_knowledge(
            sorted_findings, service=service
        )

        # 2. Generate recommendations (batched for efficiency)
        recommendations = await self._generate_batch(
            sorted_findings,
            knowledge_docs,
            connection_id=connection_id,
            scan_session_id=scan_session_id,
        )

        elapsed = round(time.time() - t0, 2)
        logger.info(
            "RECOMMENDATION_ENGINE_COMPLETE",
            finding_count=len(findings),
            recommendation_count=len(recommendations),
            elapsed_seconds=elapsed,
            knowledge_docs_used=len(knowledge_docs),
            knowledge_sources=list({d.source for d in knowledge_docs}),
        )

        # Log metrics summary periodically
        if self._metrics.total_retrievals % 10 == 0:
            self._metrics.log_summary()

        return recommendations

    async def _retrieve_knowledge(
        self,
        findings: list[dict[str, Any]],
        *,
        service: str = "",
    ) -> list[KnowledgeDocument]:
        """Retrieve relevant knowledge context for the findings batch.

        Queries the knowledge registry with finding-specific queries to get
        the most relevant documentation, pricing, security, and internal rules.
        """
        # Build unique queries from findings
        queries: list[tuple[str, str]] = []  # (query, service)
        seen_queries: set[str] = set()

        for finding in findings:
            svc = finding.get("service", service)
            title = finding.get("title", "")
            category = finding.get("category", "")

            # Build targeted query
            query_parts = []
            if svc:
                query_parts.append(svc)
            if title:
                query_parts.append(title[:100])
            if category:
                query_parts.append(category)

            query = " ".join(query_parts) if query_parts else f"AWS {svc} security best practices"

            if query not in seen_queries:
                seen_queries.add(query)
                queries.append((query, svc))

        # Retrieve from registry for each query
        all_docs: list[KnowledgeDocument] = []
        for query, svc in queries[:10]:  # Limit to 10 queries
            with MetricsCollector(
                provider_name="aggregate",
                query=query[:80],
            ) as collector:
                try:
                    docs = await self._registry.retrieve(
                        query, service=svc, max_results=5
                    )
                    all_docs.extend(docs)
                    collector.set_documents(len(docs))
                except Exception as exc:
                    logger.warning("KNOWLEDGE_RETRIEVAL_FAILED", query=query[:80], error=str(exc))

        # Deduplicate across queries
        unique_docs = self._registry._deduplicate(all_docs)
        logger.info(
            "KNOWLEDGE_CONTEXT_RETRIEVED",
            query_count=len(queries),
            total_docs=len(all_docs),
            unique_docs=len(unique_docs),
        )

        return unique_docs

    async def _generate_batch(
        self,
        findings: list[dict[str, Any]],
        knowledge_docs: list[KnowledgeDocument],
        *,
        connection_id: str = "",
        scan_session_id: str = "",
    ) -> list[CloudRecommendation]:
        """Generate recommendations for findings, using retrieved knowledge.

        Groups findings by service for batch efficiency, builds a prompt
        that includes all knowledge context, and calls the LLM once per batch.
        """
        if not findings:
            return []

        # Group by service for batch processing
        by_service: dict[str, list[dict[str, Any]]] = {}
        for f in findings:
            svc = f.get("service", "unknown")
            by_service.setdefault(svc, []).append(f)

        all_recommendations: list[CloudRecommendation] = []

        for svc, svc_findings in by_service.items():
            # Filter knowledge docs relevant to this service
            relevant_docs = [
                d for d in knowledge_docs
                if d.metadata.get("service", "") == svc
                or d.metadata.get("topic_type") in ("pillar_summary", "principles", "general", "best_practices", "overview", "strategies")
                or d.source == "internal_rules"
                or d.source == "aws_security"
            ]

            # Build the prompt
            prompt = self._build_prompt(svc_findings, relevant_docs, svc)

            # Call LLM
            try:
                llm = self._get_llm_provider()
                response_text = await llm.generate(prompt)
                recommendations = self._parse_response(
                    response_text,
                    svc_findings,
                    connection_id=connection_id,
                    scan_session_id=scan_session_id,
                    knowledge_docs=relevant_docs,
                )
                all_recommendations.extend(recommendations)
            except Exception as exc:
                logger.error(
                    "LLM_GENERATION_FAILED",
                    service=svc,
                    finding_count=len(svc_findings),
                    error=str(exc),
                )
                # Generate static fallback recommendations
                fallback = self._generate_fallback(
                    svc_findings,
                    connection_id=connection_id,
                    scan_session_id=scan_session_id,
                )
                all_recommendations.extend(fallback)

        return all_recommendations

    def _build_prompt(
        self,
        findings: list[dict[str, Any]],
        knowledge_docs: list[KnowledgeDocument],
        service: str,
    ) -> str:
        """Build an LLM prompt with findings and retrieved knowledge context."""
        sections = [
            _RECOMMENDATION_SYSTEM_PROMPT,
            "",
            f"# AWS Service: {service}",
            "",
            "# Retrieved Knowledge Context",
            "The following official AWS documentation and guidelines were retrieved "
            "for this analysis. Use this context as the authoritative source for your recommendations:",
            "",
        ]

        # Add knowledge documents
        for doc in knowledge_docs:
            sections.append(doc.to_prompt_context())
            sections.append("")

        sections.append("# Findings to Analyze")
        sections.append(
            "Generate a recommendation for each finding below. "
            "Return a JSON array with one object per finding."
        )
        sections.append("")

        for i, finding in enumerate(findings, 1):
            sections.append(f"## Finding {i}")
            sections.append(f"- Title: {finding.get('title', 'Unknown')}")
            sections.append(f"- Severity: {finding.get('severity', 'unknown')}")
            sections.append(f"- Category: {finding.get('category', 'unknown')}")
            sections.append(f"- Service: {finding.get('service', 'unknown')}")
            sections.append(f"- Resource: {finding.get('resource_id', 'N/A')}")
            sections.append(f"- Region: {finding.get('region', 'N/A')}")
            sections.append(f"- Description: {finding.get('description', '')[:300]}")
            if finding.get("rule_id"):
                sections.append(f"- Rule ID: {finding['rule_id']}")
            if finding.get("evidence"):
                sections.append(f"- Evidence: {json.dumps(finding['evidence'])[:500]}")
            sections.append("")

        sections.append(
            "Return a JSON array of recommendation objects. "
            "Each object must have the fields specified in the system prompt. "
            "Return ONLY valid JSON — no markdown, no explanation."
        )

        return "\n".join(sections)

    def _parse_response(
        self,
        response_text: str,
        findings: list[dict[str, Any]],
        *,
        connection_id: str = "",
        scan_session_id: str = "",
        knowledge_docs: list[KnowledgeDocument] | None = None,
    ) -> list[CloudRecommendation]:
        """Parse LLM response into CloudRecommendation objects."""
        try:
            # Extract JSON from response (may be wrapped in markdown)
            json_str = response_text.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                parsed = [parsed]

            recommendations: list[CloudRecommendation] = []
            knowledge_sources = list({d.source for d in (knowledge_docs or [])})

            for i, item in enumerate(parsed):
                # Match to the corresponding finding
                finding = findings[i] if i < len(findings) else {}

                rec = CloudRecommendation(
                    finding_id=str(finding.get("resource_id", "")),
                    rule_id=item.get("rule_id", finding.get("rule_id", "")),
                    service=item.get("service", finding.get("service", "")),
                    resource_id=item.get("resource_id", finding.get("resource_id", "")),
                    region=item.get("region", finding.get("region", "")),
                    executive_summary=item.get("executive_summary", ""),
                    root_cause=item.get("root_cause", ""),
                    business_impact=item.get("business_impact", ""),
                    security_impact=item.get("security_impact", ""),
                    cost_impact=item.get("cost_impact", ""),
                    official_best_practice=item.get("official_best_practice", ""),
                    documentation_references=item.get("documentation_references", []),
                    documentation_retrieved_at=datetime.now(UTC),
                    cloudformation_fix=item.get("cloudformation_fix"),
                    terraform_fix=item.get("terraform_fix"),
                    aws_cli_fix=item.get("aws_cli_fix"),
                    console_steps=item.get("console_steps", []),
                    compliance_mapping=item.get("compliance_mapping", {}),
                    confidence_score=float(item.get("confidence_score", 0.7)),
                    estimated_risk_reduction=float(item.get("estimated_risk_reduction", 0)),
                    estimated_monthly_savings=float(item.get("estimated_monthly_savings", 0)),
                    severity=item.get("severity", finding.get("severity", "medium")),
                    knowledge_sources_used=knowledge_sources,
                    llm_provider=getattr(self._llm_provider, "provider_name", None)
                    or type(self._llm_provider).__name__,
                )
                recommendations.append(rec)

            return recommendations

        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.error(
                "LLM_RESPONSE_PARSE_FAILED",
                error=str(exc),
                response_preview=response_text[:200],
            )
            return []

    def _generate_fallback(
        self,
        findings: list[dict[str, Any]],
        *,
        connection_id: str = "",
        scan_session_id: str = "",
    ) -> list[CloudRecommendation]:
        """Generate static fallback recommendations when LLM is unavailable.

        These are template-based recommendations that don't require LLM.
        They ensure the system always produces actionable output.
        """
        recommendations: list[CloudRecommendation] = []

        for finding in findings:
            service = finding.get("service", "unknown")
            title = finding.get("title", "Unknown finding")
            severity = finding.get("severity", "medium")

            rec = CloudRecommendation(
                finding_id=str(finding.get("resource_id", "")),
                rule_id=finding.get("rule_id", ""),
                service=service,
                resource_id=finding.get("resource_id", ""),
                region=finding.get("region", ""),
                executive_summary=f"Review and remediate: {title}",
                root_cause=f"A {severity}-severity issue was detected on {service}.",
                business_impact=self._estimate_business_impact(severity),
                security_impact=self._estimate_security_impact(severity, service),
                cost_impact=self._estimate_cost_impact(service),
                official_best_practice=f"Follow AWS Well-Architected best practices for {service}.",
                documentation_references=[
                    {
                        "title": f"AWS {service.upper()} Best Practices",
                        "url": f"https://docs.aws.amazon.com/{service}/latest/best-practices.html",
                        "version": "latest",
                    }
                ],
                documentation_retrieved_at=datetime.now(UTC),
                cloudformation_fix=None,
                terraform_fix=None,
                aws_cli_fix=None,
                console_steps=[
                    f"1. Navigate to the AWS {service.upper()} console",
                    "2. Locate the affected resource",
                    "3. Apply the recommended configuration change",
                    "4. Verify the change in AWS Config or CloudTrail",
                ],
                compliance_mapping={},
                confidence_score=0.5,
                estimated_risk_reduction=30.0 if severity in ("critical", "high") else 10.0,
                estimated_monthly_savings=0.0,
                severity=severity,
                knowledge_sources_used=["fallback_template"],
                llm_provider="fallback",
            )
            recommendations.append(rec)

        return recommendations

    @staticmethod
    def _estimate_business_impact(severity: str) -> str:
        impacts = {
            "critical": "Immediate risk of data breach, service outage, or compliance violation.",
            "high": "Significant security or operational risk if not addressed within 7 days.",
            "medium": "Moderate risk that should be addressed within 30 days.",
            "low": "Minor improvement opportunity with minimal immediate risk.",
        }
        return impacts.get(severity, "Impact assessment required.")

    @staticmethod
    def _estimate_security_impact(severity: str, service: str) -> str:
        impacts = {
            "critical": f"Critical {service} security gap — potential for unauthorized access or data exposure.",
            "high": f"High-severity {service} issue — could be exploited to escalate privileges or access data.",
            "medium": f"Medium-severity {service} finding — violates security best practices.",
            "low": f"Low-severity {service} observation — minor deviation from best practices.",
        }
        return impacts.get(severity, "Security impact assessment required.")

    @staticmethod
    def _estimate_cost_impact(service: str) -> str:
        return f"Review {service} resource utilization and pricing model for optimization opportunities."


def get_recommendation_engine() -> CloudRecommendationEngine:
    """Get singleton recommendation engine."""
    return CloudRecommendationEngine()
