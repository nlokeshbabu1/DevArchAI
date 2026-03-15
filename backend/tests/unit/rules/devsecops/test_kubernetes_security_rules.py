"""
Unit Tests for Kubernetes Security Rules

Tests for K8S-SEC-001 to K8S-SEC-010
"""

import pytest

from app.rules.base import Severity
from app.rules.devsecops.kubernetes_security import (
    K8sMissingNetworkPolicyRule,
    K8sPrivilegedContainerRule,
    K8sRunAsRootAllowedRule,
    K8sMissingResourceLimitsRule,
    K8sMissingLivenessProbeRule,
    K8sMissingReadinessProbeRule,
    K8sHostPathVolumeRule,
    K8sPrivilegeEscalationAllowedRule,
    K8sMissingPodSecurityContextRule,
    K8sInsecureCapabilitiesRule,
)


class TestK8sMissingNetworkPolicyRule:
    """Tests for K8S-SEC-001: Missing Network Policy."""

    def test_detects_missing_network_policy(self):
        """Kubernetes with Deployment but no NetworkPolicy should detect issue."""
        rule = K8sMissingNetworkPolicyRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].rule_id == "K8S-SEC-001"
        assert findings[0].severity == Severity.HIGH

    def test_passes_with_network_policy(self):
        """Kubernetes with NetworkPolicy should pass."""
        rule = K8sMissingNetworkPolicyRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
            },
            {
                "file_type": "kubernetes",
                "kind": "NetworkPolicy",
                "name": "default-deny",
            },
        ]

        findings = rule.evaluate(resources, "k8s/")

        assert len(findings) == 0


class TestK8sPrivilegedContainerRule:
    """Tests for K8S-SEC-002: Privileged Container."""

    def test_detects_privileged_container(self):
        """Kubernetes with privileged: true should detect issue."""
        rule = K8sPrivilegedContainerRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                            "security_context": {
                                "privileged": True,
                            },
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].rule_id == "K8S-SEC-002"
        assert findings[0].severity == Severity.CRITICAL

    def test_passes_without_privileged(self):
        """Kubernetes without privileged should pass."""
        rule = K8sPrivilegedContainerRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                            "security_context": {
                                "privileged": False,
                            },
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 0


class TestK8sRunAsRootAllowedRule:
    """Tests for K8S-SEC-003: runAsRoot Allowed."""

    def test_detects_run_as_root(self):
        """Kubernetes without runAsNonRoot should detect issue."""
        rule = K8sRunAsRootAllowedRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "pod_security_context": {},
                    "containers": [
                        {
                            "name": "app",
                            "security_context": {},
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].rule_id == "K8S-SEC-003"
        assert findings[0].severity == Severity.HIGH

    def test_passes_with_run_as_non_root(self):
        """Kubernetes with runAsNonRoot: true should pass."""
        rule = K8sRunAsRootAllowedRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "pod_security_context": {
                        "runAsNonRoot": True,
                    },
                    "containers": [
                        {
                            "name": "app",
                            "security_context": {},
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 0


class TestK8sMissingResourceLimitsRule:
    """Tests for K8S-SEC-004: Missing Resource Limits."""

    def test_detects_missing_limits(self):
        """Kubernetes without resource limits should detect issue."""
        rule = K8sMissingResourceLimitsRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                            "resources": {},
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].rule_id == "K8S-SEC-004"
        assert findings[0].severity == Severity.MEDIUM

    def test_passes_with_limits(self):
        """Kubernetes with resource limits should pass."""
        rule = K8sMissingResourceLimitsRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                            "resources": {
                                "limits": {
                                    "cpu": "1",
                                    "memory": "512Mi",
                                },
                            },
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 0


class TestK8sMissingLivenessProbeRule:
    """Tests for K8S-SEC-005: Missing Liveness Probe."""

    def test_detects_missing_liveness_probe(self):
        """Kubernetes without liveness probe should detect issue."""
        rule = K8sMissingLivenessProbeRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].rule_id == "K8S-SEC-005"
        assert findings[0].severity == Severity.MEDIUM

    def test_passes_with_liveness_probe(self):
        """Kubernetes with liveness probe should pass."""
        rule = K8sMissingLivenessProbeRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                            "liveness_probe": {
                                "http_get": {
                                    "path": "/healthz",
                                    "port": 8080,
                                },
                            },
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 0


class TestK8sMissingReadinessProbeRule:
    """Tests for K8S-SEC-006: Missing Readiness Probe."""

    def test_detects_missing_readiness_probe(self):
        """Kubernetes without readiness probe should detect issue."""
        rule = K8sMissingReadinessProbeRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].rule_id == "K8S-SEC-006"
        assert findings[0].severity == Severity.MEDIUM

    def test_passes_with_readiness_probe(self):
        """Kubernetes with readiness probe should pass."""
        rule = K8sMissingReadinessProbeRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                            "readiness_probe": {
                                "http_get": {
                                    "path": "/ready",
                                    "port": 8080,
                                },
                            },
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 0


