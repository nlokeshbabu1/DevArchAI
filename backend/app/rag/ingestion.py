"""RAG ingestion pipeline.

Loads knowledge into the RAG store via a deterministic pipeline:

    Loader -> Cleaner -> Chunker -> Metadata -> Embedding -> pgvector store

Documents are upserted idempotently by ``fingerprint`` so re-ingestion never
duplicates content. Chunking reuses LangChain's recursive text splitter
(already a project dependency).

Embeddings are optional: if the active embedding provider is unavailable, the
document is stored without embeddings and retrieval degrades to keyword /
rule-id matching.
"""

from __future__ import annotations

import hashlib
import re

import sqlalchemy as sa
import structlog

from app.config import settings
from app.db.session import get_session_factory
from app.models.knowledge import KnowledgeDocument, RagChunk
from app.rag.embeddings import EmbeddingDimensionError, EmbeddingUnavailable, get_embedding_router
from app.rag.inventory import get_inventory
from app.rag.models import KnowledgeDocumentInput

logger = structlog.get_logger(__name__)


class DocumentCleaner:
    """Normalizes document text before chunking."""

    _BLOCK_PATTERNS = (
        re.compile(r"[ \t]{2,}"),
        re.compile(r"\n{3,}"),
        re.compile(r"\r\n"),
    )

    def clean(self, text: str) -> str:
        text = text.strip()
        for pattern in self._BLOCK_PATTERNS:
            text = pattern.sub(" " if pattern is self._BLOCK_PATTERNS[0] else "\n", text)
        return text


def _default_splitter():
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


