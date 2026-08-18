"""
Production-Level Unit Tests for New Services

Tests for:
- Finding Validator (ensures NO NULL fields)
- Redis Cache Service
- RAG Retriever Service
- WebSocket Manager

Run with:
    pytest backend/tests/unit/test_production_services.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.rule_engine.base import Category, RuleFinding, Severity


# ============================================================================
# SECTION 1: FINDING VALIDATOR TESTS
# ============================================================================

class TestFindingValidator:
    """Test finding validation service ensures NO NULL fields."""

    def test_validator_imports(self):
        """Test that validator module imports successfully."""
        from app.services.finding_validator import validate_findings, FindingValidator
        assert validate_findings is not None
        assert FindingValidator is not None

    def test_validator_fills_null_summary(self):
        """Test validator fills NULL summary with fallback."""
        from app.services.finding_validator import validate_findings

        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Terraform uses local backend",
            recommendation="Use remote backend",
            file_path="main.tf",
            summary=None,  # NULL - should be filled
            risk=None,     # NULL - should be filled
            impact=None,   # NULL - should be filled
            fix_code=None, # NULL - should be filled
        )

        validated, stats = validate_findings([finding])

        assert len(validated) == 1
        assert validated[0].summary is not None, "summary should not be NULL"
        assert validated[0].risk is not None, "risk should not be NULL"
        assert validated[0].impact is not None, "impact should not be NULL"
        assert validated[0].fix_code is not None, "fix_code should not be NULL"
        assert stats.findings_with_fallbacks > 0, "Fallbacks should be applied"

    def test_validator_fills_null_for_all_severities(self):
        """Test validator fills NULL fields for all severity levels."""
        from app.services.finding_validator import validate_findings

        severities = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]

        for severity in severities:
            finding = RuleFinding(
                rule_id=f"TEST-001",
                rule_name="Test Rule",
                severity=severity,
                category=Category.SECURITY,
                description="Test finding",
                recommendation="Test recommendation",
                file_path="test.tf",
                summary=None,
                risk=None,
                impact=None,
                fix_code=None,
            )

            validated, stats = validate_findings([finding])

            assert validated[0].summary is not None, f"summary NULL for {severity}"
            assert validated[0].risk is not None, f"risk NULL for {severity}"
            assert validated[0].impact is not None, f"impact NULL for {severity}"
            assert validated[0].fix_code is not None, f"fix_code NULL for {severity}"

    def test_validator_preserves_existing_values(self):
        """Test validator doesn't overwrite existing non-NULL values."""
        from app.services.finding_validator import validate_findings

        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Test",
            file_path="main.tf",
            summary="Existing summary",
            risk="Existing risk",
            impact="Existing impact",
            fix_code="existing_fix_code",
        )

        validated, stats = validate_findings([finding])

        assert validated[0].summary == "Existing summary"
        assert validated[0].risk == "Existing risk"
        assert validated[0].impact == "Existing impact"
        assert validated[0].fix_code == "existing_fix_code"

    def test_validator_stats_are_accurate(self):
        """Test validator returns accurate statistics."""
        from app.services.finding_validator import validate_findings

        findings = [
            RuleFinding(
                rule_id="TF-STATE-001",
                rule_name="Test",
                severity=Severity.CRITICAL,
                category=Category.RELIABILITY,
                description="Test",
                recommendation="Test",
                file_path="main.tf",
                summary=None,
                risk=None,
                impact=None,
                fix_code=None,
            )
            for _ in range(5)
        ]

        validated, stats = validate_findings(findings)

        assert stats.total_findings == 5
        assert stats.valid_findings == 5
        assert stats.findings_with_fallbacks > 0
        # fallback_rate_pct is calculated in to_dict(), not as attribute
        assert stats.findings_with_fallbacks / stats.total_findings > 0

    def test_validator_handles_unknown_rule_id(self):
        """Test validator handles unknown rule IDs with generic fallback."""
        from app.services.finding_validator import validate_findings

        finding = RuleFinding(
            rule_id="UNKNOWN-RULE-999",
            rule_name="Unknown Rule",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            description="Unknown finding",
            recommendation="Unknown recommendation",
            file_path="test.tf",
            summary=None,
            risk=None,
            impact=None,
            fix_code=None,
        )

        validated, stats = validate_findings([finding])

        # Should use generic fallback
        assert validated[0].summary is not None
        assert validated[0].risk is not None
        assert validated[0].impact is not None
        assert validated[0].fix_code is not None


# ============================================================================
# SECTION 2: REDIS CACHE TESTS
# ============================================================================