class TestK8sHostPathVolumeRule:
    """Tests for K8S-SEC-007: HostPath Volume Used."""

    def test_detects_host_path_volume(self):
        """Kubernetes with hostPath volume should detect issue."""
        rule = K8sHostPathVolumeRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "volumes": [
                        {
                            "name": "host-data",
                            "host_path": {
                                "path": "/mnt/data",  # Non-sensitive path
                                "type": "",
                            },
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].rule_id == "K8S-SEC-007"
        assert findings[0].severity == Severity.HIGH

    def test_detects_sensitive_host_path(self):
        """Kubernetes with sensitive hostPath should be CRITICAL."""
        rule = K8sHostPathVolumeRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "volumes": [
                        {
                            "name": "host-etc",
                            "host_path": {
                                "path": "/etc",
                                "type": "",
                            },
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_passes_with_empty_dir(self):
        """Kubernetes with emptyDir should pass."""
        rule = K8sHostPathVolumeRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "volumes": [
                        {
                            "name": "temp",
                            "empty_dir": {},
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 0


class TestK8sPrivilegeEscalationAllowedRule:
    """Tests for K8S-SEC-008: Privilege Escalation Allowed."""

    def test_detects_allow_privilege_escalation(self):
        """Kubernetes with allowPrivilegeEscalation: true should detect issue."""
        rule = K8sPrivilegeEscalationAllowedRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                            "security_context": {
                                "allowPrivilegeEscalation": True,
                            },
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].rule_id == "K8S-SEC-008"
        assert findings[0].severity == Severity.HIGH

    def test_passes_with_false_escalation(self):
        """Kubernetes with allowPrivilegeEscalation: false should pass."""
        rule = K8sPrivilegeEscalationAllowedRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                            "security_context": {
                                "allowPrivilegeEscalation": False,
                            },
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 0


class TestK8sMissingPodSecurityContextRule:
    """Tests for K8S-SEC-009: Missing Pod Security Context."""

    def test_detects_missing_pod_security_context(self):
        """Kubernetes without pod security context should detect issue."""
        rule = K8sMissingPodSecurityContextRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "pod_security_context": None,
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].rule_id == "K8S-SEC-009"
        assert findings[0].severity == Severity.MEDIUM

    def test_passes_with_pod_security_context(self):
        """Kubernetes with pod security context should pass."""
        rule = K8sMissingPodSecurityContextRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "pod_security_context": {
                        "runAsNonRoot": True,
                        "runAsUser": 1000,
                    },
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 0


class TestK8sInsecureCapabilitiesRule:
    """Tests for K8S-SEC-010: Insecure Capabilities."""

    def test_detects_dangerous_capability(self):
        """Kubernetes with dangerous capability should detect issue."""
        rule = K8sInsecureCapabilitiesRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                            "security_context": {
                                "capabilities": {
                                    "add": ["CAP_SYS_ADMIN"],
                                },
                            },
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 1
        assert findings[0].rule_id == "K8S-SEC-010"
        assert findings[0].severity == Severity.HIGH

    def test_passes_without_capabilities(self):
        """Kubernetes without added capabilities should pass."""
        rule = K8sInsecureCapabilitiesRule()
        resources = [
            {
                "file_type": "kubernetes",
                "kind": "Deployment",
                "name": "test-app",
                "properties": {
                    "containers": [
                        {
                            "name": "app",
                            "security_context": {},
                        },
                    ],
                },
            },
        ]

        findings = rule.evaluate(resources, "deployment.yaml")

        assert len(findings) == 0
