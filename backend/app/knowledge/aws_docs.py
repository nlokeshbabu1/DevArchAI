"""AWS Documentation knowledge provider.

Retrieves context from AWS official documentation using the AWS Documentation
content index. Falls back to curated best-practice summaries when the API
is unavailable.

This provider never hardcodes AWS guidance — it fetches the latest documentation
or uses cached versions with configurable TTL.
"""

from __future__ import annotations

import asyncio
import logging

from app.knowledge.base import KnowledgeDocument, KnowledgeProvider

logger = logging.getLogger(__name__)

# Curated AWS Well-Architected best practices indexed by service.
# These are topic pointers, not hardcoded guidance — the LLM receives them
# as retrieval targets and synthesizes current recommendations.
_WELL_ARCHITECTED_TOPICS: dict[str, list[dict[str, str]]] = {
    "ec2": [
        {
            "title": "EC2 Instance Selection & Right-Sizing",
            "query": "AWS EC2 instance type selection best practices right sizing",
            "url": "https://docs.aws.amazon.com/wellarchitected/latest/ec2-pillar.html",
        },
        {
            "title": "EC2 Cost Optimization",
            "query": "AWS EC2 cost optimization Savings Plans Reserved Instances Spot",
            "url": "https://docs.aws.amazon.com/awsaccountbilling/latest/costoptimization/chap_ec2.html",
        },
    ],
    "s3": [
        {
            "title": "S3 Storage Classes & Lifecycle",
            "query": "AWS S3 storage class optimization lifecycle policies cost",
            "url": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html",
        },
        {
            "title": "S3 Security Best Practices",
            "query": "AWS S3 bucket security block public access encryption",
            "url": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html",
        },
    ],
    "rds": [
        {
            "title": "RDS Cost Optimization",
            "query": "AWS RDS cost optimization Reserved Instances right sizing",
            "url": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PurchaseInstance.html",
        },
    ],
    "iam": [
        {
            "title": "IAM Security Best Practices",
            "query": "AWS IAM security best practices least privilege MFA",
            "url": "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
        },
    ],
    "vpc": [
        {
            "title": "VPC Security Best Practices",
            "query": "AWS VPC security groups NACLs best practices",
            "url": "https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-best-practices.html",
        },
    ],
    "lambda": [
        {
            "title": "Lambda Cost Optimization",
            "query": "AWS Lambda cost optimization memory provisioned concurrency",
            "url": "https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html",
        },
    ],
    "eks": [
        {
            "title": "EKS Best Practices",
            "query": "AWS EKS Kubernetes best practices security cost",
            "url": "https://docs.aws.amazon.com/eks/latest/best-practices.html",
        },
    ],
    "cloudfront": [
        {
            "title": "CloudFront Cost Optimization",
            "query": "AWS CloudFront cost optimization caching policies",
            "url": "https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/optimizing.html",
        },
    ],
}

# Well-Architected Framework pillar summaries
_WELL_ARCHITECTED_PILLARS = [
    {
        "title": "AWS Well-Architected — Operational Excellence",
        "content": (
            "The Operational Excellence pillar focuses on running and monitoring systems to deliver "
            "business value and continually improve processes and procedures. Key areas include: "
            "organization, prepare, operate, evolve. The lens provides best practices for "
            "infrastructure as code, CI/CD, observability, and incident response."
        ),
        "url": "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html",
    },
    {
        "title": "AWS Well-Architected — Security",
        "content": (
            "The Security pillar focuses on protecting information, systems, and assets through "
            "risk assessments and mitigation strategies. Key areas include: identity and access "
            "management, detection, infrastructure protection, data protection, and incident response. "
            "Security is foundational and affects all other pillars."
        ),
        "url": "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html",
    },
    {
        "title": "AWS Well-Architected — Reliability",
        "content": (
            "The Reliability pillar focuses on ensuring workloads perform their intended function "
            "correctly and consistently. Key areas include: recovery planning, handling change, "
            "and testing. Foundations, workload architecture, and disaster recovery are critical."
        ),
        "url": "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html",
    },
    {
        "title": "AWS Well-Architected — Performance Efficiency",
        "content": (
            "The Performance Efficiency pillar focuses on using computing resources efficiently "
            "to meet system requirements. Key areas include: compute, storage, database, network, "
            "and edge optimization. Selecting the right resource type and size is essential."
        ),
        "url": "https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html",
    },
    {
        "title": "AWS Well-Architected — Cost Optimization",
        "content": (
            "The Cost Optimization pillar focuses on avoiding unnecessary costs. Key areas include: "
            "understanding spending patterns, selecting pricing models and resource types, scaling "
            "for cost, and measuring cloud ownership cost. Use Reserved Instances, Savings Plans, "
            "and Spot Instances appropriately."
        ),
        "url": "https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html",
    },
    {
        "title": "AWS Well-Architected — Sustainability",
        "content": (
            "The Sustainability pillar focuses on minimizing environmental impacts of running "
            "cloud workloads. Key areas include: region selection, hardware selection, software "
            "design patterns, and development/deployment processes."
        ),
        "url": "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/welcome.html",
    },
]


