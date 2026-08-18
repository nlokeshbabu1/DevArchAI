"""Knowledge Registry — manages providers and aggregates retrieval.

The registry is the single entry point for the recommendation engine.
It manages all knowledge providers, handles caching, and returns
deduplicated, relevance-sorted results.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.knowledge.base import KnowledgeDocument, KnowledgeProvider
from app.knowledge.cache import KnowledgeCache, get_knowledge_cache
from app.knowledge.metrics import MetricsCollector, get_knowledge_metrics

logger = logging.getLogger(__name__)


class KnowledgeRegistry:
    """Central registry for all knowledge providers.

    Responsibilities:
      - Register/unregister providers
      - Retrieve knowledge from all relevant providers (with caching)
      - Deduplicate and rank results by relevance
      - Provide health checks for all providers
    """

    def __init__(self, cache: KnowledgeCache | None = None):
        self._providers: dict[str, KnowledgeProvider] = {}
        self._cache = cache or get_knowledge_cache()
        self._metrics = get_knowledge_metrics()

    def register(self, provider: KnowledgeProvider) -> None:
        """Register a knowledge provider."""
        self._providers[provider.name] = provider
        logger.info(
            f"KNOWLEDGE_PROVIDER_REGISTERED provider={provider.name} "
            f"description={provider.description}"
        )

    def unregister(self, name: str) -> None:
        """Remove a provider by name."""
        self._providers.pop(name, None)

    @property
    def providers(self) -> dict[str, KnowledgeProvider]:
        return dict(self._providers)

    async def retrieve(
        self,
        query: str,
        *,
        service: str = "",
        region: str = "",
        provider_names: list[str] | None = None,
        max_results: int = 10,
        use_cache: bool = True,
    ) -> list[KnowledgeDocument]:
        """Retrieve knowledge from all registered providers.

        Args:
            query: Natural language query.
            service: AWS service to scope results.
            region: AWS region for pricing/regional guidance.
            provider_names: If specified, only query these providers.
            max_results: Maximum total documents to return.
            use_cache: Whether to use the cache.

        Returns:
            Deduplicated, relevance-sorted list of documents.
        """
        t0 = time.time()
        target_providers = provider_names or list(self._providers.keys())

        # 1. Check cache for aggregate query
        cache_key_query = f"{query}:{service}:{region}"
        if use_cache:
            cached = await self._cache.get("_aggregate", cache_key_query, service, region)
            if cached:
                logger.info(
                    "KNOWLEDGE_RETRIEVAL_CACHE_HIT",
                    query=query[:80],
                    doc_count=len(cached),
                )
                return cached[:max_results]

        # 2. Retrieve from all target providers
        all_documents: list[KnowledgeDocument] = []
        for name in target_providers:
            provider = self._providers.get(name)
            if not provider:
                continue
            with MetricsCollector(provider_name=name, query=query[:80]) as collector:
                try:
                    docs = await provider.retrieve(
                        query, service=service, region=region, max_results=max_results
                    )
                    all_documents.extend(docs)
                    collector.set_documents(len(docs))
                    logger.debug(
                        "KNOWLEDGE_PROVIDER_RETRIEVED",
                        provider=name,
                        doc_count=len(docs),
                    )
                except Exception as exc:
                    logger.error(
                        "KNOWLEDGE_PROVIDER_FAILED",
                        provider=name,
                        error=str(exc),
                    )

        # 3. Deduplicate by title similarity
        deduplicated = self._deduplicate(all_documents)

        # 4. Sort by relevance score
        deduplicated.sort(key=lambda d: d.relevance_score, reverse=True)

        # 5. Cache the aggregate result
        if use_cache and deduplicated:
            await self._cache.set(
                "_aggregate", cache_key_query, deduplicated, service, region
            )

        elapsed_ms = round((time.time() - t0) * 1000, 1)
        logger.info(
            f"KNOWLEDGE_RETRIEVAL_COMPLETE query={query[:80]} "
            f"provider_count={len(target_providers)} total_docs={len(all_documents)} "
            f"deduplicated_docs={len(deduplicated)} elapsed_ms={elapsed_ms}"
        )

        return deduplicated[:max_results]

    async def health_check(self) -> dict[str, bool]:
        """Check health of all registered providers."""
        results: dict[str, bool] = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results

    async def cache_stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        return await self._cache.stats()

    def get_metrics_summary(self) -> dict[str, Any]:
        """Return knowledge retrieval metrics summary."""
        return self._metrics.get_summary()

    @staticmethod
    def _deduplicate(documents: list[KnowledgeDocument]) -> list[KnowledgeDocument]:
        """Remove near-duplicate documents based on title similarity."""
        seen_titles: set[str] = set()
        unique: list[KnowledgeDocument] = []
        for doc in documents:
            # Normalize title for dedup
            normalized = doc.title.lower().strip()
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique.append(doc)
        return unique


# Singleton
_registry: KnowledgeRegistry | None = None


def get_knowledge_registry() -> KnowledgeRegistry:
    global _registry
    if _registry is None:
        _registry = KnowledgeRegistry()
    return _registry
