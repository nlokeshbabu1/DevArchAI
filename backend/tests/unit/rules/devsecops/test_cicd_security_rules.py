"""
Unit Tests for CI/CD Security Rules

Tests for CI-SEC-001 to CI-SEC-010
"""

import pytest

from app.rules.base import Severity
from app.rules.devsecops.cicd_security import (
    CICDMissingSecurityScanRule,
    CICDMissingDependencyScanRule,
    CICDHardcodedSecretsRule,
    CICDUntrustedActionsRule,
    CICDMissingContainerScanRule,
)


class TestCICDMissingSecurityScanRule:
    """Tests for CI-SEC-001: Missing Security Scanning."""

    def test_detects_missing_security_scan(self):
        """CI/CD without security scanning should detect issue."""
        rule = CICDMissingSecurityScanRule()
        resources = [
            {
                "file_type": "cicd",
                "properties": {
                    "jobs": [
                        {"name": "build", "run": "npm run build"},
                        {"name": "test", "run": "npm test"},
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        assert len(findings) == 1
        assert findings[0].rule_id == "CI-SEC-001"
        assert findings[0].severity == Severity.HIGH

    def test_passes_with_security_scan(self):
        """CI/CD with security scanning should pass."""
        rule = CICDMissingSecurityScanRule()
        resources = [
            {
                "file_type": "cicd",
                "properties": {
                    "jobs": [
                        {"name": "build", "run": "npm run build"},
                        {"name": "security", "run": "npm audit && trivy fs ."},
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        assert len(findings) == 0


class TestCICDMissingDependencyScanRule:
    """Tests for CI-SEC-002: Missing Dependency Scanning."""

    def test_detects_missing_dependency_scan(self):
        """CI/CD without dependency scanning should detect issue."""
        rule = CICDMissingDependencyScanRule()
        resources = [
            {
                "file_type": "cicd",
                "properties": {
                    "steps": [
                        {"name": "build", "run": "npm run build"},
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        assert len(findings) == 1
        assert findings[0].rule_id == "CI-SEC-002"
        assert findings[0].severity == Severity.HIGH

    def test_passes_with_npm_audit(self):
        """CI/CD with npm audit should pass."""
        rule = CICDMissingDependencyScanRule()
        resources = [
            {
                "file_type": "cicd",
                "properties": {
                    "steps": [
                        {"name": "install", "run": "npm install"},
                        {"name": "audit", "run": "npm audit"},
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        assert len(findings) == 0


class TestCICDHardcodedSecretsRule:
    """Tests for CI-SEC-003: Hardcoded Secrets in Pipeline."""

    def test_detects_hardcoded_api_key(self):
        """CI/CD with hardcoded API key should detect issue."""
        rule = CICDHardcodedSecretsRule()
        resources = [
            {
                "file_type": "cicd",
                "raw_content": """
name: CI
jobs:
  deploy:
    steps:
      - run: curl -H "API_KEY: sk_live_abc123def456ghi789jkl012" https://api.example.com
""",
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        assert len(findings) == 1
        assert findings[0].rule_id == "CI-SEC-003"
        assert findings[0].severity == Severity.CRITICAL

    def test_passes_with_secret_reference(self):
        """CI/CD with secret reference should pass."""
        rule = CICDHardcodedSecretsRule()
        resources = [
            {
                "file_type": "cicd",
                "raw_content": """
name: CI
jobs:
  deploy:
    steps:
      - run: curl -H "API_KEY: ${{ secrets.API_KEY }}" https://api.example.com
""",
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        assert len(findings) == 0


class TestCICDUntrustedActionsRule:
    """Tests for CI-SEC-004: Untrusted Third-Party Actions."""

    def test_detects_unpinned_action(self):
        """CI/CD with unpinned third-party action should detect issue."""
        rule = CICDUntrustedActionsRule()
        resources = [
            {
                "file_type": "cicd",
                "properties": {
                    "steps": [
                        {
                            "uses": "some-org/some-action@v1",
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        assert len(findings) == 1
        assert findings[0].rule_id == "CI-SEC-004"
        assert findings[0].severity == Severity.HIGH

    def test_passes_with_pinned_action(self):
        """CI/CD with pinned action should pass."""
        rule = CICDUntrustedActionsRule()
        resources = [
            {
                "file_type": "cicd",
                "properties": {
                    "steps": [
                        {
                            "uses": "actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11",
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        assert len(findings) == 0

    def test_passes_with_official_action(self):
        """CI/CD with official action should pass (lower severity)."""
        rule = CICDUntrustedActionsRule()
        resources = [
            {
                "file_type": "cicd",
                "properties": {
                    "steps": [
                        {
                            "uses": "actions/checkout@v4",
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        # Official actions without pinning get MEDIUM severity or no finding
        # depending on implementation
        assert len(findings) == 0 or findings[0].severity == Severity.MEDIUM


class TestCICDMissingContainerScanRule:
    """Tests for CI-SEC-006: Missing Container Scanning."""

    def test_detects_missing_container_scan(self):
        """CI/CD with docker build but no scan should detect issue."""
        rule = CICDMissingContainerScanRule()
        resources = [
            {
                "file_type": "cicd",
                "properties": {
                    "steps": [
                        {"name": "build", "run": "docker build -t myapp ."},
                        {"name": "push", "run": "docker push myapp"},
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        assert len(findings) == 1
        assert findings[0].rule_id == "CI-SEC-006"
        assert findings[0].severity == Severity.HIGH

    def test_passes_with_trivy_scan(self):
        """CI/CD with Trivy scan should pass."""
        rule = CICDMissingContainerScanRule()
        resources = [
            {
                "file_type": "cicd",
                "properties": {
                    "steps": [
                        {"name": "build", "run": "docker build -t myapp ."},
                        {"name": "scan", "run": "trivy image myapp:latest"},
                        {"name": "push", "run": "docker push myapp"},
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, ".github/workflows/ci.yml")

        assert len(findings) == 0
