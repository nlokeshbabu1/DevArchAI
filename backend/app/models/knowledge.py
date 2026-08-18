"""RAG + MCP knowledge layer database models.

These tables back the Phase 1 knowledge foundation:

- ``knowledge_documents``: a single ingested knowledge artifact (a rule
  documentation page, official doc, or curated entry). Carries provenance
  metadata (source_type, source_name, authority, version) plus the
  technology/rule_id/category/severity tags used for rule-id-first retrieval.
- ``rag_chunks``: chunked, embedded slices of a document. The ``embedding``
  column is a pgvector ``vector``; semantic retrieval orders by cosine
  distance (``<=>``).
- ``mcp_context``: externally sourced context (live environment data or
  current official docs) fetched through the MCP layer. Records the source,
  status, latency, and a content hash for caching/audit.

These tables are purely additive: no existing scanner/rule/scan tables are
modified.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class KnowledgeDocument(Base):
    """A single ingested knowledge artifact for the RAG layer."""

    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    source_type: Mapped[str] = mapped_column(sa.String(32), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(sa.String(128), nullable=False, index=True)
    authority: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, default="devarchai_curated", index=True,
    )
    title: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    url: Mapped[str] = mapped_column(sa.String(1024), nullable=False, default="")
    version: Mapped[str] = mapped_column(sa.String(64), nullable=False, default="")
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    technology: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, index=True)
    rule_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(sa.String(32), nullable=True, index=True)
    severity: Mapped[str | None] = mapped_column(sa.String(16), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", postgresql.JSONB, nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    rag_version: Mapped[str] = mapped_column(sa.String(16), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(
        sa.String(64), nullable=False, unique=True, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )


class RagChunk(Base):
    """A chunk of an ingested document, with its embedding."""

    __tablename__ = "rag_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    chunk_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    token_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    embedding: Mapped[list | None] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION), nullable=True,
        comment="Embedding vector (pgvector). Semantic search orders by cosine distance (<=>).",
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", postgresql.JSONB, nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=_utcnow,
    )

    __table_args__ = (
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_rag_chunk_doc_index"),
    )


class McpContext(Base):
    """Externally sourced context retrieved through the MCP layer."""

    __tablename__ = "mcp_context"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    technology: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, index=True,  # doc | live
    )
    request_key: Mapped[str] = mapped_column(sa.String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, index=True,  # success | failed | timeout | skipped
    )
    content: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")
    source_label: Mapped[str] = mapped_column(sa.String(512), nullable=False, default="")
    url: Mapped[str] = mapped_column(sa.String(1024), nullable=False, default="")
    latency_ms: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    content_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", postgresql.JSONB, nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=_utcnow,
    )


__all__ = ["KnowledgeDocument", "RagChunk", "McpContext"]
