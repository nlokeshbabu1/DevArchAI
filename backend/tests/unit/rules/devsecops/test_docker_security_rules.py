"""
Unit Tests for Docker Security Rules

Tests for DKR-SEC-001 to DKR-SEC-010
"""

import pytest

from app.rules.base import Severity
from app.rules.devsecops.docker_security import (
    DockerRootUserRule,
    DockerLatestTagRule,
    DockerSecretsInDockerfileRule,
    DockerMissingUserInstructionRule,
    DockerAddInsteadOfCopyRule,
    DockerMissingHealthcheckRule,
    DockerPrivilegedContainerRule,
    DockerResourceLimitsRule,
    DockerLargeBaseImageRule,
    DockerSSHInstalledRule,
)


class TestDockerRootUserRule:
    """Tests for DKR-SEC-001: Container Running as Root."""

    def test_detects_root_user(self):
        """Dockerfile without USER should detect issue."""
        rule = DockerRootUserRule()
        resources = [{
            "file_type": "dockerfile",
            "user": None,
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1
        assert findings[0].rule_id == "DKR-SEC-001"
        assert findings[0].severity == Severity.HIGH

    def test_detects_explicit_root(self):
        """Dockerfile with USER root should detect issue."""
        rule = DockerRootUserRule()
        resources = [{
            "file_type": "dockerfile",
            "user": "root",
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1
        assert findings[0].rule_id == "DKR-SEC-001"

    def test_passes_with_nonroot_user(self):
        """Dockerfile with non-root USER should pass."""
        rule = DockerRootUserRule()
        resources = [{
            "file_type": "dockerfile",
            "user": "appuser",
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0

    def test_passes_with_numeric_nonroot(self):
        """Dockerfile with numeric non-root UID should pass."""
        rule = DockerRootUserRule()
        resources = [{
            "file_type": "dockerfile",
            "user": "1000",
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0


class TestDockerLatestTagRule:
    """Tests for DKR-SEC-002: Latest Tag Used."""

    def test_detects_latest_tag(self):
        """Dockerfile with :latest should detect issue."""
        rule = DockerLatestTagRule()
        resources = [{
            "file_type": "dockerfile",
            "base_image": {
                "full": "node:latest",
                "repository": "node",
                "tag": "latest",
                "is_latest": True,
            },
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1
        assert findings[0].rule_id == "DKR-SEC-002"
        assert findings[0].severity == Severity.MEDIUM

    def test_detects_no_tag(self):
        """Dockerfile without tag (implicit latest) should detect issue."""
        rule = DockerLatestTagRule()
        resources = [{
            "file_type": "dockerfile",
            "base_image": {
                "full": "node",
                "repository": "node",
                "tag": None,
                "is_latest": True,
            },
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1

    def test_passes_with_version_tag(self):
        """Dockerfile with specific version should pass."""
        rule = DockerLatestTagRule()
        resources = [{
            "file_type": "dockerfile",
            "base_image": {
                "full": "node:18.17.0-alpine",
                "repository": "node",
                "tag": "18.17.0-alpine",
                "is_latest": False,
            },
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0


class TestDockerSecretsInDockerfileRule:
    """Tests for DKR-SEC-003: Secrets in Dockerfile."""

    def test_detects_api_key(self):
        """Dockerfile with API key should detect issue."""
        rule = DockerSecretsInDockerfileRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {
                    "instruction": "ENV",
                    "arguments": "API_KEY sk_live_abc123def456ghi789jkl012",
                    "line_number": 5,
                },
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1
        assert findings[0].rule_id == "DKR-SEC-003"
        assert findings[0].severity == Severity.CRITICAL

    def test_detects_password(self):
        """Dockerfile with password should detect issue."""
        rule = DockerSecretsInDockerfileRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {
                    "instruction": "RUN",
                    "arguments": "echo 'password=mysecretpassword123'",
                    "line_number": 10,
                },
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1

    def test_passes_with_placeholder(self):
        """Dockerfile with placeholder should pass."""
        rule = DockerSecretsInDockerfileRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {
                    "instruction": "ARG",
                    "arguments": "API_KEY=${API_KEY}",
                    "line_number": 5,
                },
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0

    def test_passes_with_env_reference(self):
        """Dockerfile with environment variable reference should pass."""
        rule = DockerSecretsInDockerfileRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {
                    "instruction": "ENV",
                    "arguments": "API_KEY=$API_KEY",
                    "line_number": 5,
                },
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0


class TestDockerMissingUserInstructionRule:
    """Tests for DKR-SEC-004: Missing USER Instruction."""

    def test_detects_missing_user(self):
        """Dockerfile without USER instruction should detect issue."""
        rule = DockerMissingUserInstructionRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {"instruction": "FROM", "arguments": "node:18"},
                {"instruction": "RUN", "arguments": "npm install"},
                {"instruction": "CMD", "arguments": "node app.js"},
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1
        assert findings[0].rule_id == "DKR-SEC-004"
        assert findings[0].severity == Severity.HIGH

    def test_passes_with_user_instruction(self):
        """Dockerfile with USER instruction should pass."""
        rule = DockerMissingUserInstructionRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {"instruction": "FROM", "arguments": "node:18"},
                {"instruction": "RUN", "arguments": "adduser -S app"},
                {"instruction": "USER", "arguments": "app"},
                {"instruction": "CMD", "arguments": "node app.js"},
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0


class TestDockerAddInsteadOfCopyRule:
    """Tests for DKR-SEC-005: ADD Used Instead of COPY."""

    def test_detects_add_for_regular_file(self):
        """Dockerfile with ADD for regular file should detect issue."""
        rule = DockerAddInsteadOfCopyRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {
                    "instruction": "ADD",
                    "arguments": "./app /app",
                    "line_number": 5,
                },
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1
        assert findings[0].rule_id == "DKR-SEC-005"
        assert findings[0].severity == Severity.LOW

    def test_passes_add_for_tar(self):
        """Dockerfile with ADD for tar file should pass."""
        rule = DockerAddInsteadOfCopyRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {
                    "instruction": "ADD",
                    "arguments": "app.tar.gz /app",
                    "line_number": 5,
                },
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        # ADD for tar files is acceptable (extracts archives)
        assert len(findings) == 0

    def test_passes_with_copy(self):
        """Dockerfile with COPY should pass."""
        rule = DockerAddInsteadOfCopyRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {
                    "instruction": "COPY",
                    "arguments": "./app /app",
                    "line_number": 5,
                },
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0


class TestDockerMissingHealthcheckRule:
    """Tests for DKR-SEC-006: Missing HEALTHCHECK."""

    def test_detects_missing_healthcheck(self):
        """Dockerfile without HEALTHCHECK should detect issue."""
        rule = DockerMissingHealthcheckRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {"instruction": "FROM", "arguments": "node:18"},
                {"instruction": "CMD", "arguments": "node app.js"},
            ],
            "healthcheck": None,
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1
        assert findings[0].rule_id == "DKR-SEC-006"
        assert findings[0].severity == Severity.LOW

    def test_passes_with_healthcheck(self):
        """Dockerfile with HEALTHCHECK should pass."""
        rule = DockerMissingHealthcheckRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {"instruction": "FROM", "arguments": "node:18"},
                {"instruction": "HEALTHCHECK", "arguments": "CMD curl -f http://localhost/"},
                {"instruction": "CMD", "arguments": "node app.js"},
            ],
            "healthcheck": {"cmd": "curl -f http://localhost/"},
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0


class TestDockerPrivilegedContainerRule:
    """Tests for DKR-SEC-007: Privileged Container."""

    def test_detects_privileged_dockerfile(self):
        """Dockerfile with privileged hint should detect issue."""
        rule = DockerPrivilegedContainerRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {
                    "instruction": "RUN",
                    "arguments": "--privileged docker run app",
                    "line_number": 10,
                },
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1
        assert findings[0].rule_id == "DKR-SEC-007"
        assert findings[0].severity == Severity.HIGH

    def test_detects_privileged_kubernetes(self):
        """Kubernetes with privileged: true should detect issue."""
        rule = DockerPrivilegedContainerRule()
        resources = [{
            "file_type": "kubernetes",
            "kind": "Deployment",
            "properties": {
                "name": "test-app",
                "containers": [
                    {
                        "name": "app",
                        "security_context": {
                            "privileged": True,
                        },
                    },
                ],
            },
        }]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_passes_without_privileged(self):
        """Kubernetes without privileged should pass."""
        rule = DockerPrivilegedContainerRule()
        resources = [{
            "file_type": "kubernetes",
            "kind": "Deployment",
            "properties": {
                "name": "test-app",
                "containers": [
                    {
                        "name": "app",
                        "security_context": {
                            "privileged": False,
                        },
                    },
                ],
            },
        }]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 0


class TestDockerLargeBaseImageRule:
    """Tests for DKR-SEC-009: Large Base Image."""

    def test_detects_large_image(self):
        """Dockerfile with large base image should detect issue."""
        rule = DockerLargeBaseImageRule()
        resources = [{
            "file_type": "dockerfile",
            "base_image": {
                "full": "ubuntu:22.04",
                "repository": "ubuntu",
            },
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1
        assert findings[0].rule_id == "DKR-SEC-009"
        assert findings[0].severity == Severity.LOW

    def test_passes_with_alpine(self):
        """Dockerfile with alpine should pass."""
        rule = DockerLargeBaseImageRule()
        resources = [{
            "file_type": "dockerfile",
            "base_image": {
                "full": "alpine:3.18",
                "repository": "alpine",
            },
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0

    def test_passes_with_slim(self):
        """Dockerfile with slim variant should pass."""
        rule = DockerLargeBaseImageRule()
        resources = [{
            "file_type": "dockerfile",
            "base_image": {
                "full": "python:3.11-slim",
                "repository": "python",
            },
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0


class TestDockerSSHInstalledRule:
    """Tests for DKR-SEC-010: SSH Installed in Container."""

    def test_detects_ssh_install(self):
        """Dockerfile with SSH installation should detect issue."""
        rule = DockerSSHInstalledRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {
                    "instruction": "RUN",
                    "arguments": "apt-get update && apt-get install -y openssh-server",
                    "line_number": 5,
                },
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 1
        assert findings[0].rule_id == "DKR-SEC-010"
        assert findings[0].severity == Severity.MEDIUM

    def test_passes_without_ssh(self):
        """Dockerfile without SSH should pass."""
        rule = DockerSSHInstalledRule()
        resources = [{
            "file_type": "dockerfile",
            "instructions": [
                {
                    "instruction": "RUN",
                    "arguments": "apt-get update && apt-get install -y curl",
                    "line_number": 5,
                },
            ],
        }]

        findings = rule.evaluate(resources, "Dockerfile")

        assert len(findings) == 0
