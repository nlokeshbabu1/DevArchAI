"""Tests for the Knowledge Retrieval Layer.

Tests for knowledge providers, registry, cache, and metrics.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime

from app.knowledge.base import KnowledgeDocument, KnowledgeProvider
from app.knowledge.registry import KnowledgeRegistry
from app.knowledge.cache import KnowledgeCache
from app.knowledge.metrics import KnowledgeRetrievalMetrics, MetricsCollector


class TestKnowledgeDocument:
    """Tests for KnowledgeDocument dataclass."""

    def test_create_document(self):
        """Test creating a KnowledgeDocument."""
        doc = KnowledgeDocument(
            source="aws_docs",
            title="EC2 Best Practices",
            content="EC2 best practices content",
            url="https://docs.aws.amazon.com/ec2/",
            version="latest",
            relevance_score=0.9,
            metadata={"service": "ec2"},
        )
        assert doc.source == "aws_docs"
        assert doc.title == "EC2 Best Practices"
        assert doc.content == "EC2 best practices content"
        assert doc.url == "https://docs.aws.amazon.com/ec2/"
        assert doc.version == "latest"
        assert doc.relevance_score == 0.9
        assert doc.metadata == {"service": "ec2"}

    def test_cache_key(self):
        """Test cache key generation."""
        doc1 = KnowledgeDocument(source="aws_docs", title="EC2 Best Practices", content="content1")
        doc2 = KnowledgeDocument(source="aws_docs", title="EC2 Best Practices", content="content2")
        doc3 = KnowledgeDocument(source="aws_docs", title="S3 Best Practices", content="content3")

        # Same source + title should produce same cache key
        assert doc1.cache_key == doc2.cache_key
        # Different title should produce different cache key
        assert doc1.cache_key != doc3.cache_key

    def test_to_prompt_context(self):
        """Test prompt context serialization."""
        doc = KnowledgeDocument(
            source="aws_docs",
            title="EC2 Best Practices",
            content="EC2 best practices content",
            url="https://docs.aws.amazon.com/ec2/",
            version="latest",
        )
        prompt = doc.to_prompt_context()
        assert "## EC2 Best Practices (source: aws_docs)" in prompt
        assert "Reference: https://docs.aws.amazon.com/ec2/" in prompt
        assert "Version: latest" in prompt
        assert "EC2 best practices content" in prompt


class TestKnowledgeRegistry:
    """Tests for KnowledgeRegistry."""

    def test_register_provider(self):
        """Test registering a provider."""
        registry = KnowledgeRegistry()

        class MockProvider(KnowledgeProvider):
            @property
            def name(self) -> str:
                return "mock"

            async def retrieve(self, query, *, service="", region="", max_results=5):
                return []

        provider = MockProvider()
        registry.register(provider)

        assert "mock" in registry.providers
        assert registry.providers["mock"] is provider

    def test_unregister_provider(self):
        """Test unregistering a provider."""
        registry = KnowledgeRegistry()

        class MockProvider(KnowledgeProvider):
            @property
            def name(self) -> str:
                return "mock"

            async def retrieve(self, query, *, service="", region="", max_results=5):
                return []

        provider = MockProvider()
        registry.register(provider)
        assert "mock" in registry.providers

        registry.unregister("mock")
        assert "mock" not in registry.providers

    def test_deduplicate(self):
        """Test document deduplication."""
        docs = [
            KnowledgeDocument(source="aws_docs", title="EC2 Best Practices", content="content1"),
            KnowledgeDocument(source="aws_docs", title="ec2 best practices", content="content2"),
            KnowledgeDocument(source="aws_docs", title="S3 Best Practices", content="content3"),
        ]

        unique = KnowledgeRegistry._deduplicate(docs)
        assert len(unique) == 2  # EC2 and ec2 should be deduplicated


class TestKnowledgeCache:
    """Tests for KnowledgeCache."""

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting cache entries."""
        cache = KnowledgeCache(default_ttl_seconds=60)
        docs = [
            KnowledgeDocument(source="aws_docs", title="Test", content="content"),
        ]

        await cache.set("aws_docs", "test query", docs)
        result = await cache.get("aws_docs", "test query")

        assert result is not None
        assert len(result) == 1
        assert result[0].title == "Test"

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache expiration."""
        cache = KnowledgeCache(default_ttl_seconds=0)  # Immediate expiration
        docs = [
            KnowledgeDocument(source="aws_docs", title="Test", content="content"),
        ]

        await cache.set("aws_docs", "test query", docs)
        result = await cache.get("aws_docs", "test query")

        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate(self):
        """Test cache invalidation."""
        cache = KnowledgeCache(default_ttl_seconds=60)
        docs = [
            KnowledgeDocument(source="aws_docs", title="Test", content="content"),
        ]

        await cache.set("aws_docs", "test query", docs)
        result = await cache.get("aws_docs", "test query")
        assert result is not None

        # Invalidate all entries
        count = await cache.invalidate()
        assert count >= 1

        result = await cache.get("aws_docs", "test query")
        assert result is None

    @pytest.mark.asyncio
    async def test_stats(self):
        """Test cache statistics."""
        cache = KnowledgeCache(default_ttl_seconds=60)
        docs = [
            KnowledgeDocument(source="aws_docs", title="Test", content="content"),
        ]

        await cache.set("aws_docs", "test query", docs)
        stats = await cache.stats()

        assert stats["total_entries"] == 1
        assert stats["active_entries"] == 1
        assert stats["expired_entries"] == 0


class TestKnowledgeMetrics:
    """Tests for KnowledgeRetrievalMetrics."""

    def test_record_provider_request(self):
        """Test recording provider requests."""
        metrics = KnowledgeRetrievalMetrics()

        metrics.record_provider_request(
            provider_name="aws_docs",
            latency_ms=100.0,
            success=True,
            document_count=5,
            cache_hit=False,
        )

        assert metrics.total_retrievals == 1
        assert metrics.total_documents_retrieved == 5
        assert "aws_docs" in metrics.provider_metrics

        pm = metrics.provider_metrics["aws_docs"]
        assert pm.total_requests == 1
        assert pm.successful_requests == 1
        assert pm.total_latency_ms == 100.0

    def test_get_summary(self):
        """Test getting metrics summary."""
        metrics = KnowledgeRetrievalMetrics()

        metrics.record_provider_request(
            provider_name="aws_docs",
            latency_ms=100.0,
            success=True,
            document_count=5,
        )
        metrics.record_provider_request(
            provider_name="aws_pricing",
            latency_ms=50.0,
            success=True,
            document_count=2,
        )

        summary = metrics.get_summary()

        assert summary["total_retrievals"] == 2
        assert summary["total_documents_retrieved"] == 7
        assert "aws_docs" in summary["providers"]
        assert "aws_pricing" in summary["providers"]


class TestMetricsCollector:
    """Tests for MetricsCollector context manager."""

    def test_collect_metrics(self):
        """Test metrics collection."""
        from app.knowledge.metrics import get_knowledge_metrics

        # Get the singleton and record the initial count
        metrics = get_knowledge_metrics()
        initial_count = metrics.total_retrievals

        with MetricsCollector("aws_docs", "test query") as collector:
            collector.set_documents(5)
            collector.set_cache_hit(False)

        assert metrics.total_retrievals == initial_count + 1
        assert metrics.total_documents_retrieved >= 5