class TestRedisCache:
    """Test Redis cache service."""

    def test_cache_imports(self):
        """Test that cache module imports successfully."""
        from app.cache import get_cache
        from app.cache.redis_cache import RedisCache
        assert get_cache is not None
        assert RedisCache is not None

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test basic cache set and get operations with graceful degradation."""
        from app.cache.redis_cache import RedisCache

        cache = RedisCache()
        
        # Test without connection - should return None/False gracefully
        result = await cache.get("test_key")
        assert result is None

        result = await cache.set("test_key", {"data": "value"})
        assert result is False  # Not connected

        # Test delete without connection
        result = await cache.delete("test_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_ai_response(self):
        """Test AI response caching."""
        from app.cache.redis_cache import RedisCache
        from unittest.mock import AsyncMock
        import json

        cache = RedisCache()
        
        # Mock the _redis attribute directly
        mock_redis = AsyncMock()
        ai_response = {
            "summary": "Test summary",
            "risk": "Test risk",
            "confidence": 0.9
        }
        mock_redis.get.return_value = json.dumps(ai_response)
        mock_redis.setex.return_value = True
        
        cache._redis = mock_redis
        cache._connected = True

        # Cache AI response
        await cache.set_ai_response("TF-STATE-001", ai_response)
        mock_redis.setex.assert_called_once()

        # Retrieve AI response
        result = await cache.get_ai_response("TF-STATE-001")
        assert result["summary"] == "Test summary"
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_cache_scan_result(self):
        """Test scan result caching."""
        from app.cache.redis_cache import RedisCache
        from unittest.mock import AsyncMock
        import json

        cache = RedisCache()
        
        # Mock the _redis attribute directly
        mock_redis = AsyncMock()
        scan_result = {
            "scan_id": "test-scan-123",
            "status": "completed",
            "findings_count": 10
        }
        mock_redis.get.return_value = json.dumps(scan_result)
        mock_redis.setex.return_value = True
        
        cache._redis = mock_redis
        cache._connected = True

        # Cache scan result
        await cache.set_scan_result("test-scan-123", scan_result)
        mock_redis.setex.assert_called_once()

        # Retrieve scan result
        result = await cache.get_scan_result("test-scan-123")
        assert result["scan_id"] == "test-scan-123"
        assert result["findings_count"] == 10

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test cache delete operation."""
        from app.cache.redis_cache import RedisCache
        from unittest.mock import AsyncMock

        cache = RedisCache()
        
        # Mock the _redis attribute directly
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 1
        
        cache._redis = mock_redis
        cache._connected = True

        # Delete key
        result = await cache.delete("test_key")
        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_graceful_failure(self):
        """Test cache continues to work when Redis is unavailable."""
        from app.cache.redis_cache import RedisCache

        cache = RedisCache()
        
        # Don't connect - should handle gracefully
        cache._connected = False

        # Should not raise, should return None
        result = await cache.get("test_key")
        assert result is None

        # Set should not raise
        await cache.set("test_key", {"data": "value"})


# ============================================================================
# SECTION 3: RAG RETRIEVER TESTS
# ============================================================================

class TestRAGRetriever:
    """Test RAG documentation retriever."""

    def test_rag_imports(self):
        """Test that RAG module imports successfully."""
        from app.rag import retrieve_docs
        from app.rag.retriever import RAGRetriever
        assert retrieve_docs is not None
        assert RAGRetriever is not None

    def test_rag_retrieves_by_rule_id(self):
        """Test RAG retrieves docs by rule ID."""
        from app.rag import retrieve_docs

        # Test Terraform rule
        docs = retrieve_docs("TF-STATE-001")
        assert docs is not None
        assert len(docs.documents) > 0, "Should retrieve at least one doc"

        # Check relevance score
        top_doc = docs.documents[0]
        score = docs.relevance_scores.get(top_doc.doc_id, 0.0)
        assert score > 0, "Should have relevance score"

    def test_rag_retrieves_kubernetes_docs(self):
        """Test RAG retrieves Kubernetes security docs."""
        from app.rag import retrieve_docs

        docs = retrieve_docs("K8S-SEC-001")
        assert docs is not None
        assert len(docs.documents) > 0

        # Should mention Kubernetes security
        context = docs.to_context_string()
        assert "Kubernetes" in context or "kubernetes" in context

    def test_rag_retrieves_docker_docs(self):
        """Test RAG retrieves Docker security docs."""
        from app.rag import retrieve_docs

        docs = retrieve_docs("DOCKER-SEC-001")
        assert docs is not None
        assert len(docs.documents) > 0

        context = docs.to_context_string()
        assert "Docker" in context or "docker" in context or "Container" in context

    def test_rag_context_string_format(self):
        """Test RAG context string is properly formatted for LLM."""
        from app.rag import retrieve_docs

        docs = retrieve_docs("TF-STATE-001")
        context = docs.to_context_string(max_docs=3)

        assert isinstance(context, str)
        assert len(context) > 0
        # Should be readable text (not JSON or code)
        assert " " in context, "Should be natural text with spaces"

    def test_rag_handles_unknown_rule(self):
        """Test RAG handles unknown rules gracefully."""
        from app.rag import retrieve_docs

        docs = retrieve_docs("UNKNOWN-RULE-999")
        # Should return empty or low-relevance docs, not raise
        assert docs is not None

    def test_rag_retrieves_by_keywords(self):
        """Test RAG retrieves docs by keywords."""
        from app.rag.retriever import RAGRetriever

        retriever = RAGRetriever()
        docs = retriever.retrieve_by_keywords(["terraform", "state", "backend"])

        assert docs is not None
        assert len(docs.documents) > 0

        # Should return Terraform state docs
        top_doc = docs.documents[0]
        score = docs.relevance_scores.get(top_doc.doc_id, 0.0)
        assert score > 0


