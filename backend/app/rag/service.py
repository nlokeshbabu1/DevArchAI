"""RAG knowledge service — public facade for the RAG layer.

Combines ingestion (seeding from the technology inventory), retrieval
(rule-id-first / technology / semantic / keyword), caching, and versioning
into one interface used by the API layer.

RAG = "what DevArchAI knows". This service never touches the scan pipeline;
it only answers knowledge queries.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.config import settings
from app.rag.embeddings import get_embedding_router
from app.rag.ingestion import get_ingestion_service
from app.rag.inventory import get_inventory
from app.rag.models import RetrievedContext
from app.rag.retrieval import get_retrieval_service

logger = structlog.get_logger(__name__)


class RagKnowledgeService:
    """Facade over ingestion + retrieval + inventory."""

    def __init__(self) -> None:
        self._inventory = get_inventory()
        self._ingestion = get_ingestion_service()
        self._retrieval = get_retrieval_service()

    # ------------------------------------------------------------------
    # Knowledge queries
    # ------------------------------------------------------------------

    async def get_rule_knowledge(
        self,
        rule_id: str,
        technology: str | None = None,
        category: str | None = None,
        k: int | None = None,
    ) -> RetrievedContext:
        """Retrieve everything DevArchAI knows about a rule_id."""
        return await self._retrieval.retrieve(
            rule_id,
            rule_id=rule_id,
            technology=technology,
            category=category,
            k=k,
        )

    async def retrieve_context(
        self,
        query: str,
        *,
        technology: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        rule_id: str | None = None,
        k: int | None = None,
    ) -> RetrievedContext:
        """General knowledge retrieval with optional filters."""
        return await self._retrieval.retrieve(
            query,
            rule_id=rule_id,
            technology=technology,
            category=category,
            severity=severity,
            k=k,
        )

    def technologies(self) -> list[str]:
        return self._inventory.technologies()

    def technology_for_rule_id(self, rule_id: str) -> list[str]:
        return self._inventory.technology_for_rule_id(rule_id)

    # ------------------------------------------------------------------
    # Versioning / seeding / status
    # ------------------------------------------------------------------

    @property
    def knowledge_version(self) -> str:
        return settings.RAG_VERSION

    @property
    def inventory_version(self) -> str:
        return self._inventory.version

    @property
    def embedding_provider(self) -> str:
        router = get_embedding_router()
        if not router.is_semantic_available():
            return f"{router.provider}:unavailable"
        return router.provider

    async def seed_from_inventory(self) -> int:
        """Seed/refresh the knowledge store from the technology inventory."""
        count = await self._ingestion.ingest_inventory()
        logger.info("RAG_INVENTORY_SEEDED", documents=count)
        return count

    async def stats(self) -> dict[str, Any]:
        from app.rag.cache import get_rag_cache

        cache_stats = await get_rag_cache().stats()
        return {
            "enabled": settings.RAG_ENABLED,
            "knowledge_version": self.knowledge_version,
            "inventory_version": self.inventory_version,
            "embedding_provider": self.embedding_provider,
            "technologies": self.technologies(),
            "rule_count": len(self._inventory.all_rule_ids()),
            "cache": cache_stats,
        }


# Singleton
_rag_service: RagKnowledgeService | None = None


def get_rag_service() -> RagKnowledgeService:
    """Get the global RAG knowledge service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RagKnowledgeService()
    return _rag_service
