"""Create RAG + MCP knowledge tables (Phase 1 knowledge foundation).

Adds the pgvector extension and three additive tables backing the RAG and
MCP layers:

- ``knowledge_documents`` — ingested knowledge artifacts with provenance.
- ``rag_chunks`` — embedded chunks (pgvector ``vector``) for semantic search.
- ``mcp_context`` — externally sourced context (live env / current docs).

No existing tables are modified. Requires pgvector on the PostgreSQL server
(see docker-compose image ``pgvector/pgvector:pg15-alpine``).

Revision ID: 032
Revises: 031
"""
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op
from app.config import settings

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("authority", sa.String(32), nullable=False, server_default="devarchai_curated"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False, server_default=""),
        sa.Column("version", sa.String(64), nullable=False, server_default=""),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("technology", sa.String(64), nullable=True),
        sa.Column("rule_id", sa.String(128), nullable=True),
        sa.Column("category", sa.String(32), nullable=True),
        sa.Column("severity", sa.String(16), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("rag_version", sa.String(16), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Ingested knowledge artifacts for the RAG layer",
    )
    op.create_index("ix_knowledge_documents_source_type", "knowledge_documents", ["source_type"])
    op.create_index("ix_knowledge_documents_source_name", "knowledge_documents", ["source_name"])
    op.create_index("ix_knowledge_documents_authority", "knowledge_documents", ["authority"])
    op.create_index("ix_knowledge_documents_technology", "knowledge_documents", ["technology"])
    op.create_index("ix_knowledge_documents_rule_id", "knowledge_documents", ["rule_id"])
    op.create_index("ix_knowledge_documents_category", "knowledge_documents", ["category"])
    op.create_index("ix_knowledge_documents_severity", "knowledge_documents", ["severity"])
    op.create_index("ix_knowledge_documents_rag_version", "knowledge_documents", ["rag_version"])
    op.create_unique_constraint("uq_knowledge_documents_fingerprint", "knowledge_documents", ["fingerprint"])

    op.create_table(
        "rag_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        # Dimension must match the active embedding model (EMBEDDING_DIMENSION),
        # the same value the RagChunk model uses. pgvector vector columns are
        # fixed-dimension: changing EMBEDDING_DIMENSION for an existing DB
        # requires recreating this column (or a fresh migration).
        sa.Column("embedding", Vector(settings.EMBEDDING_DIMENSION), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_rag_chunk_doc_index"),
        comment="Embedded chunks of RAG knowledge documents",
    )
    op.create_index("ix_rag_chunks_document_id", "rag_chunks", ["document_id"])

    op.create_table(
        "mcp_context",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("technology", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("request_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("source_label", sa.String(512), nullable=False, server_default=""),
        sa.Column("url", sa.String(1024), nullable=False, server_default=""),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Externally sourced context retrieved through the MCP layer",
    )
    op.create_index("ix_mcp_context_technology", "mcp_context", ["technology"])
    op.create_index("ix_mcp_context_provider", "mcp_context", ["provider"])
    op.create_index("ix_mcp_context_source_type", "mcp_context", ["source_type"])
    op.create_index("ix_mcp_context_status", "mcp_context", ["status"])
    op.create_index("ix_mcp_context_request_key", "mcp_context", ["request_key"])
    op.create_index("ix_mcp_context_content_hash", "mcp_context", ["content_hash"])


def downgrade() -> None:
    op.drop_table("mcp_context")
    op.drop_table("rag_chunks")
    op.drop_table("knowledge_documents")
