"""
Integration Tests for DevSecOps Scanner

Tests that scan sample repositories and verify expected findings.
"""

import os
import tempfile
from pathlib import Path

import pytest

from app.scanners.devsecops_scanner import DevSecOpsScanner, scan_repository


class TestIntegrationDockerfileScan:
    """Integration tests for Dockerfile scanning."""

    def test_scan_insecure_dockerfile(self):
        """Scan Dockerfile with multiple security issues."""
        dockerfile_content = """
FROM ubuntu:22.04

ENV API_KEY=sk_live_abc123def456ghi789
ENV PASSWORD=mysecretpassword123

RUN apt-get update && apt-get install -y openssh-server

COPY . .

EXPOSE 22 80 443 3306 5432 6379

CMD ["./app"]
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)

            result = scan_repository(tmpdir, "test-docker-repo")

            assert result["security_score"] < 100
            assert len(result["findings"]) > 0

            # Check for specific findings
            finding_ids = [f["rule_id"] for f in result["findings"]]
            assert "DKR-SEC-001" in finding_ids  # Root user
            assert "DKR-SEC-002" in finding_ids  # Latest tag (ubuntu is large)
            assert "DKR-SEC-003" in finding_ids  # Secrets
            assert "DKR-SEC-009" in finding_ids  # Large image

    def test_scan_secure_dockerfile(self):
        """Scan Dockerfile with security best practices."""
        dockerfile_content = """
FROM node:18.17.0-alpine3.18

WORKDIR /app

RUN addgroup -S app && adduser -S app -G app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

USER app

HEALTHCHECK --interval=30s --timeout=3s \\
  CMD curl -f http://localhost:3000/health || exit 1

EXPOSE 3000

CMD ["node", "server.js"]
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)

            result = scan_repository(tmpdir, "test-secure-docker-repo")

            # Should have better score
            assert result["security_score"] > 50

            # Check no critical findings
            critical_findings = [f for f in result["findings"] if f["severity"] == "critical"]
            assert len(critical_findings) == 0


class TestIntegrationKubernetesScan:
    """Integration tests for Kubernetes manifest scanning."""

    def test_scan_insecure_deployment(self):
        """Scan Kubernetes deployment with security issues."""
        deployment_content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: insecure-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: insecure
  template:
    metadata:
      labels:
        app: insecure
    spec:
      containers:
      - name: app
        image: myapp:latest
        securityContext:
          privileged: true
          allowPrivilegeEscalation: true
        env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
        volumeMounts:
        - name: host-data
          mountPath: /host
      volumes:
      - name: host-data
        hostPath:
          path: /var/data
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            k8s_path = Path(tmpdir) / "kubernetes"
            k8s_path.mkdir()
            deployment_path = k8s_path / "deployment.yaml"
            deployment_path.write_text(deployment_content)

            result = scan_repository(tmpdir, "test-k8s-insecure")

            assert result["security_score"] < 100
            assert len(result["findings"]) > 0

            finding_ids = [f["rule_id"] for f in result["findings"]]
            assert "K8S-SEC-002" in finding_ids  # Privileged
            assert "K8S-SEC-004" in finding_ids  # No resource limits
            assert "K8S-SEC-007" in finding_ids  # HostPath

    def test_scan_secure_deployment(self):
        """Scan Kubernetes deployment with security best practices."""
        deployment_content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: secure
  template:
    metadata:
      labels:
        app: secure
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: secure
            topologyKey: kubernetes.io/hostname
      containers:
      - name: app
        image: myapp:1.2.3
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
              - ALL
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "500m"
            memory: "256Mi"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        ports:
        - name: http
          containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: secure-app-service
spec:
  selector:
    app: secure
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: secure-app-network-policy
spec:
  podSelector:
    matchLabels:
      app: secure
  policyTypes:
  - Ingress
  - Egress
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            k8s_path = Path(tmpdir) / "kubernetes"
            k8s_path.mkdir()
            deployment_path = k8s_path / "deployment.yaml"
            deployment_path.write_text(deployment_content)

            result = scan_repository(tmpdir, "test-k8s-secure")

            # Should have much better score
            assert result["security_score"] > 70

            # Check no critical findings
            critical_findings = [f for f in result["findings"] if f["severity"] == "critical"]
            assert len(critical_findings) == 0


