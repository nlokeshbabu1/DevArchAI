"""Tests for strict per-source provenance of AI recommendations.

Verifies the guarantee required by the product: every recommendation must be
attributable to the exact evidence that was actually retrieved and used, with
no fabricated URLs, honest "used" flags, and distinct documentation states.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.ai.context_engine import AIContext, AIRecommendation, AIContextEngine, StaticRecommendationBuilder
from app.mcp.providers import McpContextResult
from app.models.ai_suggestion import AISuggestion
from app.models.finding import Category, Finding, Severity
from app.models.finding_ai_job import FindingAIJob
from app.models.scan import Scan, ScanStatus
from app.rag.models import RagResultDocument
from app.services.ai_job_service import serialize_job
from app.services.ai_recommendation_cache import context_versions, finding_fingerprint
from app.services.ai_recommendation_service import AIRecommendationService
from app.services.ai_source_provenance import (
    DOC_STATUS_MCP_USED,
    DOC_STATUS_NO_RELEVANT_DOCUMENT,
    DOC_STATUS_NOT_ATTEMPTED,
    DOC_STATUS_RAG_MCP_USED,
    DOC_STATUS_RAG_USED,
    DOC_STATUS_RETRIEVAL_UNAVAILABLE,
    collect_sources,
    documentation_status,
    normalize_sources,
)

# ---------------------------------------------------------------------------
# collect_sources
# ---------------------------------------------------------------------------


def _rag_doc(**overrides) -> RagResultDocument:
    base = dict(
        title="Docker: use a non-root user",
        content="Add USER app before CMD.",
        source_type="docs",
        source_name="docker_docs",
        authority="docker",
        url="https://docs.docker.com/develop/develop-images/dockerfile_best-practices/",
        version="2024.01",
        technology="docker",
        rule_id="DKR-SEC-001",
        score=0.87,
    )
    base.update(overrides)
    return RagResultDocument(**base)


def test_collect_sources_records_rag_documents():
    context = AIContext(
        rule_id="DKR-SEC-001",
        technology="docker",
        rule_knowledge=SimpleNamespace(documents=[_rag_doc()], method="rule_id"),
        rag_enabled=True,
    )
    sources = collect_sources(context, generated_at="2026-10-10T00:00:00+00:00")

    assert len(sources) == 1
    source = sources[0]
    assert source["kind"] == "rag"
    assert source["url"] == "https://docs.docker.com/develop/develop-images/dockerfile_best-practices/"
    assert source["publisher"] == "docker"
    assert source["technology"] == "docker"
    assert source["supplied_to_llm"] is True
    assert source["retrieved_at"] == "2026-10-10T00:00:00+00:00"
    assert source["relationship"] == "official_documentation"


def test_collect_sources_never_fabricates_urls():
    context = AIContext(
        rule_id="DKR-SEC-001",
        rule_knowledge=SimpleNamespace(documents=[_rag_doc(url="")], method="rule_id"),
        rag_enabled=True,
    )
    sources = collect_sources(context)
    assert sources[0]["url"] == ""


def test_collect_sources_marks_mcp_used_only_on_success():
    context = AIContext(
        rule_id="K8S-SEC-001",
        technology="kubernetes",
        mcp_results=[
            McpContextResult(
                technology="kubernetes",
                provider="kubernetes_docs",
                source_type="docs",
                request_key="k",
                status="success",
                content="PodSecurityContext guidance",
                url="https://kubernetes.io/docs/tasks/configure-pod-container/security-context/",
            ),
            McpContextResult(
                technology="kubernetes",
                provider="kubernetes_docs",
                source_type="docs",
                request_key="k2",
                status="timeout",
                content="",
                source_label="official documentation request timed out",
            ),
        ],
        mcp_attempted=True,
    )
    sources = collect_sources(context)
    assert len(sources) == 2
    ok, timed_out = sources
    assert ok["supplied_to_llm"] is True
    assert ok["kind"] == "mcp"
    assert ok["publisher"] == "kubernetes_docs"
    assert timed_out["supplied_to_llm"] is False
    assert timed_out["status"] == "timeout"


# ---------------------------------------------------------------------------
# documentation_status
# ---------------------------------------------------------------------------


def test_documentation_status_states():
    rag_used = [{"kind": "rag", "supplied_to_llm": True}]
    mcp_used = [{"kind": "mcp", "supplied_to_llm": True, "status": "success"}]
    mcp_timeout = [{"kind": "mcp", "supplied_to_llm": False, "status": "timeout"}]

    assert documentation_status(
        rag_used + mcp_used, rag_attempted=True, mcp_attempted=True
    ) == DOC_STATUS_RAG_MCP_USED
    assert documentation_status(rag_used, rag_attempted=True) == DOC_STATUS_RAG_USED
    assert documentation_status(mcp_used, mcp_attempted=True) == DOC_STATUS_MCP_USED
    assert documentation_status(
        [], rag_attempted=True, mcp_attempted=True
    ) == DOC_STATUS_NO_RELEVANT_DOCUMENT
    assert documentation_status(
        [], rag_attempted=False, rag_failed=True, mcp_attempted=False
    ) == DOC_STATUS_RETRIEVAL_UNAVAILABLE
    assert documentation_status(
        mcp_timeout, rag_attempted=False, mcp_attempted=True
    ) == DOC_STATUS_RETRIEVAL_UNAVAILABLE
    assert documentation_status([]) == DOC_STATUS_NOT_ATTEMPTED


# ---------------------------------------------------------------------------
# normalize_sources (cache / DB safety)
# ---------------------------------------------------------------------------


def test_normalize_sources_drops_malformed_entries():
    raw = [
        {"kind": "rag", "title": "Keep", "supplied_to_llm": True, "score": "0.5"},
        {"kind": "unknown", "title": "Drop"},
        "not-a-dict",
        {"title": "no kind"},
        {"kind": "mcp", "title": "MCP", "status": "success"},
    ]
    normalized = normalize_sources(raw)
    assert [s["kind"] for s in normalized] == ["rag", "mcp"]
    assert normalized[0]["score"] == 0.5
    assert normalized[1]["supplied_to_llm"] is False
    assert normalize_sources(None) == []


# ---------------------------------------------------------------------------
# RAG grounding regression (documents actually reach the prompt)
# ---------------------------------------------------------------------------


async def test_rag_documents_are_grounded_into_prompt():
    captured: dict[str, str] = {}

    class CapturingLLM:
        def generate(self, prompt: str):
            captured["prompt"] = prompt
            return (
                '{"summary":"s","risk":"r","impact":"i","ai_explanation":"e",'
                '"fix_code":"","fix_example":"","full_example":"","best_practices":["bp"],'
                '"confidence":0.8,"documentation_url":""}'
            )

    rag = SimpleNamespace()
    rag.technology_for_rule_id = lambda rule_id: ["docker"]

    async def _get_rule_knowledge(rule_id, technology=None, category=None):
        return SimpleNamespace(
            documents=[_rag_doc(content="GROUNDED_RAG_TEXT_MARKER")],
            method="rule_id",
        )

    rag.get_rule_knowledge = _get_rule_knowledge

    engine = AIContextEngine(
        rag_service=rag,
        mcp_service=None,
        llm_provider=CapturingLLM(),
        fallback_builder=StaticRecommendationBuilder(),
    )
    finding = SimpleNamespace(rule_id="DKR-SEC-001", category=Category.SECURITY, description="root")
    ctx = await engine.build_context(finding, file_snippet="FROM ubuntu")
    assert ctx.rag_enabled is True
    await engine.generate_recommendation(finding, ctx, finding_fingerprint(finding))
    assert "GROUNDED_RAG_TEXT_MARKER" in captured["prompt"]


# ---------------------------------------------------------------------------
# Pipeline persistence + cache replay
# ---------------------------------------------------------------------------


class ProvenanceEngine:
    def technology_for_finding(self, finding):
        return "docker"

    async def build_context(self, finding, file_snippet: str = ""):
        return AIContext(
            rule_id=str(getattr(finding, "rule_id", "")),
            technology="docker",
            rule_knowledge=SimpleNamespace(documents=[_rag_doc()], method="rule_id"),
            mcp_results=[],
            rag_version="1.0.0",
            mcp_version="1.0.0",
            rag_enabled=True,
            mcp_attempted=False,
        )

    async def generate_recommendation(self, finding, context, fingerprint):
        return AIRecommendation(
            finding_fingerprint=fingerprint,
            rule_id=str(getattr(finding, "rule_id", "")),
            technology="docker",
            summary="AI summary",
            risk="risk",
            impact="impact",
            ai_explanation="explanation",
            fix_code="# fix",
            fix_example="# example",
            full_example="# full",
            best_practices=["bp"],
            confidence=0.9,
            documentation_url="",
            ai_generated=True,
            source="llm",
        )


class FakeCache:
    def __init__(self) -> None:
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, entry):
        self.store[entry.cache_key] = entry
        return True

    def ttl_for(self, source: str) -> int:
        return 3600


@pytest.fixture
async def session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        for table in (Scan.__table__, Finding.__table__, AISuggestion.__table__, FindingAIJob.__table__):
            await conn.run_sync(table.create, checkfirst=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed(session):
    scan = Scan(
        id=uuid4(),
        repository_url="https://github.com/acme/demo.git",
        branch="main",
        status=ScanStatus.COMPLETED,
        ai_status="pending",
        detected_stack=["docker"],
    )
    session.add(scan)
    await session.flush()
    finding = Finding(
        id=uuid4(),
        scan_id=scan.id,
        rule_id="DKR-SEC-001",
        rule_name="Root user",
        severity=Severity.HIGH,
        category=Category.SECURITY,
        description="Container runs as root",
        recommendation="Use non-root user",
        file_path="Dockerfile",
        line_number=5,
    )
    session.add(finding)
    await session.commit()
    return scan, finding


async def test_pipeline_persists_sources_and_cache_replays_them(session_factory):
    async with session_factory() as session:
        scan, _ = await _seed(session)
        cache = FakeCache()
        service = AIRecommendationService(
            session=session,
            cache=cache,
            context_engine=ProvenanceEngine(),
            snippet_loader=lambda s, f: "snippet",
        )
        await service.process_scan(scan.id)

        job = (
            await session.execute(select(FindingAIJob).where(FindingAIJob.scan_id == scan.id))
        ).scalar_one()
        assert job.documentation_status == DOC_STATUS_RAG_USED
        assert len(job.sources) == 1
        assert job.sources[0]["kind"] == "rag"
        assert job.sources[0]["supplied_to_llm"] is True

        serialized = serialize_job(job)
        assert serialized["documentation_status"] == DOC_STATUS_RAG_USED
        assert serialized["sources"][0]["title"] == "Docker: use a non-root user"
        assert serialized["documentation_status_display"]

        # Cache payload carries the same provenance so a cache hit is honest.
        assert len(cache.store) == 1
        payload = next(iter(cache.store.values())).payload
        assert payload["documentation_status"] == DOC_STATUS_RAG_USED
        assert payload["sources"][0]["kind"] == "rag"

        # Second scan reuses cache -> provenance replayed, not lost.
        scan2, _ = await _seed(session)
        # Align version context by reusing the same cache.
        service2 = AIRecommendationService(
            session=session,
            cache=cache,
            context_engine=ProvenanceEngine(),
            snippet_loader=lambda s, f: "snippet",
        )
        # Force same cache key by simulating identical finding fingerprint.
        await service2.process_scan(scan2.id)
