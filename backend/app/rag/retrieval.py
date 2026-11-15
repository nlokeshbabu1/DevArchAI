"""RAG retrieval service — rule-id-first, technology-aware retrieval.

Retrieval strategy (per the knowledge priority order: live env data > current
official docs > DevArchAI curated > general external):

1. **rule_id path**: exact (or prefix) match on ``rule_id``, plus optional
   technology/category/severity filters. Deterministic, no embeddings needed.
2. **technology path**: everything DevArchAI knows about a technology, with
   optional category/severity filters.
3. **semantic path**: pgvector cosine similarity over chunk embeddings with
   metadata filters. Used for free-form queries when embeddings are available.
4. **keyword fallback**: SQL ``ilike`` ranking when embeddings are unavailable
   (never fails the caller).

Results are cached in Redis (``devarchai:rag:chunk:{hash}``) and metrics are
recorded through ``app.services.metrics``.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
import structlog

from app.config import settings
from app.db.session import get_session_factory
from app.models.knowledge import KnowledgeDocument, RagChunk
from app.rag.cache import get_rag_cache, rag_cache_key
from app.rag.embeddings import get_embedding_router
from app.rag.models import (
    SOURCE_PRIORITY,
    RagResultDocument,
    RetrievedContext,
)
from app.services.metrics import (
    record_rag_cache_hit,
    record_rag_cache_miss,
    record_rag_retrieval,
)

logger = structlog.get_logger(__name__)


def _to_result_document(row: KnowledgeDocument, score: float = 0.0) -> RagResultDocument:
    return RagResultDocument(
        title=row.title,
        content=row.content,
        source_type=row.source_type,
        source_name=row.source_name,
        authority=row.authority,
        url=row.url,
        version=row.version,
        technology=row.technology,
        rule_id=row.rule_id,
        category=row.category,
        severity=row.severity,
        score=score,
    )


class RagRetrievalService:
    """Retrieves knowledge from the RAG store."""

    def __init__(self, session_factory: Any | None = None) -> None:
        self._session_factory = session_factory

    def _db_session_factory(self) -> Any:
        """Return the async session factory for the current event loop."""
        if self._session_factory is not None:
            return self._session_factory
        return get_session_factory()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        query: str,
        *,
        rule_id: str | None = None,
        technology: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        k: int | None = None,
        skip_cache: bool = False,
    ) -> RetrievedContext:
        """Retrieve knowledge context for a query.

        Args:
            query: Free-form query text (also the cache salt).
            rule_id: If provided, rule-id-first retrieval is used.
            technology: Restrict results to a technology.
            category: Restrict to a rule category.
            severity: Restrict to a severity.
            k: Max documents to return (default RAG_MAX_RESULTS).
            skip_cache: Bypass the Redis/in-memory cache.

        Returns:
            A RetrievedContext (never raises for missing knowledge).
        """
        k = k or settings.RAG_MAX_RESULTS
        filters: dict[str, Any] = {
            "rule_id": rule_id,
            "technology": technology,
            "category": category,
            "severity": severity,
            "k": k,
        }
        cache_key = rag_cache_key(query, filters)

        if not skip_cache:
            cached = await get_rag_cache().get(cache_key)
            if cached is not None:
                record_rag_cache_hit("rag")
                return RetrievedContext(
                    query=query,
                    documents=[
                        RagResultDocument(**d) for d in cached.get("documents", [])
                    ],
                    method=cached.get("method", "cache"),
                    total_available=cached.get("total_available", 0),
                    rag_version=cached.get("rag_version", settings.RAG_VERSION),
                )
            record_rag_cache_miss("rag")

        try:
            if rule_id:
                context = await self._retrieve_by_rule(
                    query, rule_id, technology, category, severity, k
                )
            elif technology:
                context = await self._retrieve_by_technology(
                    query, technology, category, severity, k
                )
            elif get_embedding_router().is_semantic_available():
                context = await self._retrieve_semantic(
                    query, technology, category, severity, k
                )
            else:
                context = await self._retrieve_keyword(
                    query, technology, category, severity, k
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("RAG_RETRIEVAL_ERROR", error=str(exc))
            record_rag_retrieval("failure", 0)
            context = RetrievedContext(
                query=query,
                documents=[],
                method="error",
                total_available=0,
                rag_version=settings.RAG_VERSION,
            )

        record_rag_retrieval("success", len(context.documents))
        if not skip_cache:
            await get_rag_cache().set(
                cache_key,
                {
                    "documents": [d.to_dict() for d in context.documents],
                    "method": context.method,
                    "total_available": context.total_available,
                    "rag_version": context.rag_version,
                },
            )
        return context

    # ------------------------------------------------------------------
    # Retrieval strategies
    # ------------------------------------------------------------------

    async def _retrieve_by_rule(
        self,
        query: str,
        rule_id: str,
        technology: str | None,
        category: str | None,
        severity: str | None,
        k: int,
    ) -> RetrievedContext:
        stmt = (
            sa.select(KnowledgeDocument)
            .where(KnowledgeDocument.rule_id.startswith(rule_id))
            .order_by(
                KnowledgeDocument.updated_at.desc(),
            )
        )
        stmt = self._apply_filters(stmt, technology, category, severity)
        async with self._db_session_factory()() as session:
            rows = (await session.execute(stmt)).scalars().all()

        ranked = sorted(
            rows,
            key=lambda r: (
                SOURCE_PRIORITY.get(r.source_type, 99),
                -len(r.rule_id or ""),
            ),
        )[:k]
        return RetrievedContext(
            query=query,
            documents=[_to_result_document(r) for r in ranked],
            method="rule_id",
            total_available=len(rows),
            rag_version=settings.RAG_VERSION,
        )

    async def _retrieve_by_technology(
        self,
        query: str,
        technology: str,
        category: str | None,
        severity: str | None,
        k: int,
    ) -> RetrievedContext:
        stmt = (
            sa.select(KnowledgeDocument)
            .where(KnowledgeDocument.technology == technology)
            .order_by(KnowledgeDocument.updated_at.desc())
        )
        stmt = self._apply_filters(stmt, technology, category, severity)
        async with self._db_session_factory()() as session:
            rows = (await session.execute(stmt)).scalars().all()

        ranked = sorted(
            rows,
            key=lambda r: (
                SOURCE_PRIORITY.get(r.source_type, 99),
                r.updated_at.timestamp() if r.updated_at else 0,
            ),
        )[:k]
        return RetrievedContext(
            query=query,
            documents=[_to_result_document(r) for r in ranked],
            method="technology",
            total_available=len(rows),
            rag_version=settings.RAG_VERSION,
        )

    async def _retrieve_semantic(
        self,
        query: str,
        technology: str | None,
        category: str | None,
        severity: str | None,
        k: int,
    ) -> RetrievedContext:
        router = get_embedding_router()
        query_vector = router.embed_query(query)

        base = (
            sa.select(
                RagChunk.document_id,
                RagChunk.content,
                RagChunk.embedding.cosine_distance(query_vector).label("distance"),
            )
            .join(KnowledgeDocument, KnowledgeDocument.id == RagChunk.document_id)
            .order_by("distance")
            .limit(k * 4)
        )
        base = self._apply_filters(base, technology, category, severity)

        async with self._db_session_factory()() as session:
            chunk_rows = (await session.execute(base)).all()
            if not chunk_rows:
                return RetrievedContext(
                    query=query,
                    documents=[],
                    method="semantic",
                    total_available=0,
                    rag_version=settings.RAG_VERSION,
                )

            doc_ids = [r.document_id for r in chunk_rows]
            doc_stmt = (
                sa.select(KnowledgeDocument)
                .where(KnowledgeDocument.id.in_(doc_ids))
            )
            doc_map = {
                d.id: d for d in (await session.execute(doc_stmt)).scalars().all()
            }

        ranked: list[tuple[KnowledgeDocument, float]] = []
        for row in chunk_rows:
            doc = doc_map.get(row.document_id)
            if doc is None:
                continue
            score = 1.0 - float(row.distance)
            ranked.append((doc, score))

        seen: set[str] = set()
        documents: list[RagResultDocument] = []
        for doc, score in ranked:
            if doc.fingerprint in seen:
                continue
            seen.add(doc.fingerprint)
            documents.append(_to_result_document(doc, score=score))
            if len(documents) >= k:
                break

        return RetrievedContext(
            query=query,
            documents=documents,
            method="semantic",
            total_available=len(ranked),
            rag_version=settings.RAG_VERSION,
        )

    async def _retrieve_keyword(
        self,
        query: str,
        technology: str | None,
        category: str | None,
        severity: str | None,
        k: int,
    ) -> RetrievedContext:
        terms = [t for t in query.lower().split() if len(t) > 2]
        if not terms:
            return RetrievedContext(
                query=query,
                documents=[],
                method="keyword",
                total_available=0,
                rag_version=settings.RAG_VERSION,
            )

        stmt = sa.select(KnowledgeDocument).limit(k * 4)
        stmt = self._apply_filters(stmt, technology, category, severity)
        async with self._db_session_factory()() as session:
            rows = (await session.execute(stmt)).scalars().all()

        scored: list[tuple[KnowledgeDocument, float]] = []
        for doc in rows:
            haystack = f"{doc.title} {doc.content}".lower()
            score: float = float(sum(haystack.count(term) for term in terms))
            if doc.rule_id and any(term in doc.rule_id.lower() for term in terms):
                score += 3.0
            if doc.technology and any(term in doc.technology.lower() for term in terms):
                score += 2.0
            if score > 0:
                scored.append((doc, score))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return RetrievedContext(
            query=query,
            documents=[_to_result_document(d, s) for d, s in scored[:k]],
            method="keyword",
            total_available=len(scored),
            rag_version=settings.RAG_VERSION,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_filters(stmt, technology: str | None, category: str | None, severity: str | None):
        if technology:
            stmt = stmt.where(KnowledgeDocument.technology == technology)
        if category:
            stmt = stmt.where(KnowledgeDocument.category == category)
        if severity:
            stmt = stmt.where(KnowledgeDocument.severity == severity)
        return stmt


# Singleton
_retrieval_service: RagRetrievalService | None = None


def get_retrieval_service() -> RagRetrievalService:
    """Get the global RAG retrieval service singleton."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RagRetrievalService()
    return _retrieval_service


def create_retrieval_service(session_factory: Any | None = None) -> RagRetrievalService:
    """Build a retrieval service bound to a specific async session factory."""
    if session_factory is None:
        return get_retrieval_service()
    return RagRetrievalService(session_factory=session_factory)
