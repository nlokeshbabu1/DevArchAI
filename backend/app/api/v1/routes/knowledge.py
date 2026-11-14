"""RAG + MCP knowledge API routes (Phase 1 knowledge foundation).

Exposes the RAG knowledge service and the MCP live-context gateway without
touching the scan pipeline. Used by the future AI recommendation pipeline and
by operators/UI to inspect what DevArchAI knows and whether live context is
needed.

Endpoints:
- ``GET  /knowledge/status`` — RAG + MCP status
- ``GET  /knowledge/technologies`` — technologies in the knowledge inventory
- ``POST /knowledge/retrieve`` — RAG retrieval (rule-id / technology / query)
- ``GET  /knowledge/rules/{rule_id}`` — rule-id-first RAG retrieval
- ``POST /knowledge/seed`` — (re)seed the RAG store from the inventory
- ``GET  /knowledge/mcp/requires-live`` — does a technology need live context?
- ``POST /knowledge/mcp/context`` — fetch current live/docs context
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import get_optional_user, require_admin
from app.config import settings
from app.mcp.service import get_mcp_service
from app.models.user import User
from app.rag.service import get_rag_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class RetrieveRequest(BaseModel):
    query: str = Field("", description="Free-form query text")
    rule_id: str | None = Field(None, description="Exact or prefix rule ID for rule-id-first retrieval")
    technology: str | None = Field(None, description="Restrict to a technology")
    category: str | None = Field(None, description="Restrict to a rule category")
    severity: str | None = Field(None, description="Restrict to a severity")
    k: int | None = Field(None, ge=1, le=50, description="Max documents to return")


class McpContextRequest(BaseModel):
    technology: str = Field(..., description="Technology to fetch current context for")
    rule_id: str | None = Field(None, description="Optional rule ID (used for routing decisions)")
    query: str = Field("", description="Optional request context text")
    connection_id: str | None = Field(None, description="Cloud connection id for live AWS/Azure context")
    skip_cache: bool = Field(False, description="Bypass the MCP result cache")


# ---------------------------------------------------------------------------
# RAG routes
# ---------------------------------------------------------------------------

@router.get("/status")
async def rag_status(current_user: User | None = Depends(get_optional_user)):
    """RAG + MCP layer status (knowledge version, embedding provider, cache)."""
    service = get_rag_service()
    stats = await service.stats()
    mcp_stats = await get_mcp_service().stats()
    return {"rag": stats, "mcp": mcp_stats}


@router.get("/technologies")
async def rag_technologies(current_user: User | None = Depends(get_optional_user)):
    """List all technologies known to the RAG inventory."""
    service = get_rag_service()
    return {
        "technologies": service.technologies(),
        "inventory_version": service.inventory_version,
    }


@router.post("/retrieve")
async def rag_retrieve(
    request: RetrieveRequest,
    current_user: User | None = Depends(get_optional_user),
):
    """Retrieve RAG knowledge for a query / rule / technology."""
    if not request.rule_id and not request.query:
        raise HTTPException(status_code=400, detail="Provide a query or rule_id")
    service = get_rag_service()
    context = await service.retrieve_context(
        request.query,
        rule_id=request.rule_id,
        technology=request.technology,
        category=request.category,
        severity=request.severity,
        k=request.k,
    )
    return context.to_dict(content_preview=True)


@router.get("/rules/{rule_id}")
async def rag_rule_knowledge(
    rule_id: str,
    technology: str | None = Query(None),
    category: str | None = Query(None),
    current_user: User | None = Depends(get_optional_user),
):
    """Retrieve everything DevArchAI knows about a rule_id."""
    service = get_rag_service()
    context = await service.get_rule_knowledge(
        rule_id, technology=technology, category=category
    )
    return context.to_dict(content_preview=True)


@router.post("/seed")
async def rag_seed(_admin: User = Depends(require_admin)):
    """(Re)seed the RAG store from the technology inventory. Idempotent."""
    service = get_rag_service()
    count = await service.seed_from_inventory()
    return {"success": True, "documents_created_or_updated": count}


@router.post("/re-embed")
async def rag_re_embed(_admin: User = Depends(require_admin)):
    """Backfill embeddings for chunks stored without them (semantic search).

    Idempotent: only chunks with a NULL embedding are touched.
    """
    service = get_rag_service()
    count = await service.re_embed()
    return {"success": True, "chunks_embedded": count}


@router.get("/health")
async def knowledge_health(current_user: User | None = Depends(get_optional_user)):
    """Verify the RAG + MCP knowledge layer works end-to-end."""
    service = get_rag_service()
    mcp_service = get_mcp_service()

    # 1. RAG: retrieve a known rule to confirm documents are queryable.
    probe_rule = "k8s_single_replica"
    rag_docs = 0
    try:
        ctx = await service.get_rule_knowledge(probe_rule)
        rag_docs = len(getattr(ctx, "documents", []) or [])
    except Exception:
        rag_docs = 0

    # 2. MCP: confirm routing works and providers are configured.
    try:
        mcp_routes_live = bool(mcp_service.requires_live_context("aws"))
    except Exception:
        mcp_routes_live = False
    try:
        mcp_stats = await mcp_service.stats()
    except Exception:
        mcp_stats = {}
    mcp_enabled = bool(mcp_stats.get("enabled", False))
    router = mcp_stats.get("router", {}) or {}
    providers = router.get("providers", []) or []
    mcp_providers = [getattr(p, "name", p.get("name")) if isinstance(p, dict) else getattr(p, "name", "") for p in providers]

    embedding = getattr(service, "embedding_provider", "unknown")

    return {
        "rag": {
            "enabled": settings.RAG_ENABLED,
            "documents_queryable": rag_docs,
            "probe_rule": probe_rule,
        },
        "mcp": {
            "enabled": mcp_enabled,
            "providers_configured": mcp_providers,
            "routes_live": mcp_routes_live,
        },
        "embedding_provider": embedding,
        "healthy": settings.RAG_ENABLED and rag_docs > 0,
    }


# ---------------------------------------------------------------------------
# MCP routes
# ---------------------------------------------------------------------------

@router.get("/mcp/requires-live")
async def mcp_requires_live(
    technology: str = Query(..., description="Technology to check"),
    rule_id: str | None = Query(None),
    current_user: User | None = Depends(get_optional_user),
):
    """Whether live environment data is the primary context source."""
    return {
        "technology": technology,
        "requires_live_context": get_mcp_service().requires_live_context(
            technology, rule_id
        ),
    }


@router.post("/mcp/context")
async def mcp_context(
    request: McpContextRequest,
    current_user: User | None = Depends(get_optional_user),
):
    """Fetch current live/docs context for a technology (never raises)."""
    service = get_mcp_service()
    results = await service.get_live_context(
        request.technology,
        rule_id=request.rule_id,
        query=request.query,
        connection_id=request.connection_id,
        skip_cache=request.skip_cache,
    )
    return {"results": [r.to_dict() for r in results]}