# ============================================================================
# SECTION 4: WEBSOCKET MANAGER TESTS
# ============================================================================

class TestWebSocketManager:
    """Test WebSocket manager for scan progress."""

    def test_websocket_imports(self):
        """Test that WebSocket module imports successfully."""
        from app.websockets.scan_progress import (
            ScanProgressWebSocketManager,
            scan_progress_websocket
        )
        assert ScanProgressWebSocketManager is not None
        assert scan_progress_websocket is not None

    def test_websocket_manager_creation(self):
        """Test WebSocket manager can be created."""
        from app.websockets.scan_progress import ScanProgressWebSocketManager

        manager = ScanProgressWebSocketManager()
        assert manager is not None
        assert hasattr(manager, '_connections')

    def test_websocket_manager_register_connection(self):
        """Test WebSocket manager can register connections."""
        from app.websockets.scan_progress import ScanProgressWebSocketManager
        import asyncio

        manager = ScanProgressWebSocketManager()

        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()

        # Register connection using async method
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(manager.connect(mock_ws, "test-scan-id"))
            assert "test-scan-id" in manager._connections
            assert len(manager._connections["test-scan-id"]) == 1
        finally:
            loop.close()

    def test_websocket_manager_broadcast(self):
        """Test WebSocket manager can broadcast messages."""
        from app.websockets.scan_progress import ScanProgressWebSocketManager
        import asyncio

        manager = ScanProgressWebSocketManager()

        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()

        # Register connection
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(manager.connect(mock_ws, "test-scan-id"))

            # Broadcast message
            loop.run_until_complete(
                manager.broadcast_progress("test-scan-id", 50, "Running tests...")
            )

            # Verify message sent
            assert mock_ws.send_text.called
        finally:
            loop.close()

    def test_websocket_manager_cleanup(self):
        """Test WebSocket manager cleans up connections."""
        from app.websockets.scan_progress import ScanProgressWebSocketManager
        import asyncio

        manager = ScanProgressWebSocketManager()

        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()

        # Register and disconnect
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(manager.connect(mock_ws, "test-scan-id"))
            assert len(manager._connections.get("test-scan-id", [])) == 1

            # Disconnect
            loop.run_until_complete(manager.disconnect(mock_ws))
            # Connection should be removed
            assert "test-scan-id" not in manager._connections or len(manager._connections.get("test-scan-id", [])) == 0
        finally:
            loop.close()


# ============================================================================
# SECTION 5: INTEGRATION TESTS - FULL PIPELINE
# ============================================================================

class TestFullPipelineIntegration:
    """Test full scan pipeline integration."""

    def test_pipeline_imports_all_services(self):
        """Test that all pipeline services can be imported."""
        # All imports should succeed
        from app.services.findings_enricher import enrich_findings_with_ai
        from app.services.findings_deduplicator import deduplicate_findings
        from app.services.finding_validator import validate_findings
        from app.cache import get_cache
        from app.rag import retrieve_docs
        from app.websockets.scan_progress import ScanProgressWebSocketManager

        assert all([
            enrich_findings_with_ai,
            deduplicate_findings,
            validate_findings,
            get_cache,
            retrieve_docs,
            ScanProgressWebSocketManager
        ])

    @pytest.mark.asyncio
    async def test_pipeline_order(self):
        """Test pipeline executes in correct order."""
        from app.services.findings_enricher import enrich_findings_with_ai
        from app.services.findings_deduplicator import deduplicate_findings
        from app.services.finding_validator import validate_findings

        # Create test finding
        finding = RuleFinding(
            rule_id="TF-STATE-001",
            rule_name="Local Backend",
            severity=Severity.CRITICAL,
            category=Category.RELIABILITY,
            description="Test",
            recommendation="Test",
            file_path="main.tf",
        )

        # Pipeline order: Enrich → Dedup → Validate
        # (In real scan, this happens in scan_repository.py)

        # Step 1: Enrich (mock AI)
        with patch('app.services.findings_enricher.FindingsEnricher._get_ai_service') as mock_ai:
            mock_ai.return_value.generate_fix = AsyncMock(return_value={
                "summary": "AI summary",
                "risk": "AI risk",
                "impact": "AI impact",
                "fix_code": "AI fix",
                "confidence": 0.9
            })

            enriched = await enrich_findings_with_ai([finding])

            assert len(enriched) == 1
            assert enriched[0].summary is not None

        # Step 2: Dedup
        deduped, dedup_stats = deduplicate_findings(enriched)
        assert len(deduped) == 1

        # Step 3: Validate
        validated, val_stats = validate_findings(deduped)
        assert len(validated) == 1

        # All fields should be non-NULL after pipeline
        assert validated[0].summary is not None
        assert validated[0].risk is not None
        assert validated[0].impact is not None
        assert validated[0].fix_code is not None
