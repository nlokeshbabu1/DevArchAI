"""Knowledge Retrieval Layer — provider-agnostic context for AI recommendations.

This module provides a pluggable knowledge retrieval system that ensures
the AI recommendation engine never relies solely on LLM pretrained knowledge.
Instead, it retrieves authoritative context from:

- AWS Official Documentation
- AWS Well-Architected Framework
- AWS Pricing API
- AWS Cost Explorer
- AWS Trusted Advisor
- AWS Service Quotas
- AWS Security Bulletins
- CIS AWS Benchmark
- NIST 800-53
- Internal DevArchAI Rules

Architecture:
    Knowledge Providers → Registry → Cache → Recommendation Engine → LLM

Usage:
    from app.knowledge import get_knowledge_registry

    registry = get_knowledge_registry()
    docs = await registry.retrieve("EC2 security best practices", service="ec2")
"""

from app.knowledge.base import KnowledgeDocument, KnowledgeProvider
from app.knowledge.cache import KnowledgeCache, get_knowledge_cache
from app.knowledge.metrics import (
    KnowledgeRetrievalMetrics,
    MetricsCollector,
    get_knowledge_metrics,
)
from app.knowledge.registration import initialize_knowledge_system, register_providers
from app.knowledge.registry import KnowledgeRegistry, get_knowledge_registry
from app.knowledge.search import SearchClient, get_search_client

__all__ = [
    # Core types
    "KnowledgeDocument",
    "KnowledgeProvider",
    "KnowledgeRegistry",
    # Registry functions
    "get_knowledge_registry",
    "register_providers",
    "initialize_knowledge_system",
    # Cache
    "KnowledgeCache",
    "get_knowledge_cache",
    # Metrics
    "KnowledgeRetrievalMetrics",
    "MetricsCollector",
    "get_knowledge_metrics",
    # Search
    "SearchClient",
    "get_search_client",
]
