"""Unit tests for the RAG knowledge layer (Phase 1).

Covers: technology inventory loading, fingerprint idempotency, retrieval
(rule-id / technology / keyword fallback), caching, and the ingestion
pipeline — all against fakes; no database required.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.models.knowledge import KnowledgeDocument
from app.rag.embeddings import EmbeddingUnavailable
from app.rag.ingestion import DocumentCleaner, RagIngestionService
from app.rag.inventory import TechnologyInventory
from app.rag.models import KnowledgeDocumentInput, RagResultDocument
from app.rag.retrieval import RagRetrievalService

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeScalars:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)
        self._scalars = FakeScalars(self._rows)

    def scalars(self):
        return self._scalars

    def all(self):
        return list(self._rows)

    def fetchall(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.added = []
        self.committed = False
        self.flushed = False

    def set_rows(self, rows):
        self.rows = rows

    async def execute(self, stmt, *args, **kwargs):
        return FakeResult(self.rows)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeFactory:
    def __init__(self, session=None):
        self.session = session or FakeSession()

    def __call__(self):
        return self.session

    def set_rows(self, rows):
        self.session.set_rows(rows)


class FakeRagCache:
    def __init__(self):
        self.store: dict = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ttl_seconds=None):
        self.store[key] = value


def _row(**overrides):
    kwargs = {
        "source_type": "curated",
        "source_name": "inv",
        "authority": "devarchai_curated",
        "title": "doc",
        "url": "",
        "version": "1.0.0",
        "content": "content about rule",
        "technology": "kubernetes",
        "rule_id": "K8S-CON-001",
        "category": "security",
        "severity": "high",
        "rag_version": "1.0.0",
        "fingerprint": "fp",
        "metadata_json": {},
        "updated_at": datetime.now(UTC),
    }
    kwargs.update(overrides)
    return KnowledgeDocument(**kwargs)


def _service(session):
    svc = RagRetrievalService()
    svc._session_factory = FakeFactory(session)
    return svc


def _no_embeddings():
    router = type("Router", (), {})()
    router.is_semantic_available = lambda: False
    return router


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

MINIMAL_INVENTORY = {
    "inventory_version": "1.0.0",
    "technologies": [
        {
            "id": "kubernetes",
            "description": "Kubernetes security",
            "rule_ids": ["K8S-CON-001", "K8S-NET-002"],
            "categories": ["security"],
            "file_types": [".yaml", ".yml"],
            "external_scanners": ["kube-bench"],
        },
        {
            "id": "terraform",
            "description": "Terraform",
            "rule_ids": ["TF-ENC-003"],
            "categories": ["security"],
            "file_types": [".tf"],
            "external_scanners": ["tfsec"],
        },
    ],
    "cross_cutting": [
        {"id": "security", "description": "Cross-cutting security", "rule_ids": ["X-SEC-001"]}
    ],
}


class TestInventory:
    def test_technologies_loaded(self):
        inv = TechnologyInventory(MINIMAL_INVENTORY)
        assert set(inv.technologies()) == {"kubernetes", "terraform"}

    def test_rule_id_reverse_lookup(self):
        inv = TechnologyInventory(MINIMAL_INVENTORY)
        assert inv.technology_for_rule_id("K8S-CON-001") == ["kubernetes"]
        assert inv.technology_for_rule_id("UNKNOWN-000") == []

    def test_rule_ids_for(self):
        inv = TechnologyInventory(MINIMAL_INVENTORY)
        assert inv.rule_ids_for("terraform") == ["TF-ENC-003"]
        assert inv.rule_ids_for("nope") == []

    def test_cross_cutting_and_scanners(self):
        inv = TechnologyInventory(MINIMAL_INVENTORY)
        assert inv.cross_cutting_rule_ids() == ["X-SEC-001"]
        assert inv.external_scanners_for("kubernetes") == ["kube-bench"]

    def test_version(self):
        inv = TechnologyInventory(MINIMAL_INVENTORY)
        assert inv.version == "1.0.0"


class TestFingerprint:
    def test_fingerprint_is_deterministic(self):
        a = KnowledgeDocumentInput(
            source_type="curated", source_name="x", title="t", content="c", rule_id="R-1"
        )
        b = KnowledgeDocumentInput(
            source_type="curated", source_name="x", title="t", content="c", rule_id="R-1"
        )
        assert a.fingerprint == b.fingerprint

    def test_fingerprint_changes_on_rule(self):
        a = KnowledgeDocumentInput(
            source_type="curated", source_name="x", title="t", content="c", rule_id="R-1"
        )
        b = KnowledgeDocumentInput(
            source_type="curated", source_name="x", title="t", content="c", rule_id="R-2"
        )
        assert a.fingerprint != b.fingerprint


class TestDocumentCleaner:
    def test_clean_normalizes_whitespace(self):
        cleaner = DocumentCleaner()
        assert cleaner.clean("  a\r\n\n\nb  ") == "a\nb"


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

class TestRetrievalRuleId:
    @pytest.mark.asyncio
    @patch("app.rag.retrieval.get_rag_cache", return_value=FakeRagCache())
    @patch("app.rag.retrieval.get_embedding_router", return_value=_no_embeddings())
    async def test_rule_id_retrieval_filters(self, router, cache):
        # Fake session returns rows as-is (SQL filtering is exercised against a
        # real DB); supply the rows the filtered query would return.
        rows = [
            _row(rule_id="K8S-CON-001"),
            _row(rule_id="K8S-CON-001-extra"),
        ]
        context = await _service(FakeSession(rows)).retrieve("k8s", rule_id="K8S-CON-001")

        assert context.method == "rule_id"
        assert all(d.rule_id.startswith("K8S-CON-001") for d in context.documents)
        assert context.total_available == 2

    @pytest.mark.asyncio
    @patch("app.rag.retrieval.get_rag_cache", return_value=FakeRagCache())
    @patch("app.rag.retrieval.get_embedding_router", return_value=_no_embeddings())
    async def test_rule_id_source_priority_ordering(self, router, cache):
        rows = [
            _row(rule_id="K8S-CON-001", source_type="curated"),
            _row(rule_id="K8S-CON-001", source_type="docs"),
            _row(rule_id="K8S-CON-001", source_type="live"),
        ]
        context = await _service(FakeSession(rows)).retrieve("k8s", rule_id="K8S-CON-001", k=3)

        assert [d.source_type for d in context.documents] == ["live", "docs", "curated"]


class TestRetrievalTechnologyAndKeyword:
    @pytest.mark.asyncio
    @patch("app.rag.retrieval.get_rag_cache", return_value=FakeRagCache())
    @patch("app.rag.retrieval.get_embedding_router", return_value=_no_embeddings())
    async def test_technology_filter(self, router, cache):
        rows = [
            _row(technology="kubernetes", rule_id="K8S-001", content="pod security"),
            _row(technology="kubernetes", rule_id="K8S-002", content="rbac hardening"),
        ]
        context = await _service(FakeSession(rows)).retrieve("anything", technology="kubernetes")

        assert context.method == "technology"
        assert all(d.technology == "kubernetes" for d in context.documents)
        assert context.total_available == 2

    @pytest.mark.asyncio
    @patch("app.rag.retrieval.get_rag_cache", return_value=FakeRagCache())
    @patch("app.rag.retrieval.get_embedding_router", return_value=_no_embeddings())
    async def test_keyword_fallback_scores_terms(self, router, cache):
        rows = [
            _row(title="k8s pod security", content="runs as root in kubernetes", rule_id="K8S-001"),
            _row(title="docker", content="nothing relevant", rule_id="DOCKER-001", technology="docker"),
        ]
        context = await _service(FakeSession(rows)).retrieve("kubernetes security")

        assert context.method == "keyword"
        assert [d.rule_id for d in context.documents] == ["K8S-001"]

    @pytest.mark.asyncio
    @patch("app.rag.retrieval.get_rag_cache", return_value=FakeRagCache())
    @patch("app.rag.retrieval.get_embedding_router", return_value=_no_embeddings())
    async def test_empty_query_returns_empty(self, router, cache):
        context = await _service(FakeSession([_row()])).retrieve("")
        assert context.documents == []
        assert context.method == "keyword"


class TestRetrievalCache:
    @pytest.mark.asyncio
    async def test_cache_miss_then_hit(self):
        from app.rag.cache import rag_cache_key

        key = rag_cache_key("q", {"rule_id": None, "technology": None, "category": None, "severity": None, "k": 5})
        cache = FakeRagCache()
        cache.store[key] = {
            "documents": [
                RagResultDocument(title="cached", content="c", source_type="curated", source_name="s").to_dict()
            ],
            "method": "cache",
            "total_available": 1,
            "rag_version": "1.0.0",
        }

        with patch("app.rag.retrieval.get_rag_cache", return_value=cache):
            svc = _service(FakeSession([]))
            context = await svc.retrieve("q", k=5)

        assert context.method == "cache"
        assert context.documents[0].title == "cached"


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

class TestIngestion:
    @pytest.mark.asyncio
    @patch("app.rag.ingestion.get_embedding_router")
    async def test_ingest_document_creates_row_and_chunks(self, router):
        router.return_value.is_semantic_available.return_value = False
        router.return_value.embed_texts.side_effect = EmbeddingUnavailable("no embeddings")

        session = FakeSession([])
        svc = RagIngestionService()
        svc._session_factory = FakeFactory(session)

        doc = KnowledgeDocumentInput(
            source_type="curated",
            source_name="inv",
            title="K8S rules",
            content="word " * 500,
            technology="kubernetes",
            rule_id="K8S-CON-001",
        )
        created = await svc.ingest_document(doc)

        assert created is True
        assert session.committed is True
        assert isinstance(session.added[0], KnowledgeDocument)
        assert len(session.added) >= 2  # document + at least one chunk

    @pytest.mark.asyncio
    @patch("app.rag.ingestion.get_embedding_router")
    async def test_ingest_unchanged_returns_false(self, router):
        router.return_value.is_semantic_available.return_value = False
        router.return_value.embed_texts.side_effect = EmbeddingUnavailable("no embeddings")

        content = "word " * 500
        content_hash = hashlib.sha256(
            DocumentCleaner().clean(content).encode("utf-8")
        ).hexdigest()
        existing = _row(rule_id="K8S-CON-001", content=content, metadata_json={"content_hash": content_hash})
        session = FakeSession([existing])
        svc = RagIngestionService()
        svc._session_factory = FakeFactory(session)

        doc = KnowledgeDocumentInput(
            source_type="curated",
            source_name="inv",
            title="K8S rules",
            content=content,
            technology="kubernetes",
            rule_id="K8S-CON-001",
        )
        created = await svc.ingest_document(doc)

        assert created is False
        assert session.committed is False

    def test_inventory_seed_builds_docs(self):
        from app.rag.inventory import load_inventory

        inv = load_inventory()
        assert len(inv.technologies()) >= 10
        assert inv.all_rule_ids()
        first = inv.technologies()[0]
        assert inv.rule_ids_for(first)
