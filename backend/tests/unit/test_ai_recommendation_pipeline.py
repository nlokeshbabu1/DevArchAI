"""Tests for the async AI recommendation pipeline (Phase 2).

Covers the 12 required scenarios:

1.  Scan completes without AI (enqueue is non-blocking, never raises).
2.  Cache hit → no LLM call.
3.  Cache miss → context engine generates + persists.
4.  Dedup: 100 identical findings → 1 LLM call, all applied.
5.  MCP not required → no live-context fetch.
6.  MCP required → live context fetched and grounded into the prompt.
7.  RAG failure → scan stays COMPLETED, fallback recommendation.
8.  LLM failure → scan stays COMPLETED, fallback recommendation.
9.  WebSocket per-finding update is broadcast.
10. Batch dedup across groups (distinct rules → one LLM call each).
11. Cache invalidation when a context version changes.
12. Restart recovery re-enqueues pending scans.

No real network, RAG, MCP, LLM, or Redis is used — everything is injected.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.ai.context_engine import AIRecommendation, AIContextEngine, StaticRecommendationBuilder
from app.models.ai_suggestion import AISuggestion
from app.models.finding import Category, Finding, Severity
from app.models.scan import Scan, ScanStatus
from app.models.scan_ai_recommendation import ScanAIRecommendation
from app.services.ai_recommendation_cache import (
    RecommendationEntry,
    config_digest,
    context_versions,
    finding_fingerprint,
    recommendation_cache_key,
)
from app.services.ai_recommendation_service import (
    AIRecommendationService,
    enqueue_ai_analysis_for_scan,
    run_ai_recommendations_for_scan,
)
from app.workers.tasks.ai_recommendations import recover_pending_ai_scans

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class FakeCache:
    """In-memory recommendation cache double."""

    def __init__(self) -> None:
        self.store: dict[str, RecommendationEntry] = {}
        self.get_calls = 0
        self.set_calls = 0

    async def get(self, key: str) -> RecommendationEntry | None:
        self.get_calls += 1
        return self.store.get(key)

    async def set(self, entry: RecommendationEntry) -> bool:
        self.set_calls += 1
        self.store[entry.cache_key] = entry
        return True

    def ttl_for(self, source: str) -> int:
        return 3600 if source in ("mcp", "live") else 86400


class FakeEngine:
    """Deterministic context-engine double for service-level tests."""

    def __init__(self) -> None:
        self.build_calls = 0
        self.generate_calls = 0
        self.llm_ok = True
        self.rag_fail = False
        self.mcp_required = False
        self.tech_by_rule: dict[str, str] = {}

    def technology_for_finding(self, finding: Any) -> str | None:
        return self.tech_by_rule.get(str(getattr(finding, "rule_id", "")))

    async def build_context(self, finding: Any, file_snippet: str = "") -> SimpleNamespace:
        self.build_calls += 1
        return SimpleNamespace(
            rule_id=str(getattr(finding, "rule_id", "")),
            technology=self.technology_for_finding(finding),
            rule_knowledge=None if self.rag_fail else SimpleNamespace(chunks=[]),
            mcp_results=[SimpleNamespace(status="success", content="live-ctx", source_type="docs", provider="docs")]
            if self.mcp_required
            else [],
            file_snippet=file_snippet,
            rag_version="1.0.0",
            mcp_version="1.0.0",
        )

    async def generate_recommendation(self, finding: Any, context: Any, fingerprint: str) -> AIRecommendation:
        self.generate_calls += 1
        return AIRecommendation(
            finding_fingerprint=fingerprint,
            rule_id=str(getattr(finding, "rule_id", "")),
            technology=context.technology,
            summary="AI summary",
            risk="AI risk",
            impact="AI impact",
            ai_explanation="AI explanation",
            fix_code="# fix",
            fix_example="# example",
            full_example="# full",
            best_practices=["bp1"],
            confidence=0.9,
            documentation_url="",
            ai_generated=self.llm_ok,
            source="llm" if self.llm_ok else "fallback",
        )


# ---------------------------------------------------------------------------
# In-memory database (only the tables the pipeline needs)
# ---------------------------------------------------------------------------


@pytest.fixture
async def session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        for table in (
            Scan.__table__,
            Finding.__table__,
            AISuggestion.__table__,
        ):
            await conn.run_sync(table.create, checkfirst=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _insert_scan(session, *, ai_status: str = "pending", detected_stack: list[str] | None = None) -> Scan:
    scan = Scan(
        id=uuid4(),
        repository_url="https://github.com/acme/demo.git",
        branch="main",
        status=ScanStatus.COMPLETED,
        ai_status=ai_status,
        detected_stack=detected_stack,
        completed_at=datetime.now(UTC),
    )
    session.add(scan)
    await session.commit()
    return scan


async def _insert_finding(
    session,
    scan_id,
    *,
    rule_id: str = "DKR-SEC-001",
    severity: Severity = Severity.HIGH,
    category: Category = Category.SECURITY,
    description: str = "Container runs as root.",
    recommendation: str = "Use a non-root user.",
    file_path: str = "Dockerfile",
    line_number: int = 5,
) -> Finding:
    finding = Finding(
        id=uuid4(),
        scan_id=scan_id,
        rule_id=rule_id,
        rule_name=f"Rule {rule_id}",
        severity=severity,
        category=category,
        description=description,
        recommendation=recommendation,
        file_path=file_path,
        line_number=line_number,
    )
    session.add(finding)
    await session.commit()
    return finding


def _make_service(session, engine=None, cache=None, **kwargs):
    return AIRecommendationService(
        session=session,
        cache=cache or FakeCache(),
        context_engine=engine or FakeEngine(),
        snippet_loader=lambda scan, finding: "file snippet",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 1. Scan completes without AI
# ---------------------------------------------------------------------------


def test_enqueue_never_blocks_or_raises_when_celery_down():
    with patch(
        "app.workers.tasks.ai_recommendations.enqueue_ai_analysis"
    ) as mock_task:
        mock_task.delay.side_effect = ConnectionError("broker down")
        with patch("app.config.settings.CELERY_AI_TASKS_ENABLED", True):
            enqueue_ai_analysis_for_scan(uuid4())
        mock_task.delay.assert_called_once()
        time.sleep(0.2)


def test_enqueue_uses_thread_by_default():
    scan_id = uuid4()
    with patch("app.workers.tasks.ai_recommendations.enqueue_ai_analysis") as mock_task:
        with patch("app.config.settings.CELERY_AI_TASKS_ENABLED", False):
            enqueue_ai_analysis_for_scan(scan_id)
        mock_task.delay.assert_not_called()


def test_enqueue_uses_celery_when_enabled():
    scan_id = uuid4()
    with patch("app.workers.tasks.ai_recommendations.enqueue_ai_analysis") as mock_task:
        with patch("app.config.settings.CELERY_AI_TASKS_ENABLED", True):
            enqueue_ai_analysis_for_scan(scan_id)
        mock_task.delay.assert_called_once_with(str(scan_id))


# ---------------------------------------------------------------------------
# 2. Cache hit / 3. cache miss
# ---------------------------------------------------------------------------


async def test_cache_miss_generates_and_persists(session_factory):
    async with session_factory() as session:
        scan = await _insert_scan(session)
        finding = await _insert_finding(session, scan.id)
        engine = FakeEngine()
        cache = FakeCache()
        service = _make_service(session, engine=engine, cache=cache)

        result = await service.process_scan(scan.id)

        assert engine.build_calls == 1
        assert engine.generate_calls == 1
        assert result.cache_hits == 0
        assert result.findings_updated == 1
        assert result.llm_calls == 1
        assert len(cache.store) == 1

        refreshed = await session.get(Scan, scan.id)
        assert refreshed.ai_status == "completed"
        assert refreshed.status == ScanStatus.COMPLETED
        assert refreshed.ai_completed_at is not None


async def test_cache_hit_skips_llm(session_factory):
    async with session_factory() as session:
        scan = await _insert_scan(session)
        finding = await _insert_finding(session, scan.id)
        key = recommendation_cache_key(
            "DKR-SEC-001",
            None,
            finding_fingerprint(finding),
            config_digest(scan.detected_stack),
            context_versions(),
        )
        cache = FakeCache()
        cache.store[key] = RecommendationEntry(
            cache_key=key,
            payload={"summary": "cached", "ai_generated": True, "rule_id": "DKR-SEC-001"},
            source="llm",
            ai_generated=True,
        )
        engine = FakeEngine()
        service = _make_service(session, engine=engine, cache=cache)

        result = await service.process_scan(scan.id)

        assert result.cache_hits == 1
        assert engine.build_calls == 0
        assert engine.generate_calls == 0
        assert result.findings_updated == 1
        refreshed = await session.get(Finding, finding.id)
        assert refreshed.summary == "cached"
        assert refreshed.ai_generated is True


# ---------------------------------------------------------------------------
# 4. Dedup: 100 identical findings → 1 LLM call
# ---------------------------------------------------------------------------


async def test_dedup_100_identical_findings_single_llm_call(session_factory):
    async with session_factory() as session:
        scan = await _insert_scan(session)
        for _ in range(100):
            await _insert_finding(
                session, scan.id, rule_id="DKR-SEC-001", description="same", file_path="Dockerfile"
            )
        engine = FakeEngine()
        service = _make_service(session, engine=engine, cache=FakeCache(), max_per_scan=100)

        result = await service.process_scan(scan.id)

        assert engine.generate_calls == 1
        assert result.groups == 1
        assert result.findings_processed == 100
        assert result.findings_updated == 100
        assert result.llm_calls == 1
        ai_findings = (
            await session.execute(
                select_findings(session, scan.id)
            )
        ).scalars().all()
        assert all(f.ai_generated for f in ai_findings)
        assert all(f.summary == "AI summary" for f in ai_findings)


def select_findings(session, scan_id):
    from sqlalchemy import select
    return select(Finding).where(Finding.scan_id == scan_id)


# ---------------------------------------------------------------------------
# 5. MCP not required / 6. MCP required
# ---------------------------------------------------------------------------


async def test_mcp_not_required_skips_live_fetch():
    mcp = MagicMock()
    mcp.requires_live_context.return_value = False
    mcp.requires_docs_context.return_value = False
    mcp.get_live_context = AsyncMock()
    rag = MagicMock()
    rag.technology_for_rule_id.return_value = ["docker"]
    rag.get_rule_knowledge = AsyncMock(return_value=SimpleNamespace(chunks=[]))
    engine = AIContextEngine(
        rag_service=rag, mcp_service=mcp, llm_provider=None, fallback_builder=StaticRecommendationBuilder()
    )
    finding = SimpleNamespace(
        rule_id="DKR-SEC-001", category=Category.SECURITY, description="root user"
    )
    ctx = await engine.build_context(finding, file_snippet="FROM ubuntu")
    assert ctx.mcp_results == []
    mcp.get_live_context.assert_not_called()


async def test_mcp_required_grounds_live_context_into_prompt():
    from app.mcp.providers import McpContextResult

    captured: dict[str, str] = {}

    class CapturingLLM:
        def generate(self, prompt: str):
            captured["prompt"] = prompt
            return '{"summary":"s","risk":"r","impact":"i","ai_explanation":"e",' \
                   '"fix_code":"","fix_example":"","full_example":"","best_practices":["bp"],' \
                   '"confidence":0.8,"documentation_url":""}'

    mcp = MagicMock()
    mcp.requires_live_context.return_value = True
    mcp.get_live_context = AsyncMock(
        return_value=[
            McpContextResult(
                technology="docker",
                provider="docs",
                source_type="docs",
                request_key="root",
                status="success",
                content="Docker best practice: use non-root user",
            )
        ]
    )
    rag = MagicMock()
    rag.technology_for_rule_id.return_value = ["docker"]
    rag.get_rule_knowledge = AsyncMock(
        return_value=SimpleNamespace(chunks=[SimpleNamespace(content="rule knowledge for DKR-SEC-001")])
    )
    engine = AIContextEngine(
        rag_service=rag, mcp_service=mcp, llm_provider=CapturingLLM(), fallback_builder=StaticRecommendationBuilder()
    )
    finding = SimpleNamespace(
        id=uuid4(),
        rule_id="DKR-SEC-001",
        rule_name="Root user",
        severity=Severity.HIGH,
        category=Category.SECURITY,
        description="Container runs as root",
        recommendation="Use non-root user",
        file_path="Dockerfile",
        line_number=1,
    )
    ctx = await engine.build_context(finding, file_snippet="FROM ubuntu:latest")
    assert len(ctx.mcp_results) == 1
    rec = await engine.generate_recommendation(finding, ctx, finding_fingerprint(finding))
    assert rec.ai_generated is True
    assert "Docker best practice: use non-root user" in captured["prompt"]
    assert "rule knowledge for DKR-SEC-001" in captured["prompt"]


# ---------------------------------------------------------------------------
# 7. RAG failure keeps scan COMPLETED
# ---------------------------------------------------------------------------


async def test_rag_failure_keeps_scan_completed(session_factory):
    async with session_factory() as session:
        scan = await _insert_scan(session)
        await _insert_finding(session, scan.id)
        engine = FakeEngine()
        engine.rag_fail = True
        service = _make_service(session, engine=engine, cache=FakeCache())

        result = await service.process_scan(scan.id)

        refreshed = await session.get(Scan, scan.id)
        assert refreshed.status == ScanStatus.COMPLETED
        assert refreshed.ai_status == "completed"
        assert result.findings_updated == 1
        assert result.llm_calls == 1


# ---------------------------------------------------------------------------
# 8. LLM failure keeps scan COMPLETED (fallback)
# ---------------------------------------------------------------------------


async def test_llm_failure_falls_back_and_keeps_scan_completed(session_factory):
    async with session_factory() as session:
        scan = await _insert_scan(session)
        await _insert_finding(session, scan.id)
        engine = FakeEngine()
        engine.llm_ok = False
        service = _make_service(session, engine=engine, cache=FakeCache())

        result = await service.process_scan(scan.id)

        refreshed = await session.get(Scan, scan.id)
        assert refreshed.status == ScanStatus.COMPLETED
        assert refreshed.ai_status == "completed"
        assert refreshed.ai_error_message is None
        finding = (
            await session.execute(select_findings(session, scan.id))
        ).scalars().first()
        assert finding.ai_generated is False
        assert result.findings_updated == 1


# ---------------------------------------------------------------------------
# 9. WebSocket per-finding update is broadcast
# ---------------------------------------------------------------------------


async def test_websocket_finding_completed_broadcast(session_factory):
    async with session_factory() as session:
        scan = await _insert_scan(session)
        for rule in ("DKR-SEC-001", "K8S-SEC-001"):
            await _insert_finding(session, scan.id, rule_id=rule, file_path=f"{rule}.yaml")
        service = _make_service(session, engine=FakeEngine(), cache=FakeCache())

        with patch(
            "app.websockets.scan_progress.scan_progress_manager"
        ) as mock_manager:
            mock_manager.broadcast_ai_analysis_started = AsyncMock()
            mock_manager.broadcast_ai_progress = AsyncMock()
            mock_manager.broadcast_ai_finding_completed = AsyncMock()
            mock_manager.broadcast_ai_analysis_completed = AsyncMock()
            mock_manager.broadcast_ai_completed = AsyncMock()
            await service.process_scan(scan.id)

            mock_manager.broadcast_ai_analysis_started.assert_awaited_once_with(str(scan.id))
            assert mock_manager.broadcast_ai_finding_completed.await_count == 2
            call = mock_manager.broadcast_ai_finding_completed.await_args_list[1]
            assert call.args[1] == 2
            assert call.args[2] == 2
            mock_manager.broadcast_ai_analysis_completed.assert_awaited()


# ---------------------------------------------------------------------------
# 10. Batch dedup across groups
# ---------------------------------------------------------------------------


async def test_dedup_across_distinct_rules(session_factory):
    async with session_factory() as session:
        scan = await _insert_scan(session)
        for i in range(6):
            rule = "DKR-SEC-001" if i % 2 == 0 else "K8S-SEC-001"
            await _insert_finding(
                session, scan.id, rule_id=rule, description=f"issue for {rule}", file_path=f"{rule}.yaml"
            )
        engine = FakeEngine()
        service = _make_service(session, engine=engine, cache=FakeCache())

        result = await service.process_scan(scan.id)

        assert result.groups == 2
        assert engine.generate_calls == 2
        assert result.findings_updated == 6


# ---------------------------------------------------------------------------
# 11. Cache invalidation on version change
# ---------------------------------------------------------------------------


def test_cache_key_changes_when_context_version_changes():
    finding = SimpleNamespace(
        rule_id="DKR-SEC-001",
        severity=Severity.HIGH,
        category=Category.SECURITY,
        description="Container runs as root",
        recommendation="Use non-root user",
        file_path="Dockerfile",
        line_number=5,
    )
    fp = finding_fingerprint(finding)
    base = {"rag": "1.0.0", "mcp": "1.0.0", "prompt": "1.0.0", "model": "mock:"}
    k1 = recommendation_cache_key("DKR-SEC-001", "docker", fp, "", base)
    assert k1 == recommendation_cache_key("DKR-SEC-001", "docker", fp, "", dict(base))

    bumped_rag = dict(base, rag="2.0.0")
    assert recommendation_cache_key("DKR-SEC-001", "docker", fp, "", bumped_rag) != k1

    bumped_model = dict(base, model="openai:gpt-4o")
    assert recommendation_cache_key("DKR-SEC-001", "docker", fp, "", bumped_model) != k1

    different_tech = recommendation_cache_key("DKR-SEC-001", "kubernetes", fp, "", base)
    assert different_tech != k1


def test_cache_key_stable_across_identical_findings():
    a = SimpleNamespace(
        rule_id="DKR-SEC-001", severity=Severity.HIGH, category=Category.SECURITY,
        description="  Container   runs as root ", recommendation="Use a non-root user.",
        file_path="/tmp/devarchai/clone/Dockerfile", line_number=5,
    )
    b = SimpleNamespace(
        rule_id="DKR-SEC-001", severity=Severity.HIGH, category=Category.SECURITY,
        description="Container runs as root", recommendation="Use a non-root user.",
        file_path="Dockerfile", line_number=5,
    )
    assert recommendation_cache_key(
        "DKR-SEC-001", "docker", finding_fingerprint(a), "", context_versions()
    ) == recommendation_cache_key("DKR-SEC-001", "docker", finding_fingerprint(b), "", context_versions())


# ---------------------------------------------------------------------------
# 12. Restart recovery
# ---------------------------------------------------------------------------


async def test_recover_pending_ai_scans_re_enqueues():
    pending = [uuid4() for _ in range(2)]
    session = MagicMock()
    scalars = MagicMock()
    mock_rows = [MagicMock(id=uuid_val) for uuid_val in pending]
    scalars.all.return_value = mock_rows
    result = MagicMock()
    result.scalars.return_value = scalars
    session.execute.return_value = result

    with patch("app.db.session.get_sync_session_factory", return_value=lambda: session), patch(
        "app.workers.tasks.ai_recommendations.enqueue_ai_analysis"
    ) as mock_task:
        count = recover_pending_ai_scans()
        assert count == 2
        assert mock_task.delay.call_count == 2
        assert {c.args[0] for c in mock_task.delay.call_args_list} == {str(s) for s in pending}


async def test_already_completed_scan_is_skipped(session_factory):
    async with session_factory() as session:
        scan = await _insert_scan(session, ai_status="completed")
        await _insert_finding(session, scan.id)
        engine = FakeEngine()
        service = _make_service(session, engine=engine, cache=FakeCache())
        result = await service.process_scan(scan.id)
        assert result.findings_updated == 0
        assert engine.generate_calls == 0
