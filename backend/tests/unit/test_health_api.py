"""Tests for health check endpoints."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.health import router as health_router
from app.api.v1.routes.health import router as v1_health_router
from app.db.session import get_db


def create_test_app():
    app = FastAPI()
    app.include_router(health_router)
    app.include_router(v1_health_router, prefix="/api/v1")
    return app


def _mock_db_session():
    mock = AsyncMock()
    mock.execute = AsyncMock()
    return mock


def _mock_get_db_override():
    db = _mock_db_session()

    async def override():
        yield db

    return override, db


class TestRootHealthEndpoint:
    def setup_method(self):
        self.app = create_test_app()
        self.client = TestClient(self.app)

    @patch("app.api.routes.health.settings")
    def test_health_returns_200(self, mock_settings):
        mock_settings.VERSION = "1.0.0"
        resp = self.client.get("/health")
        assert resp.status_code == 200

    @patch("app.api.routes.health.settings")
    def test_health_status_healthy(self, mock_settings):
        mock_settings.VERSION = "1.0.0"
        resp = self.client.get("/health")
        data = resp.json()
        assert data["status"] == "healthy"

    @patch("app.api.routes.health.settings")
    def test_health_version_matches_settings(self, mock_settings):
        mock_settings.VERSION = "2.3.4"
        resp = self.client.get("/health")
        data = resp.json()
        assert data["version"] == "2.3.4"

    @patch("app.api.routes.health.settings")
    def test_health_has_services_dict(self, mock_settings):
        mock_settings.VERSION = "1.0.0"
        resp = self.client.get("/health")
        data = resp.json()
        assert "services" in data
        assert isinstance(data["services"], dict)
        assert data["services"]["api"] == "up"

    @patch("app.api.routes.health.settings")
    def test_health_has_timestamp(self, mock_settings):
        mock_settings.VERSION = "1.0.0"
        resp = self.client.get("/health")
        data = resp.json()
        assert "timestamp" in data

    def test_readiness_returns_200(self):
        resp = self.client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_liveness_returns_200(self):
        resp = self.client.get("/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"


class TestV1HealthEndpoint:
    def setup_method(self):
        self.app = create_test_app()
        self.override, self.mock_db = _mock_get_db_override()
        self.app.dependency_overrides[get_db] = self.override
        self.client = TestClient(self.app)

    def teardown_method(self):
        self.app.dependency_overrides.clear()

    @patch("app.config.settings")
    def test_v1_health_returns_200(self, mock_settings):
        mock_settings.VERSION = "1.0.0"
        mock_settings.REDIS_URL = None
        resp = self.client.get("/api/v1/health")
        assert resp.status_code == 200

    @patch("app.config.settings")
    def test_v1_health_status_healthy_when_db_up(self, mock_settings):
        mock_settings.VERSION = "1.0.0"
        mock_settings.REDIS_URL = None
        resp = self.client.get("/api/v1/health")
        data = resp.json()
        assert data["status"] == "healthy"

    @patch("app.config.settings")
    def test_v1_health_database_up(self, mock_settings):
        mock_settings.VERSION = "1.0.0"
        mock_settings.REDIS_URL = None
        resp = self.client.get("/api/v1/health")
        data = resp.json()
        assert data["services"]["database"] == "up"

    @patch("app.config.settings")
    def test_v1_health_database_down_on_exception(self, mock_settings):
        mock_settings.VERSION = "1.0.0"
        mock_settings.REDIS_URL = None
        self.mock_db.execute = AsyncMock(side_effect=Exception("connection refused"))
        resp = self.client.get("/api/v1/health")
        data = resp.json()
        assert data["services"]["database"] == "down"
        assert data["status"] == "degraded"

    @patch("app.config.settings")
    def test_v1_health_cache_not_configured(self, mock_settings):
        mock_settings.VERSION = "1.0.0"
        mock_settings.REDIS_URL = ""
        resp = self.client.get("/api/v1/health")
        data = resp.json()
        assert data["services"]["cache"] == "not_configured"

    @patch("redis.asyncio.from_url")
    @patch("app.config.settings")
    def test_v1_health_cache_up(self, mock_settings, mock_from_url):
        mock_settings.VERSION = "1.0.0"
        mock_settings.REDIS_URL = "redis://localhost:6379/0"

        mock_ping = AsyncMock()
        mock_close = AsyncMock()
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping = mock_ping
        mock_redis_instance.close = mock_close
        mock_from_url.return_value = mock_redis_instance

        resp = self.client.get("/api/v1/health")
        data = resp.json()
        assert data["services"]["cache"] == "up"
        mock_ping.assert_awaited_once()

    @patch("redis.asyncio.from_url")
    @patch("app.config.settings")
    def test_v1_health_cache_down_on_exception(self, mock_settings, mock_from_url):
        mock_settings.VERSION = "1.0.0"
        mock_settings.REDIS_URL = "redis://localhost:6379/0"

        mock_redis_instance = MagicMock()
        mock_redis_instance.ping = AsyncMock(side_effect=Exception("connection refused"))
        mock_redis_instance.close = AsyncMock()
        mock_from_url.return_value = mock_redis_instance

        resp = self.client.get("/api/v1/health")
        data = resp.json()
        assert data["services"]["cache"] == "down"
        assert data["status"] == "degraded"

    @patch("app.config.settings")
    def test_v1_health_version_matches_settings(self, mock_settings):
        mock_settings.VERSION = "3.0.0-beta"
        mock_settings.REDIS_URL = None
        resp = self.client.get("/api/v1/health")
        data = resp.json()
        assert data["version"] == "3.0.0-beta"

    @patch("app.config.settings")
    def test_v1_health_has_services_dict(self, mock_settings):
        mock_settings.VERSION = "1.0.0"
        mock_settings.REDIS_URL = None
        resp = self.client.get("/api/v1/health")
        data = resp.json()
        assert "services" in data
        assert isinstance(data["services"], dict)
        assert set(data["services"].keys()) >= {"api", "database", "cache"}


class TestV1HealthSubEndpoints:
    def setup_method(self):
        self.app = create_test_app()
        self.override, self.mock_db = _mock_get_db_override()
        self.app.dependency_overrides[get_db] = self.override
        self.client = TestClient(self.app)

    def teardown_method(self):
        self.app.dependency_overrides.clear()

    def test_readiness_when_db_ok(self):
        resp = self.client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"] == "ok"

    def test_readiness_when_db_fails(self):
        self.mock_db.execute = AsyncMock(side_effect=Exception("timeout"))
        resp = self.client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"] == "failed"

    def test_liveness(self):
        resp = self.client.get("/api/v1/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"