class RagIngestionService:
    """Ingests knowledge documents into the RAG store."""

    def __init__(self, cleaner: DocumentCleaner | None = None) -> None:
        self._cleaner = cleaner or DocumentCleaner()
        self._session_factory = get_session_factory()

    def _chunk_text(self, content: str) -> list[str]:
        splitter = _default_splitter()
        chunks = splitter.split_text(content)
        return [c for c in chunks if c.strip()]

    def _embed(self, chunks: list[str]) -> list[list[float]] | None:
        """Embed chunks; returns None (no embeddings) on graceful degradation."""
        try:
            return get_embedding_router().embed_texts(chunks)
        except (EmbeddingUnavailable, EmbeddingDimensionError) as exc:
            logger.warning("RAG_EMBEDDING_DEGRADED", reason=str(exc))
            return None

    @staticmethod
    def _token_estimate(text: str) -> int:
        return max(1, len(text) // 4)

    async def ingest_document(
        self,
        doc: KnowledgeDocumentInput,
        *,
        embeddings_required: bool = False,
    ) -> bool:
        """Ingest (or upsert) a single document.

        Args:
            doc: Document to ingest.
            embeddings_required: If True, embedding failure raises instead of
                degrading (used by seeding when semantic search is expected).

        Returns:
            True if the document was created/updated, False if unchanged.
        """
        cleaned = self._cleaner.clean(doc.content)
        if not cleaned:
            logger.debug("RAG_SKIP_EMPTY_DOCUMENT", title=doc.title)
            return False

        chunks = self._chunk_text(cleaned)
        vectors = self._embed(chunks)
        if vectors is None and embeddings_required:
            raise EmbeddingUnavailable("embeddings required but unavailable")

        rag_version = doc.rag_version or settings.RAG_VERSION
        fingerprint = doc.fingerprint
        content_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

        async with self._session_factory() as session:
            existing = await session.execute(
                sa.select(KnowledgeDocument).where(
                    KnowledgeDocument.fingerprint == fingerprint
                )
            )
            row = existing.scalar_one_or_none()

            if row is not None:
                if row.metadata_json.get("content_hash") == content_hash:
                    return False
                doc_id = row.id
                row.title = doc.title
                row.url = doc.url
                row.version = doc.version
                row.content = cleaned
                row.source_type = doc.source_type
                row.source_name = doc.source_name
                row.authority = doc.authority
                row.technology = doc.technology
                row.rule_id = doc.rule_id
                row.category = doc.category
                row.severity = doc.severity
                row.rag_version = rag_version
                row.metadata_json = dict(doc.metadata, content_hash=content_hash)
                # Drop old chunks; re-add below.
                await session.execute(
                    sa.delete(RagChunk).where(RagChunk.document_id == doc_id)
                )
            else:
                doc_id = None
                row = KnowledgeDocument(
                    source_type=doc.source_type,
                    source_name=doc.source_name,
                    authority=doc.authority,
                    title=doc.title,
                    url=doc.url,
                    version=doc.version,
                    content=cleaned,
                    technology=doc.technology,
                    rule_id=doc.rule_id,
                    category=doc.category,
                    severity=doc.severity,
                    metadata_json=dict(doc.metadata, content_hash=content_hash),
                    rag_version=rag_version,
                    fingerprint=fingerprint,
                )
                session.add(row)
                await session.flush()
                doc_id = row.id

            for index, chunk_text in enumerate(chunks):
                session.add(
                    RagChunk(
                        document_id=doc_id,
                        chunk_index=index,
                        content=chunk_text,
                        token_count=self._token_estimate(chunk_text),
                        embedding=vectors[index] if vectors else None,
                        metadata_json={
                            "technology": doc.technology,
                            "rule_id": doc.rule_id,
                            "category": doc.category,
                        },
                    )
                )

            await session.commit()
            logger.info(
                "RAG_DOCUMENT_INGESTED",
                title=doc.title,
                technology=doc.technology,
                rule_id=doc.rule_id,
                chunks=len(chunks),
                embedded=vectors is not None,
            )
            return True

    async def ingest_many(
        self,
        docs: list[KnowledgeDocumentInput],
        *,
        embeddings_required: bool = False,
    ) -> int:
        """Ingest many documents; returns number created/updated."""
        count = 0
        for doc in docs:
            if await self.ingest_document(doc, embeddings_required=embeddings_required):
                count += 1
        return count

    async def ingest_inventory(self) -> int:
        """Seed the RAG store from the technology inventory.

        Creates one curated document per canonical rule id (tagged with its
        technology and category) plus one per cross-cutting rule id, so the
        rule-id-first retrieval path has real data to match. Idempotent by
        fingerprint.
        """
        inventory = get_inventory()
        docs: list[KnowledgeDocumentInput] = []

        for tech_id in inventory.technologies():
            tech = inventory.get_technology(tech_id)
            if not tech:
                continue
            rule_ids = inventory.rule_ids_for(tech_id)
            scanners = inventory.external_scanners_for(tech_id)
            categories = inventory.categories_for_technology(tech_id)
            for rule_id in rule_ids:
                docs.append(
                    KnowledgeDocumentInput(
                        source_type="curated",
                        source_name="technology_inventory",
                        authority="devarchai_curated",
                        title=f"Rule {rule_id} — {tech_id}",
                        content=(
                            f"# {rule_id}\n\n"
                            f"Technology: {tech_id}. Canonical rule id: {rule_id}.\n"
                            f"Cross-cutting categories: "
                            f"{', '.join(categories) or '(none)'}.\n"
                            f"External scanners that may enrich this finding: "
                            f"{', '.join(scanners) or '(none)'}."
                        ),
                        version=inventory.version,
                        technology=tech_id,
                        rule_id=rule_id,
                        category=categories[0] if categories else None,
                        metadata={"inventory_version": inventory.version},
                    )
                )

        for cat in inventory.cross_cutting():
            cat_id = cat["id"]
            for rule_id in cat.get("rule_ids", []):
                docs.append(
                    KnowledgeDocumentInput(
                        source_type="curated",
                        source_name="technology_inventory",
                        authority="devarchai_curated",
                        title=f"Rule {rule_id} — {cat_id}",
                        content=(
                            f"# {rule_id}\n\n"
                            f"Cross-cutting category: {cat_id}. Canonical rule id: {rule_id}."
                        ),
                        version=inventory.version,
                        technology=None,
                        rule_id=rule_id,
                        category=cat_id,
                        metadata={"inventory_version": inventory.version},
                    )
                )

        return await self.ingest_many(docs)


# Singleton
_ingestion_service: RagIngestionService | None = None


def get_ingestion_service() -> RagIngestionService:
    """Get the global RAG ingestion service singleton."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = RagIngestionService()
    return _ingestion_service
