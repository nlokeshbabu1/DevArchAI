"""
Tests for Helm Chart Scanner
"""

import pytest

from app.rules.base import Severity
from app.scanners.helm_scanner import HelmScanner


class TestHelmScanner:
    """Test Helm chart security scanner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = HelmScanner()
    
    def test_container_running_as_root(self):
        """Test HELM-SEC-001: Container running as root."""
        files = [
            {
                "file_path": "mychart/values.yaml",
                "content": """
securityContext:
  runAsRoot: true
  runAsUser: 0
""",
            }
        ]
        
        findings = self.scanner.scan("repo", files)
        
        assert len(findings) >= 1
        assert any(f.rule_id == "HELM-SEC-001" for f in findings)
        root_finding = next(f for f in findings if f.rule_id == "HELM-SEC-001")
        assert root_finding.severity == Severity.CRITICAL
    
    def test_privileged_container(self):
        """Test HELM-SEC-002: Privileged container."""
        files = [
            {
                "file_path": "mychart/values.yaml",
                "content": """
securityContext:
  runAsNonRoot: true  # Secure
  privileged: true
""",
            }
        ]
        
        findings = self.scanner.scan("repo", files)
        
        assert len(findings) >= 1
        assert any(f.rule_id == "HELM-SEC-002" for f in findings)
        priv_finding = next(f for f in findings if f.rule_id == "HELM-SEC-002")
        assert priv_finding.severity == Severity.CRITICAL
    
    def test_missing_resource_limits(self):
        """Test HELM-REL-001: Missing resource limits."""
        files = [
            {
                "file_path": "mychart/values.yaml",
                "content": """
securityContext:
  runAsNonRoot: true  # Secure
  
resources: {}
""",
            }
        ]
        
        findings = self.scanner.scan("repo", files)
        
        assert len(findings) >= 1
        assert any(f.rule_id == "HELM-REL-001" for f in findings)
        limits_finding = next(f for f in findings if f.rule_id == "HELM-REL-001")
        assert limits_finding.severity == Severity.HIGH
    
    def test_missing_probes(self):
        """Test HELM-REL-002: Missing liveness/readiness probes."""
        files = [
            {
                "file_path": "mychart/values.yaml",
                "content": """
securityContext:
  runAsNonRoot: true  # Secure

resources:
  limits:
    cpu: 500m
    memory: 512Mi

livenessProbe: {}
readinessProbe: {}
""",
            }
        ]
        
        findings = self.scanner.scan("repo", files)
        
        assert len(findings) >= 2  # Both liveness and readiness
        probe_findings = [f for f in findings if f.rule_id == "HELM-REL-002"]
        assert len(probe_findings) >= 2
        assert all(f.severity == Severity.MEDIUM for f in probe_findings)
    
    def test_single_replica(self):
        """Test HELM-REL-003: Single replica deployment."""
        files = [
            {
                "file_path": "mychart/values.yaml",
                "content": """
securityContext:
  runAsNonRoot: true  # Secure

resources:
  limits:
    cpu: 500m
    memory: 512Mi

livenessProbe:
  httpGet:
    path: /healthz
    port: 8080

readinessProbe:
  httpGet:
    path: /ready
    port: 8080

replicaCount: 1

image:
  repository: myapp
  tag: v1.2.3  # Secure
""",
            }
        ]
        
        findings = self.scanner.scan("repo", files)
        
        assert len(findings) >= 1
        assert any(f.rule_id == "HELM-REL-003" for f in findings)
        replica_finding = next(f for f in findings if f.rule_id == "HELM-REL-003")
        assert replica_finding.severity == Severity.MEDIUM
    
    def test_image_tag_not_pinned(self):
        """Test HELM-IMG-001: Image tag not pinned."""
        files = [
            {
                "file_path": "mychart/values.yaml",
                "content": """
securityContext:
  runAsNonRoot: true  # Secure

resources:
  limits:
    cpu: 500m
    memory: 512Mi

livenessProbe:
  httpGet:
    path: /healthz
    port: 8080

readinessProbe:
  httpGet:
    path: /ready
    port: 8080

replicaCount: 3  # Secure

image:
  repository: myapp
  tag: latest
""",
            }
        ]
        
        findings = self.scanner.scan("repo", files)
        
        assert len(findings) >= 1
        assert any(f.rule_id == "HELM-IMG-001" for f in findings)
        image_finding = next(f for f in findings if f.rule_id == "HELM-IMG-001")
        assert image_finding.severity == Severity.HIGH
    
    def test_chart_version_not_pinned(self):
        """Test HELM-VER-001: Chart dependency version not pinned."""
        files = [
            {
                "file_path": "mychart/Chart.yaml",
                "content": """
dependencies:
  - name: redis
    repository: https://charts.bitnami.com/bitnami
    version: "*"
""",
            }
        ]
        
        findings = self.scanner.scan("repo", files)
        
        assert len(findings) >= 1
        assert any(f.rule_id == "HELM-VER-001" for f in findings)
        version_finding = next(f for f in findings if f.rule_id == "HELM-VER-001")
        assert version_finding.severity == Severity.LOW
    
    def test_secure_helm_chart(self):
        """Test that secure Helm chart passes."""
        files = [
            {
                "file_path": "mychart/values.yaml",
                "content": """
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  privileged: false

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 30

readinessProbe:
  httpGet:
    path: /ready
    port: 8080

replicaCount: 3

image:
  repository: myapp
  tag: v1.2.3
""",
            },
            {
                "file_path": "mychart/Chart.yaml",
                "content": """
dependencies:
  - name: redis
    repository: https://charts.bitnami.com/bitnami
    version: "16.10.0"
""",
            }
        ]
        
        findings = self.scanner.scan("repo", files)
        
        # Should have no critical/high severity findings for secure chart
        critical_high = [f for f in findings if f.severity in [Severity.CRITICAL, Severity.HIGH]]
        assert len(critical_high) == 0