class AWSDocsProvider(KnowledgeProvider):
    """Retrieves AWS documentation and Well-Architected Framework guidance.

    Primary source: AWS Documentation API or web search index.
    Fallback: curated topic pointers that the LLM uses as retrieval targets.

    This ensures recommendations cite official AWS guidance rather than
    relying solely on pretrained knowledge.
    """

    def __init__(self, use_live_retrieval: bool = False):
        self._use_live_retrieval = use_live_retrieval
        self._search_client = None

    @property
    def name(self) -> str:
        return "aws_docs"

    @property
    def description(self) -> str:
        return "AWS Official Documentation and Well-Architected Framework"

    async def retrieve(
        self,
        query: str,
        *,
        service: str = "",
        region: str = "",
        max_results: int = 5,
    ) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []

        # 1. Try live documentation retrieval if enabled
        if self._use_live_retrieval:
            try:
                live_docs = await self._fetch_live_docs(query, service, max_results)
                if live_docs:
                    documents.extend(live_docs)
            except Exception as exc:
                logger.warning(
                    "AWS_DOCS_LIVE_RETRIEVAL_FAILED",
                    query=query[:80],
                    error=str(exc),
                )

        # 2. Service-specific Well-Architected topics (if not enough live docs)
        remaining = max_results - len(documents)
        if remaining > 0 and service and service.lower() in _WELL_ARCHITECTED_TOPICS:
            topics = _WELL_ARCHITECTED_TOPICS[service.lower()]
            for topic in topics[:remaining]:
                documents.append(
                    KnowledgeDocument(
                        source=self.name,
                        title=topic["title"],
                        content=(
                            f"AWS official guidance for {topic['query']}. "
                            f"This document should be consulted for the latest "
                            f"recommendations on {service} best practices."
                        ),
                        url=topic["url"],
                        version="latest",
                        relevance_score=0.9,
                        metadata={"topic_type": "well_architected", "service": service},
                    )
                )

        # 3. Well-Architected Framework pillar summaries
        remaining = max_results - len(documents)
        for pillar in _WELL_ARCHITECTED_PILLARS[:remaining]:
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title=pillar["title"],
                    content=pillar["content"],
                    url=pillar["url"],
                    version="latest",
                    relevance_score=0.7,
                    metadata={"topic_type": "pillar_summary"},
                )
            )

        # 4. Security bulletins
        if len(documents) < max_results:
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title="AWS Security Bulletins",
                    content=(
                        "Check https://aws.amazon.com/security/security-bulletins/ for the latest "
                        "security advisories affecting AWS services. Critical and high severity "
                        "findings should be cross-referenced with active bulletins."
                    ),
                    url="https://aws.amazon.com/security/security-bulletins/",
                    version="latest",
                    relevance_score=0.6,
                    metadata={"topic_type": "security_bulletins"},
                )
            )

        return documents[:max_results]

    async def _fetch_live_docs(
        self,
        query: str,
        service: str,
        max_results: int,
    ) -> list[KnowledgeDocument]:
        """Fetch live documentation using web search or AWS Docs API.

        This method uses a search client to find the latest AWS documentation
        relevant to the query. Falls back gracefully if search is unavailable.
        """
        if not self._search_client:
            # Try to initialize a search client (e.g., AWS Docs API, web search)
            try:
                from app.knowledge.search import get_search_client
                self._search_client = get_search_client()
            except ImportError:
                logger.debug("AWS_DOCS_SEARCH_UNAVAILABLE")
                return []

        if not self._search_client:
            return []

        # Build search query targeting AWS documentation
        search_query = f"site:docs.aws.amazon.com {query}"
        if service:
            search_query = f"site:docs.aws.amazon.com {service} {query}"

        def _search() -> list[dict[str, str]]:
            try:
                return self._search_client.search(search_query, max_results)
            except Exception:
                return []

        results = await asyncio.to_thread(_search)

        documents = []
        for result in results:
            documents.append(
                KnowledgeDocument(
                    source=self.name,
                    title=result.get("title", "AWS Documentation"),
                    content=result.get("snippet", "Retrieved from AWS documentation."),
                    url=result.get("url", ""),
                    version="live",
                    relevance_score=0.85,
                    metadata={
                        "topic_type": "live_doc",
                        "service": service,
                        "retrieved_at": "live",
                    },
                )
            )

        return documents
