"""RAG layer data models (ingestion inputs and retrieval results)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class SourceType:
    """Allowed knowledge source types (ordered by retrieval priority)."""

    LIVE_ENV = "live"      # live environment data (AWS/Azure state)
    OFFICIAL_DOCS = "docs"  # current official documentation
    CURATED = "curated"     # DevArchAI curated knowledge (inventory, internal rules)
    EXTERNAL = "external"   # general external knowledge

    ALL = {LIVE_ENV, OFFICIAL_DOCS, CURATED, EXTERNAL}


@dataclass(frozen=True)
class KnowledgeDocumentInput:
    """A document to ingest into the RAG knowledge store."""

    source_type: str
    source_name: str
    title: str
    content: str
    url: str = ""
    version: str = ""
    technology: str | None = None
    rule_id: str | None = None
    category: str | None = None
    severity: str | None = None
    authority: str = "devarchai_curated"
    metadata: dict[str, Any] = field(default_factory=dict)
    rag_version: str | None = None

    @property
    def fingerprint(self) -> str:
        """Deterministic idempotency key for upserting."""
        import hashlib

        raw = "|".join(
            [
                self.source_type,
                self.source_name,
                self.title,
                self.url,
                self.version,
                self.rule_id or "",
                self.technology or "",
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RagResultDocument:
    """A single retrieved knowledge document."""

    title: str
    content: str
    source_type: str
    source_name: str
    authority: str = "devarchai_curated"
    url: str = ""
    version: str = ""
    technology: str | None = None
    rule_id: str | None = None
    category: str | None = None
    severity: str | None = None
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "authority": self.authority,
            "url": self.url,
            "version": self.version,
            "technology": self.technology,
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "score": round(self.score, 4),
        }


@dataclass(frozen=True)
class RetrievedContext:
    """Result of a RAG retrieval operation."""

    query: str
    documents: list[RagResultDocument]
    method: str  # rule_id | technology | semantic | keyword
    total_available: int
    rag_version: str = ""

    def to_dict(self, content_preview: bool = True) -> dict[str, Any]:
        docs: list[dict[str, Any]] = []
        for d in self.documents:
            item = d.to_dict()
            if content_preview:
                item["content"] = (item["content"][:500] + "…") if len(item["content"]) > 500 else item["content"]
            docs.append(item)
        return {
            "query": self.query,
            "method": self.method,
            "document_count": len(docs),
            "total_available": self.total_available,
            "rag_version": self.rag_version,
            "documents": docs,
        }


# Source/authority priority for deterministic rule-id-first ordering.
# Live data > current official docs > DevArchAI curated > general external.
SOURCE_PRIORITY: dict[str, int] = {
    SourceType.LIVE_ENV: 0,
    SourceType.OFFICIAL_DOCS: 1,
    SourceType.CURATED: 2,
    SourceType.EXTERNAL: 3,
}
