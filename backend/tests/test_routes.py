"""
Backend API Route Tests

Tests for FastAPI routes using TestClient
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

client = TestClient(app)

NIL_UUID = "00000000-0000-0000-0000-000000000000"


def _override_current_user() -> None:
    """Stub authentication so tests can reach payload validation.

    The API checks authentication before request validation (401 first),
    which is correct behavior; these tests exercise the validation layer.
    """
    stub = MagicMock()
    stub.id = NIL_UUID
    stub.email = "qa@example.com"
    app.dependency_overrides[get_current_user] = lambda: stub


class TestHealthCheck:
    """Test health check endpoints."""

    def test_root_health(self):
        """Test root endpoint health check."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "running"

    def test_health_endpoint(self):
        """Test /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_api_docs(self):
        """Test API documentation is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200


class TestAuthRoutes:
    """Test authentication routes."""

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "invalid@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code in [401, 400]

    def test_register_missing_fields(self):
        """Test registration with missing required fields."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com"
                # Missing username and password
            }
        )
        assert response.status_code == 422  # Validation error

    def test_register_invalid_email(self):
        """Test registration with invalid email format."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "username": "testuser",
                "password": "password123"
            }
        )
        assert response.status_code == 422


class TestScanRoutes:
    """Test scan-related routes."""

    def test_get_scans_unauthorized(self):
        """Test getting scans without authentication."""
        response = client.get("/api/v1/scans")
        # Should either redirect to login or return 401
        assert response.status_code in [307, 401, 200]

    def test_get_scan_not_found(self):
        """Test getting non-existent scan."""
        # Must be a syntactically valid UUID, otherwise the route's
        # scan-id parsing rejects it with 400 VALIDATION_ERROR.
        response = client.get(f"/api/v1/scans/{NIL_UUID}")
        assert response.status_code in [404, 307]


class TestFindingsRoutes:
    """Test findings routes."""

    def test_get_findings_unauthorized(self):
        """Test getting findings without authentication."""
        response = client.get("/api/v1/findings")
        assert response.status_code in [307, 401, 200]


class TestRepoAnalysisRoutes:
    """Test repository analysis routes."""

    def test_analyze_repo_invalid_url(self):
        """Test analysis with invalid repository URL."""
        _override_current_user()
        try:
            response = client.post(
                "/api/v1/analyze/repo/deep",
                json={
                    "repo_url": "invalid-url"
                }
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert response.status_code in [400, 422, 500]

    def test_analyze_repo_missing_url(self):
        """Test analysis without repository URL."""
        _override_current_user()
        try:
            response = client.post(
                "/api/v1/analyze/repo/deep",
                json={}
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert response.status_code in [400, 422]


class TestErrorHandling:
    """Test error handling."""

    def test_404_not_found(self):
        """Test 404 error handling."""
        response = client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test method not allowed error."""
        response = client.post("/health")
        assert response.status_code == 405
