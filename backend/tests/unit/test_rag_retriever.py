"""Unit tests for the in-memory RAG retriever."""
import pytest
from app.rag.retriever import (
    DocEntry,
    RetrievalResult,
    RAGRetriever,
    get_retriever,
    retrieve_docs,
)


class TestDocEntry:
    """Tests for the DocEntry dataclass."""

    def test_doc_entry_creation(self):
        """DocEntry can be created with all fields."""
        doc = DocEntry(
            doc_id="test-001",
            title="Test Document",
            category="security",
            content="This is test content about security.",
            tags=["security", "test"],
            rule_ids=["TF-001", "DOCKER-001"],
            url="https://example.com",
            priority=1,
        )
        assert doc.doc_id == "test-001"
        assert doc.category == "security"
        assert "security" in doc.tags
        assert len(doc.rule_ids) == 2

    def test_doc_entry_optional_fields(self):
        """DocEntry works with minimal fields (defaults)."""
        doc = DocEntry(
            doc_id="test-002",
            title="Minimal",
            category="general",
            content="Content",
        )
        assert doc.tags == []
        assert doc.rule_ids == []
        assert doc.url is None
        assert doc.priority == 0


class TestRetrievalResult:
    """Tests for the RetrievalResult dataclass."""

    def test_to_dict(self):
        """to_dict returns serializable dict."""
        doc = DocEntry("d1", "Title", "cat", "content")
        result = RetrievalResult(
            query="test query",
            documents=[doc],
            total_available=5,
            relevance_scores={"d1": 0.9},
        )
        d = result.to_dict()
        assert d["query"] == "test query"
        assert len(d["documents"]) == 1

    def test_to_context_string(self):
        """to_context_string produces readable context."""
        doc = DocEntry("d1", "Security Guide", "security", "Best practices for security.")
        result = RetrievalResult("test", [doc], 1, {"d1": 0.8})
        ctx = result.to_context_string(max_docs=1)
        assert "Security Guide" in ctx
        assert "Best practices" in ctx

    def test_empty_documents(self):
        """Empty documents list produces fallback message."""
        result = RetrievalResult("test", [], 0, {})
        assert "No relevant" in result.to_context_string()


class TestRAGRetriever:
    """Tests for the RAGRetriever knowledge base."""

    @pytest.fixture
    def retriever(self):
        """Provide a fresh retriever with default knowledge base."""
        return RAGRetriever()

    def test_default_knowledge_base_not_empty(self, retriever):
        """Default knowledge base contains documents."""
        all_docs = retriever.get_all_categories()
        assert len(all_docs) > 0

    def test_retrieve_by_rule_id(self, retriever):
        """Retrieve documents by rule ID prefix."""
        result = retriever.retrieve("TF-STATE-001", max_results=3)
        assert len(result.documents) >= 1

    def test_retrieve_by_keyword(self, retriever):
        """Retrieve documents by keyword."""
        result = retriever.retrieve_by_keywords(["docker", "security"], max_results=5)
        assert len(result.documents) >= 1

    def test_retrieve_nonexistent_rule(self, retriever):
        """Retrieve for unknown rule returns empty result."""
        result = retriever.retrieve("UNKNOWN-999", max_results=5)
        assert len(result.documents) == 0

    def test_get_document_by_id(self, retriever):
        """get_document returns specific document."""
        all_docs = retriever.get_all_categories()
        first_cat = all_docs[0] if all_docs else None
        if first_cat:
            docs = retriever.get_documents_by_category(first_cat)
            if docs:
                doc = retriever.get_document(docs[0].doc_id)
                assert doc is not None
                assert doc.doc_id == docs[0].doc_id

    def test_add_and_remove_document(self, retriever):
        """Can add and remove custom documents."""
        new_doc = DocEntry(
            doc_id="custom-001",
            title="Custom Doc",
            category="custom",
            content="Custom content",
            tags=["custom"],
            rule_ids=["CUSTOM-001"],
        )
        retriever.add_document(new_doc)
        retrieved = retriever.get_document("custom-001")
        assert retrieved is not None
        assert retrieved.title == "Custom Doc"

        removed = retriever.remove_document("custom-001")
        assert removed is True
        assert retriever.get_document("custom-001") is None

    def test_remove_nonexistent_returns_false(self, retriever):
        """Removing non-existent document returns False."""
        result = retriever.remove_document("nonexistent-999")
        assert result is False

    def test_get_documents_by_category(self, retriever):
        """get_documents_by_category returns relevant docs."""
        categories = retriever.get_all_categories()
        if categories:
            docs = retriever.get_documents_by_category(categories[0], max_results=10)
            assert len(docs) >= 1
            for doc in docs:
                assert doc.category == categories[0]

    def test_get_all_categories(self, retriever):
        """get_all_categories returns unique categories."""
        cats = retriever.get_all_categories()
        assert len(cats) > 0
        assert len(cats) == len(set(cats))

    def test_relevance_scoring(self, retriever):
        """Documents with exact rule_id match score higher than prefix match."""
        result = retriever.retrieve("DOCKER-SEC-001", max_results=5)
        if len(result.relevance_scores) > 1:
            scores = list(result.relevance_scores.values())
            # First result should have highest score
            assert scores[0] >= scores[1]


class TestRetrieveDocsConvenience:
    """Tests for the retrieve_docs convenience function."""

    def test_retrieve_docs_returns_result(self):
        """retrieve_docs returns a RetrievalResult."""
        result = retrieve_docs("TF-STATE-001", max_results=3)
        assert isinstance(result, RetrievalResult)
        assert result.query == "TF-STATE-001"

    def test_retrieve_docs_empty_for_unknown(self):
        """retrieve_docs returns empty for unknown rule."""
        result = retrieve_docs("UNKNOWN-999")
        assert len(result.documents) == 0


class TestGetRetrieverSingleton:
    """Tests for get_retriever singleton."""

    def test_returns_same_instance(self):
        """get_retriever returns the same instance on repeated calls."""
        r1 = get_retriever()
        r2 = get_retriever()
        assert r1 is r2
