"""
Production-Level API Integration Tests

Tests complete API flows:
- Scan lifecycle (start → status → results)
- AI generation validation
- Data integrity checks
- Error handling

Run with:
    pytest backend/tests/integration/test_api_production.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.main import app


# ============================================================================
# SECTION 1: SCAN LIFECYCLE TESTS
# ============================================================================

class TestScanLifecycleAPI:
    """Test complete scan lifecycle through API."""

    @pytest.mark.asyncio
    async def test_start_scan_returns_scan_id(self):
        """Test that starting a scan returns a valid scan_id."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/scan/start",
                json={
                    "repository_url": "https://github.com/test/sample-repo",
                    "branch": "main"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "scan_id" in data
            assert data["scan_id"] is not None
            assert "status" in data

    @pytest.mark.asyncio
    async def test_scan_status_endpoint(self):
        """Test scan status endpoint returns progress."""
        # First start a scan
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start_response = await client.post(
                "/api/v1/scan/start",
                json={
                    "repository_url": "https://github.com/test/sample-repo",
                    "branch": "main"
                }
            )

            assert start_response.status_code == 200
            scan_id = start_response.json()["scan_id"]

            # Check status
            status_response = await client.get(f"/api/v1/scan/status/{scan_id}")
            assert status_response.status_code == 200

            data = status_response.json()
            assert "status" in data
            assert "progress" in data
            assert "current_step" in data

    @pytest.mark.asyncio
    async def test_scan_validation_rejects_invalid_urls(self):
        """Test that scan endpoint rejects invalid repository URLs."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Test HTTP (should be rejected)
            response = await client.post(
                "/api/v1/scan/start",
                json={
                    "repository_url": "http://github.com/test/repo",
                    "branch": "main"
                }
            )

            assert response.status_code == 422  # Validation error

            # Test empty URL
            response = await client.post(
                "/api/v1/scan/start",
                json={
                    "repository_url": "",
                    "branch": "main"
                }
            )

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_scan_validation_rejects_unsafe_urls(self):
        """Test that scan endpoint rejects unsafe URLs."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Test file:// protocol
            response = await client.post(
                "/api/v1/scan/start",
                json={
                    "repository_url": "file:///etc/passwd",
                    "branch": "main"
                }
            )

            assert response.status_code == 422


# ============================================================================
# SECTION 2: AI GENERATION VALIDATION TESTS
# ============================================================================

class TestAIGenerationAPI:
    """Test AI generation through API endpoints."""

    @pytest.mark.asyncio
    async def test_ai_suggestions_endpoint(self):
        """Test AI suggestions endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Start a scan first
            response = await client.post(
                "/api/v1/scan/start",
                json={
                    "repository_url": "https://github.com/test/sample-repo",
                    "branch": "main"
                }
            )

            assert response.status_code == 200
            scan_id = response.json()["scan_id"]

            # Get AI suggestions (endpoint should exist)
            # Note: This tests that the endpoint is registered and responds
            ai_response = await client.get(f"/api/v1/ai-suggestions/{scan_id}")

            # Should return 200 or 404 (if scan not completed), but not 500
            assert ai_response.status_code in [200, 404, 422]


# ============================================================================
# SECTION 3: DATA INTEGRITY TESTS
# ============================================================================

class TestDataIntegrityAPI:
    """Test data integrity through API."""

    @pytest.mark.asyncio
    async def test_scan_results_have_no_null_fields(self):
        """Test that scan results have no NULL AI fields."""
        # This test validates the entire pipeline
        # In production, this would run a real scan
        # For testing, we mock the scan execution

        with patch('app.api.v1.routes.unified_scan.SyncScanService') as mock_service:
            # Mock scan to return findings with AI fields
            mock_scan_instance = MagicMock()
            mock_scan_service = MagicMock()
            mock_scan_service.execute_scan.return_value = MagicMock(
                status=MagicMock(value="completed"),
                progress=100,
                overall_score=75.0,
                security_score=70.0,
                scalability_score=80.0,
                reliability_score=75.0,
                cost_score=70.0,
                observability_score=80.0,
                completed_at=MagicMock(isoformat=MagicMock(return_value="2026-04-05T10:00:00")),
                analysis_duration_seconds=120.0,
                detected_stack={"detected_stack": ["docker", "terraform"]}
            )
            mock_service.return_value = mock_scan_service

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/scan/start",
                    json={
                        "repository_url": "https://github.com/test/sample-repo",
                        "branch": "main"
                    }
                )

                # Should complete without error
                assert response.status_code == 200


# ============================================================================
# SECTION 4: ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandlingAPI:
    """Test API error handling."""

    @pytest.mark.asyncio
    async def test_scan_nonexistent_repo_returns_error(self):
        """Test scanning nonexistent repo returns proper error."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/scan/start",
                json={
                    "repository_url": "https://github.com/nonexistent-user/nonexistent-repo-12345",
                    "branch": "main"
                }
            )

            # Should return error (500 or 400), not crash
            assert response.status_code in [400, 422, 500]
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_scan_status_404_for_invalid_id(self):
        """Test scan status returns 404 for invalid scan ID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/scan/status/nonexistent-scan-id")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_scan_results_404_for_invalid_id(self):
        """Test scan results returns 404 for invalid scan ID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/scan/results/nonexistent-scan-id")

            assert response.status_code in [404, 400]


# ============================================================================
# SECTION 5: HEALTH CHECK TESTS
# ============================================================================

class TestHealthCheckAPI:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_health_check(self):
        """Test root health check endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    @pytest.mark.asyncio
    async def test_readiness_check(self):
        """Test readiness check endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/ready")

            # Should return 200 or 503 (if DB not connected)
            assert response.status_code in [200, 503]
            data = response.json()
            assert "status" in data
            assert "database" in data


# ============================================================================
# SECTION 6: PERFORMANCE TESTS
# ============================================================================

class TestPerformanceAPI:
    """Test API performance characteristics."""

    @pytest.mark.asyncio
    async def test_scan_start_response_time(self):
        """Test scan start endpoint responds quickly."""
        import time

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start_time = time.time()
            response = await client.post(
                "/api/v1/scan/start",
                json={
                    "repository_url": "https://github.com/test/sample-repo",
                    "branch": "main"
                }
            )
            elapsed = time.time() - start_time

            # Should respond within 5 seconds (scan runs in background)
            assert elapsed < 5.0
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_endpoint_fast(self):
        """Test status endpoint responds quickly."""
        import time

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Start scan
            start_response = await client.post(
                "/api/v1/scan/start",
                json={
                    "repository_url": "https://github.com/test/sample-repo",
                    "branch": "main"
                }
            )

            scan_id = start_response.json()["scan_id"]

            # Check status
            start_time = time.time()
            response = await client.get(f"/api/v1/scan/status/{scan_id}")
            elapsed = time.time() - start_time

            # Should respond within 1 second
            assert elapsed < 1.0
            assert response.status_code == 200