class TestIntegrationCICDScan:
    """Integration tests for CI/CD pipeline scanning."""

    def test_scan_insecure_pipeline(self):
        """Scan CI/CD pipeline with security issues."""
        workflow_content = """
name: CI/CD

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Setup Node
      uses: setup-node@v3

    - name: Install dependencies
      run: npm install

    - name: Build
      run: npm run build

    - name: Deploy
      run: |
        curl -X POST https://api.example.com/deploy \\
          -H "Authorization: Bearer ghp_abc123def456ghi789jkl012mno345pqr678"
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            github_path = Path(tmpdir) / ".github" / "workflows"
            github_path.mkdir(parents=True)
            workflow_path = github_path / "ci.yml"
            workflow_path.write_text(workflow_content)

            result = scan_repository(tmpdir, "test-cicd-insecure")

            assert result["security_score"] < 100

            finding_ids = [f["rule_id"] for f in result["findings"]]
            assert "CI-SEC-001" in finding_ids  # No security scan
            assert "CI-SEC-003" in finding_ids  # Hardcoded secret

    def test_scan_secure_pipeline(self):
        """Scan CI/CD pipeline with security best practices."""
        workflow_content = """
name: CI/CD

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

    - name: Setup Node
      uses: actions/setup-node@b4ffde65f46336ab88eb53be808477a3936bae11

    - name: Install dependencies
      run: npm ci

    - name: Run linter
      run: npm run lint

    - name: Run tests
      run: npm test

    - name: Security scan
      run: |
        npm audit
        npx snyk test

    - name: Build
      run: npm run build

    - name: Container scan
      run: |
        docker build -t myapp:$GITHUB_SHA .
        trivy image --severity HIGH,CRITICAL myapp:$GITHUB_SHA

    - name: Deploy
      if: github.ref == 'refs/heads/main'
      run: |
        curl -X POST https://api.example.com/deploy \\
          -H "Authorization: Bearer ${{ secrets.DEPLOY_TOKEN }}"
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            github_path = Path(tmpdir) / ".github" / "workflows"
            github_path.mkdir(parents=True)
            workflow_path = github_path / "ci.yml"
            workflow_path.write_text(workflow_content)

            result = scan_repository(tmpdir, "test-cicd-secure")

            # Should have better score
            assert result["security_score"] > 60


class TestIntegrationFullRepository:
    """Integration tests for full repository scanning."""

    def test_scan_full_devops_repo(self):
        """Scan a complete DevOps repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create Dockerfile
            dockerfile = tmpdir / "Dockerfile"
            dockerfile.write_text("""
FROM python:3.11-slim
WORKDIR /app
RUN adduser -S app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
USER app
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "app.py"]
""")

            # Create Kubernetes manifests
            k8s_dir = tmpdir / "kubernetes"
            k8s_dir.mkdir()
            (k8s_dir / "deployment.yaml").write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
      - name: app
        image: myapp:1.0.0
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "500m"
            memory: "256Mi"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8000
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: myapp-network-policy
spec:
  podSelector:
    matchLabels:
      app: myapp
  policyTypes:
  - Ingress
""")

            # Create CI/CD workflow
            github_dir = tmpdir / ".github" / "workflows"
            github_dir.mkdir(parents=True)
            (github_dir / "ci.yml").write_text("""
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run tests
      run: pytest
    - name: Security scan
      run: |
        pip install safety
        safety check
    - name: Build image
      run: docker build -t myapp .
""")

            result = scan_repository(tmpdir, "test-full-repo")

            # Verify scan completed
            assert result["repository"] == "test-full-repo"
            assert "security_score" in result
            assert "findings" in result
            assert len(result["files_scanned"]) > 0

            # Should have scanned multiple file types
            files_scanned = result["files_scanned"]
            assert any("Dockerfile" in f for f in files_scanned)
            assert any(".yaml" in f for f in files_scanned)
            assert any(".yml" in f for f in files_scanned)
