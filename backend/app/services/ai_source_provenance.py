"""Structured, persisted provenance for AI recommendation sources.

The AI recommendation pipeline assembles grounded context from the RAG layer
(internal rule knowledge) and the MCP layer (live / official documentation).
This module normalizes that context into a stable, user-facing list of source
records so every recommendation can be attributed to the exact evidence that
informed it.

Guarantees enforced here:

* **No fabrication** — only sources that were actually retrieved are recorded.
  URLs are copied verbatim from the retrieved document/result (never invented);
  an empty URL stays empty.
* **Honest "used" flag** — ``supplied_to_llm`` is True only for sources that
  were formatted into the LLM prompt. Failed / timed-out / skipped MCP
  fetches are recorded with ``supplied_to_llm=False`` so the UI can explain
  *why* documentation is missing.
* **Cache-safe** — the records are deterministic for a given context, so they
  can be persisted in the recommendation cache and replayed on a cache hit
  without drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Source kinds ---------------------------------------------------------------

SOURCE_KIND_RAG = "rag"
SOURCE_KIND_MCP = "mcp"

# Documentation status -------------------------------------------------------

DOC_STATUS_RAG_USED = "rag_used"
DOC_STATUS_MCP_USED = "mcp_used"
DOC_STATUS_RAG_MCP_USED = "rag_mcp_used"
DOC_STATUS_NO_RELEVANT_DOCUMENT = "no_relevant_document"
DOC_STATUS_RETRIEVAL_UNAVAILABLE = "retrieval_unavailable"
DOC_STATUS_NOT_ATTEMPTED = "not_attempted"

DOCUMENTATION_STATUS_DISPLAY: dict[str, str] = {
    DOC_STATUS_RAG_USED: "Grounded in internal knowledge base",
    DOC_STATUS_MCP_USED: "Grounded in live documentation",
    DOC_STATUS_RAG_MCP_USED: "Grounded in internal knowledge base + live documentation",
    DOC_STATUS_NO_RELEVANT_DOCUMENT: "No matching documentation found",
    DOC_STATUS_RETRIEVAL_UNAVAILABLE: "Documentation retrieval unavailable",
    DOC_STATUS_NOT_ATTEMPTED: "Static remediation guidance",
}

# Human labels for the retrieval relationship ---------------------------------

_RELATIONSHIP_BY_SOURCE_TYPE: dict[str, str] = {
    "live": "live_environment",
    "docs": "official_documentation",
    "curated": "curated_knowledge",
    "external": "external_reference",
}

_DOC_METHOD_BY_SOURCE_TYPE: dict[str, str] = {
    "live": "mcp_live",
    "docs": "mcp_docs",
}

_MCP_FAILURE_STATUSES = {"failed", "timeout", "skipped"}


@dataclass
class SourceRecord:
    """A single, attributable piece of evidence behind a recommendation."""

    kind: str
    title: str
    url: str = ""
    publisher: str = ""
    retrieval_method: str = ""
    relationship: str = ""
    status: str = "used"
    supplied_to_llm: bool = False
    retrieved_at: str = ""
    version: str = ""
    technology: str | None = None
    rule_id: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind,
            "title": self.title,
            "url": self.url,
            "publisher": self.publisher,
            "retrieval_method": self.retrieval_method,
            "relationship": self.relationship,
            "status": self.status,
            "supplied_to_llm": self.supplied_to_llm,
            "retrieved_at": self.retrieved_at,
            "version": self.version,
        }
        if self.technology:
            payload["technology"] = self.technology
        if self.rule_id:
            payload["rule_id"] = self.rule_id
        if self.score is not None:
            payload["score"] = round(float(self.score), 4)
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _relationship_for_source_type(source_type: str | None) -> str:
    return _RELATIONSHIP_BY_SOURCE_TYPE.get((source_type or "").lower(), "reference")


def _doc_retrieval_method(source_type: str | None) -> str:
    return _DOC_METHOD_BY_SOURCE_TYPE.get((source_type or "").lower(), "rag")


def _iso_or_none(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat() if value.tzinfo else value.replace(tzinfo=UTC).isoformat()
    return ""


def collect_sources(context: Any, *, generated_at: str | None = None) -> list[dict[str, Any]]:
    """Normalize an assembled :class:`AIContext` into source records.

    Only RAG documents that were actually retrieved and MCP results that were
    actually requested are recorded. Never raises.
    """
    if context is None:
        return []

    retrieved_at = generated_at or _now_iso()
    records: list[SourceRecord] = []

    rule_knowledge = getattr(context, "rule_knowledge", None)
    documents = _context_rag_documents(rule_knowledge)
    for doc in documents:
        records.append(_rag_record(doc, retrieved_at=retrieved_at))

    for mcp_result in getattr(context, "mcp_results", None) or []:
        record = _mcp_record(mcp_result, retrieved_at=retrieved_at)
        if record is not None:
            records.append(record)

    return [record.to_dict() for record in records]


def _context_rag_documents(rule_knowledge: Any) -> list[Any]:
    if rule_knowledge is None:
        return []
    documents = getattr(rule_knowledge, "documents", None)
    if documents:
        return list(documents)
    # Defensive: tolerate callers/doubles that expose chunks instead.
    chunks = getattr(rule_knowledge, "chunks", None)
    return list(chunks) if chunks else []


def _rag_record(doc: Any, *, retrieved_at: str) -> SourceRecord:
    source_type = str(getattr(doc, "source_type", "") or "")
    title = (
        str(getattr(doc, "title", "") or "").strip()
        or str(getattr(doc, "source_name", "") or "").strip()
        or "Internal knowledge base document"
    )
    score = getattr(doc, "score", None)
    try:
        score_value = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_value = None
    content = str(getattr(doc, "content", "") or getattr(doc, "text", "") or "")
    supplied = bool(content.strip())
    return SourceRecord(
        kind=SOURCE_KIND_RAG,
        title=title,
        url=str(getattr(doc, "url", "") or ""),
        publisher=str(getattr(doc, "authority", "") or getattr(doc, "source_name", "") or ""),
        retrieval_method=_doc_retrieval_method(source_type),
        relationship=_relationship_for_source_type(source_type),
        status="used" if supplied else "empty",
        supplied_to_llm=supplied,
        retrieved_at=retrieved_at,
        version=str(getattr(doc, "version", "") or ""),
        technology=getattr(doc, "technology", None),
        rule_id=getattr(doc, "rule_id", None),
        score=score_value,
        metadata={"source_type": source_type} if source_type else {},
    )


def _mcp_record(mcp_result: Any, *, retrieved_at: str) -> SourceRecord | None:
    provider = str(getattr(mcp_result, "provider", "") or "").strip()
    source_type = str(getattr(mcp_result, "source_type", "") or "").strip()
    status = str(getattr(mcp_result, "status", "") or "unknown").strip().lower()
    content = str(getattr(mcp_result, "content", "") or "")
    title = (
        str(getattr(mcp_result, "source_label", "") or "").strip()
        or str(getattr(mcp_result, "technology", "") or "").strip()
        or provider
        or "Live documentation"
    )
    if not provider and not title:
        return None
    supplied = status == "success" and bool(content.strip())
    return SourceRecord(
        kind=SOURCE_KIND_MCP,
        title=title,
        url=str(getattr(mcp_result, "url", "") or ""),
        publisher=provider,
        retrieval_method=_doc_retrieval_method(source_type) or "mcp",
        relationship=_relationship_for_source_type(source_type),
        status=status or "unknown",
        supplied_to_llm=supplied,
        retrieved_at=retrieved_at,
        technology=getattr(mcp_result, "technology", None),
        metadata={
            "source_type": source_type,
            "provider": provider,
        },
    )


def documentation_status(
    sources: list[dict[str, Any]],
    *,
    rag_attempted: bool = False,
    rag_failed: bool = False,
    mcp_attempted: bool = False,
) -> str:
    """Classify the documentation outcome for a recommendation.

    Distinct from the coarse ``source`` label so the UI can show explicit
    "no relevant document" / "retrieval unavailable" states.
    """
    rag_used = any(
        s.get("kind") == SOURCE_KIND_RAG and s.get("supplied_to_llm")
        for s in sources
    )
    mcp_used = any(
        s.get("kind") == SOURCE_KIND_MCP and s.get("supplied_to_llm")
        for s in sources
    )
    if rag_used and mcp_used:
        return DOC_STATUS_RAG_MCP_USED
    if rag_used:
        return DOC_STATUS_RAG_USED
    if mcp_used:
        return DOC_STATUS_MCP_USED

    if not rag_attempted and not rag_failed and not mcp_attempted:
        return DOC_STATUS_NOT_ATTEMPTED
    mcp_failed = any(
        s.get("kind") == SOURCE_KIND_MCP and s.get("status") in _MCP_FAILURE_STATUSES
        for s in sources
    )
    if rag_failed and not mcp_attempted:
        return DOC_STATUS_RETRIEVAL_UNAVAILABLE
    if mcp_attempted and mcp_failed and not (rag_attempted or rag_failed):
        return DOC_STATUS_RETRIEVAL_UNAVAILABLE
    return DOC_STATUS_NO_RELEVANT_DOCUMENT


def documentation_status_display(status: str | None) -> str:
    if not status:
        return DOCUMENTATION_STATUS_DISPLAY[DOC_STATUS_NOT_ATTEMPTED]
    return DOCUMENTATION_STATUS_DISPLAY.get(status, status)


def normalize_sources(raw: Any) -> list[dict[str, Any]]:
    """Sanitize sources loaded from a cache payload or job row.

    Drops anything that is not a well-formed record so the API never returns
    arbitrary cached content.
    """
    if not isinstance(raw, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip().lower()
        if kind not in {SOURCE_KIND_RAG, SOURCE_KIND_MCP}:
            continue
        record = {
            "kind": kind,
            "title": str(item.get("title") or ""),
            "url": str(item.get("url") or ""),
            "publisher": str(item.get("publisher") or ""),
            "retrieval_method": str(item.get("retrieval_method") or ""),
            "relationship": str(item.get("relationship") or ""),
            "status": str(item.get("status") or "used"),
            "supplied_to_llm": bool(item.get("supplied_to_llm")),
            "retrieved_at": str(item.get("retrieved_at") or ""),
            "version": str(item.get("version") or ""),
        }
        for optional in ("technology", "rule_id"):
            if item.get(optional):
                record[optional] = str(item[optional])
        if item.get("score") is not None:
            try:
                record["score"] = float(item["score"])
            except (TypeError, ValueError):
                pass
        if isinstance(item.get("metadata"), dict):
            record["metadata"] = item["metadata"]
        normalized.append(record)
    return normalized
