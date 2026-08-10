"""Scan AI Recommendation model — L2 persisted recommendation cache.

One row per deterministic, versioned recommendation ``cache_key``. A cache
key is derived from the finding fingerprint + rule + technology + context
versions, so identical findings across scans (and across 100 duplicate
findings in one scan) share a single cached recommendation.

This is the persisted layer of the layered cache (L1 = Redis, L2 = this
table). It is scan-independent: rows are keyed by content, not by scan, so
re-scans of the same repository or scans of identical findings never
re-pay the LLM/MCP/RAG cost.

It is intentionally distinct from the cloud subsystem's
``AIRecommendation`` (``cloud_connections`` scope).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ScanAIRecommendation(Base):
    """Cached AI recommendation for a normalized repository finding."""

    __tablename__ = "scan_ai_recommendations"
    __table_args__ = (
        {"comment": "Cached AI recommendations for repository scan findings"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    # Deterministic, versioned key (see app.services.ai_recommendation_cache).
    cache_key = Column(String(64), nullable=False, unique=True, index=True)
    finding_fingerprint = Column(String(64), nullable=False, index=True)
    rule_id = Column(String(50), nullable=False, index=True)
    technology = Column(String(100), nullable=True, index=True)

    # Context versions that produced this recommendation. Changing any of
    # these changes the cache key, which invalidates stale entries.
    rag_version = Column(String(32), nullable=False, server_default=text("''"))
    mcp_version = Column(String(32), nullable=False, server_default=text("''"))
    prompt_version = Column(String(32), nullable=False, server_default=text("''"))
    model_version = Column(String(64), nullable=False, server_default=text("''"))

    # The recommendation payload (JSON) and its provenance.
    payload = Column(JSONB, nullable=False)
    source = Column(String(20), nullable=False, server_default=text("'llm'"))
    ai_generated = Column(Boolean, nullable=False, server_default=text("false"))

    # Optional reference to the first finding that produced this cache entry.
    origin_finding_id = Column(
        UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Cache semantics.
    ttl_seconds = Column(Integer, nullable=False, server_default=text("0"))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=_utcnow,
        nullable=False,
    )

    origin_finding = relationship("Finding")

    @property
    def expired(self) -> bool:
        return self.expires_at <= datetime.now(UTC)

    def is_fresh(self, ttl_seconds: int | None = None) -> bool:
        """Whether the entry is still usable for caching purposes."""
        ttl = ttl_seconds or self.ttl_seconds or 0
        if ttl > 0 and (datetime.now(UTC) - self.created_at) > timedelta(seconds=ttl):
            return False
        return not self.expired

    def __repr__(self) -> str:
        return f"<ScanAIRecommendation(cache_key={self.cache_key}, source={self.source})>"
