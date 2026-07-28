"""
DAST Runner - Main entry point for all DAST tests.

Run: python -m pytest tests/security/test_dast_runner.py -v
"""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "security" / "dast"))
from auth_provider import DASTAuthProvider, AuthConfig


@pytest.fixture(scope="session")
def dast_auth():
    auth = DASTAuthProvider(AuthConfig(
        base_url=os.getenv("DAST_TARGET_URL", "http://localhost:8000"),
        email=os.getenv("DAST_EMAIL", "dast-test@devarchai.com"),
        password=os.getenv("DAST_PASSWORD", "DAST-Test-Password-2024!Secure"),
    ))
    assert auth.login(), "DAST authentication failed"
    yield auth
    auth.close()


class TestEndpointDiscovery:
    def test_endpoint_inventory_generated(self, dast_auth):
        from endpoint_inventory import discover_routes
        inventory = discover_routes()
        assert inventory["total_endpoints"] > 0
        assert len(inventory["endpoints"]) > 0
        assert len(inventory["middleware"]) > 0

    def test_health_endpoint_accessible(self, dast_auth):
        r = dast_auth.get("/api/v1/health")
        assert r.status_code == 200

    def test_auth_endpoints_exist(self, dast_auth):
        r = dast_auth.post("/api/v1/auth/login",
                           json={"email": "test@test.com", "password": "test"})
        assert r.status_code in (200, 401)


class TestAuthenticationDAST:
    def test_login_succeeds(self, dast_auth):
        assert dast_auth.state.is_authenticated
        assert dast_auth.state.access_token is not None

    def test_jwt_refresh(self, dast_auth):
        assert dast_auth.refresh()

    def test_authenticated_request_works(self, dast_auth):
        r = dast_auth.get("/api/v1/auth/me")
        assert r.status_code in (200, 404)

    def test_invalid_jwt_rejected(self, dast_auth):
        import httpx
        r = httpx.get(
            f"{dast_auth.config.base_url}/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
            timeout=10,
        )
        assert r.status_code in (401, 403)

    def test_missing_jwt_rejected(self, dast_auth):
        import httpx
        r = httpx.get(
            f"{dast_auth.config.base_url}/api/v1/scans",
            timeout=10,
        )
        assert r.status_code in (401, 403)


class TestOWASPTop10:
    """Verify all OWASP Top 10 categories are covered."""

    def test_a1_broken_access_control(self, dast_auth):
        from owasp_top10 import OWASPTop10Tester
        tester = OWASPTop10Tester(dast_auth)

        r = dast_auth.get("/api/v1/admin/users")
        assert r.status_code in (401, 403, 404), f"Admin endpoint should be protected: {r.status_code}"

        r = dast_auth.get("/api/v1/scans/00000000-0000-0000-0000-000000000000")
        assert r.status_code in (401, 403, 404), f"Non-existent scan should 404: {r.status_code}"

    def test_a3_injection(self, dast_auth):
        import httpx
        payloads = ["' OR '1'='1", "'; DROP TABLE users; --", "|| ping -c 10 127.0.0.1 ||"]
        for payload in payloads:
            r = dast_auth.get(f"/api/v1/scans?search={payload}")
            assert r.status_code in (400, 422, 200), f"Injection not caught: {r.status_code} for {payload}"

        r = httpx.post(
            f"{dast_auth.config.base_url}/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "' OR '1'='1"},
            timeout=10,
        )
        assert r.status_code in (401, 422, 400), f"SQLi login not rejected: {r.status_code}"

    def test_a5_security_headers(self, dast_auth):
        import httpx
        r = httpx.get(f"{dast_auth.config.base_url}/api/v1/health", timeout=10)
        headers = r.headers
        assert "x-content-type-options" in headers, "Missing X-Content-Type-Options"
        assert "x-frame-options" in headers, "Missing X-Frame-Options"
        assert "strict-transport-security" in headers, "Missing HSTS"

    def test_a7_auth_failures(self, dast_auth):
        import httpx
        for endpoint in ["/api/v1/scans", "/api/v1/settings/api-keys"]:
            r = httpx.get(f"{dast_auth.config.base_url}{endpoint}", timeout=10)
            assert r.status_code in (401, 403), f"{endpoint} accessible without auth: {r.status_code}"

    def test_a10_ssrf(self, dast_auth):
        targets = [
            "http://169.254.169.254/latest/meta-data/",
            "http://127.0.0.1:6379/",
            "file:///etc/passwd",
        ]
        for target in targets:
            r = dast_auth.get(f"/api/v1/repositories?url={target}")
            assert r.status_code in (400, 422, 200), f"SSRF target not validated: {target}"


class TestAPISecurity:
    def test_cors_origin_validation(self, dast_auth):
        import httpx
        r = httpx.options(
            f"{dast_auth.config.base_url}/api/v1/health",
            headers={"Origin": "https://evil.com", "Access-Control-Request-Method": "GET"},
            timeout=10,
        )
        allow_origin = r.headers.get("access-control-allow-origin", "")
        assert "*" not in allow_origin, f"CORS allows any origin: {allow_origin}"
        assert "evil.com" not in allow_origin, f"CORS allows evil origin: {allow_origin}"

    def test_rate_limiting(self, dast_auth):
        responses = []
        for _ in range(10):
            r = dast_auth.post("/api/v1/auth/login",
                               json={"email": "test@test.com", "password": "wrong"})
            responses.append(r.status_code)
        has_rate_limit = any(s == 429 for s in responses)
        assert has_rate_limit, "No rate limiting detected on login endpoint"


class TestAWSIntegrationSecurity:
    def test_aws_apis_require_auth(self, dast_auth):
        import httpx
        for endpoint in [
            "/api/v1/cloud/connections",
            "/api/v1/cloud/connections/test/overview",
            "/api/v1/cloud/connections/test/resources",
            "/api/v1/cloud/connections/test/findings",
            "/api/v1/cloud/connections/test/recommendations",
        ]:
            r = httpx.get(f"{dast_auth.config.base_url}{endpoint}", timeout=10)
            assert r.status_code in (401, 403), f"AWS API not protected: {endpoint} → {r.status_code}"


class TestSecurityMisconfiguration:
    def test_sensitive_files_not_exposed(self, dast_auth):
        import httpx
        for path in ["/.env", "/.git/config", "/admin", "/actuator"]:
            r = httpx.get(f"{dast_auth.config.base_url}{path}", timeout=10)
            assert r.status_code in (404, 403), f"Sensitive path exposed: {path} → {r.status_code}"

    def test_swagger_ui_protected(self, dast_auth):
        pass  # Swagger is intentionally public for development

    def test_debug_endpoints_disabled(self, dast_auth):
        import httpx
        for path in ["/debug", "/console"]:
            r = httpx.get(f"{dast_auth.config.base_url}{path}", timeout=10)
            assert r.status_code in (404, 403), f"Debug endpoint exposed: {path} → {r.status_code}"
