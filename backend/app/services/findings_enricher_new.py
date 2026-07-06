"""Findings enrichment service - Production-grade with guaranteed fallback.

This module provides:
- AI-powered enrichment (always attempted first)
- Static FIX_EXAMPLES (guaranteed fallback)
- Documentation URL mapping
- Synchronous and async support
"""

import hashlib
import json
from typing import Any

import structlog

from app.ai.engine import BaseLLMProvider, get_llm_provider
from app.config import settings
from app.rule_engine.base import RuleFinding
from app.services.devops_documentation import get_documentation_url

logger = structlog.get_logger(__name__)


# Static fix examples library (GUARANTEED FALLBACK)
FIX_EXAMPLES: dict[str, dict[str, Any]] = {
    # Terraform State Management
    "TF-STATE-001": {
        "summary": "Terraform state is stored locally without remote backend configuration.",
        "risk": "Terraform state stored locally cannot be shared across team members or CI/CD pipelines, leading to state drift, failed applies, and potential infrastructure corruption.",
        "impact": "Multiple engineers running terraform apply simultaneously can corrupt state, causing infrastructure drift and deployment failures.",
        "fix_code": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
        "fix_example": '''terraform {
  backend "s3" {
    bucket         = "tf-state-prod"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}''',
        "best_practices": [
            "Use separate state files for different environments",
            "Enable versioning on the S3 bucket",
            "Restrict IAM access to state bucket",
        ],
        "confidence": 0.95,
    },
    "TF-STATE-002": {
        "summary": "Terraform root module does not have a remote backend configured.",
        "risk": "Without remote backend, Terraform state is stored locally, preventing team collaboration and risking state loss.",
        "impact": "Team members cannot collaborate on infrastructure changes. State loss results in inability to manage existing resources.",
        "fix_code": '''terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "project/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
  }
}''',
        "fix_example": '''terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "project/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
  }
}''',
        "best_practices": [
            "Use DynamoDB for state locking",
            "Enable encryption for state files",
        ],
        "confidence": 0.95,
    },
    # Kubernetes Rules
    "K8S-001": {
        "risk": "Containers without resource limits can consume all node resources, causing node instability.",
        "impact": "Resource exhaustion leads to node crashes, pod evictions, and service outages.",
        "fix_example": '''apiVersion: v1
kind: Pod
metadata:
  name: resource-limited-pod
spec:
  containers:
  - name: app
    image: myapp:1.0.0
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"
      limits:
        memory: "512Mi"
        cpu: "500m"''',
    },
    "K8S-002": {
        "risk": "Containers running as root have full access to the host system if they escape.",
        "impact": "Container breakout vulnerabilities can lead to full host compromise.",
        "fix_example": '''apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
  containers:
  - name: app
    image: myapp:1.0.0
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
          - ALL''',
    },
    "K8S-REL-001": {
        "risk": "Single replica deployments have no redundancy and will cause outage during failures.",
        "impact": "Service downtime during pod failures, updates, or node maintenance. No high availability.",
        "fix_example": '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
spec:
  replicas: 3  # Run multiple replicas for HA
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:1.0.0''',
    },
    "K8S-SEC-001": {
        "summary": "Missing NetworkPolicy allows unrestricted pod-to-pod communication in the cluster.",
        "risk": "Pods without network isolation can communicate freely, increasing attack surface.",
        "impact": "Lateral movement, data exfiltration, and unauthorized access to sensitive services.",
        "fix_code": '''apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress''',
        "fix_example": '''apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress''',
    },
    "K8S-SCALE-001": {
        "summary": "Missing HorizontalPodAutoscaler prevents automatic scaling based on resource utilization.",
        "risk": "Application cannot scale automatically during traffic spikes or high load.",
        "impact": "Service degradation, downtime during peak traffic, and poor resource utilization.",
        "fix_code": '''apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70''',
        "fix_example": '''apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70''',
        "best_practices": [
            "Set appropriate min/max replicas based on baseline and peak traffic",
            "Use custom metrics for application-specific scaling",
            "Configure scale-down stabilization to prevent flapping",
            "Monitor HPA events and metrics for optimization",
        ],
    },
    # CI/CD Rules
    "CI-SEC-001": {
        "risk": "CI/CD pipeline does not include security scanning steps.",
        "impact": "Security vulnerabilities, supply chain attacks, and compliance violations in production.",
        "fix_example": '''# GitHub Actions with security scanning
name: CI/CD Pipeline
on: [push]
jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
''',
    },
    "CI-SEC-002": {
        "risk": "CI/CD pipeline does not scan container images for vulnerabilities.",
        "impact": "Vulnerable containers deployed to production can be exploited.",
        "fix_example": '''# Add container scanning
- name: Build and scan container
  uses: docker/build-push-action@v5
  with:
    push: false
    tags: app:${{ github.sha }}
- name: Run Trivy on image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'app:${{ github.sha }}'
    format: 'table'
''',
    },
    "CI-SEC-003": {
        "summary": "CI/CD pipeline uses cloud provider authentication without OIDC.",
        "risk": "Long-lived credentials can be leaked and provide persistent access to attackers.",
        "impact": "Credential theft, unauthorized access to cloud resources, supply chain attacks.",
        "fix_code": '''# Use OIDC for AWS (preferred)
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789:role/github-actions
    aws-region: us-east-1
''',
        "fix_example": '''name: Deploy
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    # Use OIDC for AWS (preferred)
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789:role/github-actions
        aws-region: us-east-1

    # Use secrets for application config
    - name: Deploy
      env:
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
        API_KEY: ${{ secrets.API_KEY }}
      run: |
        ./deploy.sh''',
        "best_practices": [
            "Use OIDC instead of long-lived credentials",
            "Never print secrets in logs",
            "Rotate secrets regularly",
            "Use environment-specific secrets",
        ],
        "confidence": 0.95,
    },
    "CI-SCALE-001": {
        "summary": "CI/CD pipeline does not use caching for faster builds.",
        "risk": "Without build caching, every CI/CD run downloads dependencies from scratch, wasting time and resources.",
        "impact": "Slow build times (5-10x slower). Increased CI/CD costs. Wasted compute resources.",
        "fix_code": '''# Add dependency caching
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-''',
        "fix_example": '''name: CI Pipeline
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    # Cache dependencies
    - name: Cache node modules
      uses: actions/cache@v4
      with:
        path: ~/.npm
        key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
        restore-keys: |
          ${{ runner.os }}-node-

    # Use cached dependencies
    - name: Install dependencies
      run: npm ci''',
        "best_practices": [
            "Cache dependencies between runs",
            "Use matrix builds for parallel testing",
            "Split large workflows into smaller jobs",
        ],
        "confidence": 0.90,
    },
    "CI-REL-001": {
        "summary": "CI/CD pipeline does not have approval gates for production deployments.",
        "risk": "Without approval gates, untested or broken code can be deployed to production automatically.",
        "impact": "Production outages, difficult rollbacks, poor deployment reliability.",
        "fix_code": '''# Add deployment approval gate
jobs:
  deploy-production:
    needs: [test, staging]
    environment:
      name: production
      url: https://myapp.com''',
        "fix_example": '''name: Deploy Pipeline
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - run: npm test

  deploy-staging:
    needs: test
    environment: staging
    steps:
    - run: ./deploy.sh staging

  deploy-production:
    needs: [test, deploy-staging]
    environment:
      name: production
      url: https://myapp.com
    steps:
    - run: ./deploy.sh production''',
        "best_practices": [
            "Use environment protection rules",
            "Require manual approval for production",
            "Implement automatic rollback on failure",
        ],
        "confidence": 0.90,
    },
    "CI-REL-002": {
        "summary": "CI/CD pipeline does not include automated testing.",
        "risk": "Without automated testing, bugs and regressions reach production, causing service outages.",
        "impact": "Production bugs, service outages, customer dissatisfaction, and increased support costs.",
        "fix_code": '''# Add automated testing
- name: Run unit tests
  run: npm run test:unit
- name: Run integration tests
  run: npm run test:integration''',
        "fix_example": '''name: CI/CD Pipeline
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    # Unit tests
    - name: Run unit tests
      run: npm run test:unit

    # Integration tests
    - name: Run integration tests
      run: npm run test:integration

    # Code coverage
    - name: Check code coverage
      run: npm run test:coverage''',
        "best_practices": [
            "Run tests on every commit",
            "Fail builds on test failures",
            "Track code coverage over time",
        ],
        "confidence": 0.90,
    },
    # Docker Rules
    "DOCKER-001": {
        "risk": "Containers running as root can exploit container vulnerabilities to escape and compromise the host.",
        "impact": "Root container access increases attack surface and potential damage from container breakout.",
        "fix_example": '''FROM node:18.17.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \\
    adduser -S nodejs -u 1001

USER nodejs

EXPOSE 3000
CMD ["node", "server.js"]''',
    },
    "DOCKER-002": {
        "risk": "Using 'latest' tag leads to non-deterministic builds, making it impossible to reproduce builds.",
        "impact": "Unexpected base image changes can introduce vulnerabilities or breaking changes.",
        "fix_example": '''# Pin specific version
FROM node:18.17.0-alpine3.18

# Or use digest for immutability
FROM node@sha256:abc123def456...''',
    },
    "DKR-REL-001": {
        "summary": "Docker container lacks HEALTHCHECK instruction for health monitoring.",
        "risk": "Without HEALTHCHECK, container orchestration systems cannot detect if the application is healthy.",
        "impact": "Unhealthy containers may continue receiving traffic, causing service degradation.",
        "fix_code": '''HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1''',
        "fix_example": '''FROM node:18.17.0-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

# Create non-root user
RUN addgroup --gid 1000 appgroup && adduser -u 1000 -S appuser -G appgroup
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000
CMD ["node", "server.js"]''',
        "best_practices": [
            "Set appropriate interval and timeout for your application",
            "Use /health or /healthz endpoint for health checks",
            "Ensure health endpoint checks critical dependencies",
        ],
        "confidence": 0.95,
    },
    "DKR-SCALE-001": {
        "summary": "Base image uses 'latest' tag which can cause inconsistent deployments and non-reproducible builds.",
        "risk": "Using 'latest' tag leads to non-deterministic builds, making it impossible to reproduce builds or rollback to known-good versions. Unexpected base image changes can break your application.",
        "impact": "Your Docker builds will pull different base images over time, potentially introducing breaking changes, security vulnerabilities, or compatibility issues without your knowledge. This makes debugging and rollbacks extremely difficult.",
        "fix_code": '''# Pin specific version instead of latest
FROM node:18.17.0-alpine3.18

# Or use digest for complete immutability
FROM node@sha256:abc123def456...''',
        "fix_example": '''# Bad: Using latest tag (non-deterministic)
# FROM node:latest

# Good: Pin specific version
FROM node:18.17.0-alpine3.18

# Better: Use digest for complete immutability
# FROM node@sha256:1234567890abcdef...''',
        "full_example": '''# Production-ready Dockerfile with pinned base image
FROM node:18.17.0-alpine3.18

WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user for security
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
USER appuser

# Add healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000
CMD ["node", "server.js"]''',
        "best_practices": [
            "Always pin base images to specific versions (e.g., node:18.17.0-alpine3.18)",
            "Consider using image digests for complete immutability (e.g., node@sha256:...)",
            "Use automated tools like Dependabot to update base image versions",
            "Document base image versions in your README or documentation",
            "Test base image updates in a staging environment before production",
        ],
        "confidence": 0.95,
    },
    "DKR-SEC-002": {
        "summary": "Potential secrets exposed in Dockerfile ENV variables which can be accessed by anyone with access to the image.",
        "risk": "Secrets in Dockerfile ENV variables are stored in image layers and can be extracted by anyone with access to the image. This includes API keys, database passwords, and other sensitive credentials.",
        "impact": "Exposed credentials can lead to unauthorized access to databases, APIs, cloud resources, and sensitive data. This can result in data breaches, financial loss, and compliance violations.",
        "fix_code": '''# Use build arguments for build-time secrets (not stored in final image)
ARG API_KEY
RUN echo "Building with API key" # Don't echo the actual value

# Or use runtime environment variables (passed at container start)
# docker run -e API_KEY=secret my-image

# Or use Docker secrets (for Swarm)
# docker secret create my_secret secret.txt
# docker service create --secret my_secret my-service''',
        "fix_example": '''# Bad: Secret in ENV (stored in image layer)
# ENV API_KEY=sk-1234567890
# ENV DATABASE_PASSWORD=supersecret

# Good: Use ARG for build-time (not in final image)
ARG API_KEY
RUN echo "Building application..."

# Better: Pass secrets at runtime
# docker run -e API_KEY=$API_KEY my-image

# Best: Use secret management tools (AWS Secrets Manager, HashiCorp Vault)''',
        "full_example": '''FROM node:18.17.0-alpine3.18

WORKDIR /app

# Use ARG for build-time variables (not stored in final image)
ARG NPM_TOKEN
RUN if [ -n "$NPM_TOKEN" ]; then \\
      echo "//registry.npmjs.org/:_authToken=$NPM_TOKEN" > ~/.npmrc; \\
    fi

# Copy and install dependencies
COPY package*.json ./
RUN npm ci --only=production

COPY . .

# Create non-root user
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
USER appuser

# Don't include secrets in the image!
# Pass them at runtime: docker run -e API_KEY=secret my-image

EXPOSE 3000
CMD ["node", "server.js"]''',
        "best_practices": [
            "Never hardcode secrets in Dockerfile ENV instructions",
            "Use build arguments (ARG) for build-time secrets - they're not in final image",
            "Pass secrets at runtime using environment variables or Docker secrets",
            "Use secret management tools like AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault",
            "Scan Dockerfiles with tools like Hadolint or Trivy to detect exposed secrets",
        ],
        "confidence": 0.95,
    },
    "DKR-COST-001": {
        "summary": "Using a large base image increases build time, storage costs, and attack surface.",
        "risk": "Large base images like Ubuntu or Debian take longer to build, pull, and deploy. They also contain more packages that could have security vulnerabilities, increasing your attack surface.",
        "impact": "Slower CI/CD pipelines, increased storage costs, longer deployment times, and higher security risk from unnecessary packages. Can also increase cloud egress costs for multi-region deployments.",
        "fix_code": '''# Use Alpine or distroless images for smaller size
FROM node:18.17.0-alpine3.18

# Or use distroless for minimal attack surface
FROM gcr.io/distroless/nodejs18-debian11''',
        "fix_example": '''# Bad: Large base image (~150MB)
# FROM ubuntu:22.04
# FROM debian:bullseye

# Good: Alpine image (~50MB)
FROM node:18.17.0-alpine3.18

# Better: Distroless image (~30MB)
# FROM gcr.io/distroless/nodejs18-debian11

# Best: Multi-stage build for minimal final image
FROM node:18.17.0 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18.17.0-alpine3.18
WORKDIR /app
COPY --from=builder /app/dist ./dist
CMD ["node", "dist/index.js"]''',
        "full_example": '''# Multi-stage build for minimal production image
FROM node:18.17.0 AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production image - minimal size
FROM node:18.17.0-alpine3.18

WORKDIR /app

# Copy only production dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy built application
COPY --from=builder /app/dist ./dist

# Create non-root user
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

EXPOSE 3000
CMD ["node", "dist/index.js"]''',
        "best_practices": [
            "Use Alpine-based images for smaller size (e.g., node:18-alpine)",
            "Consider distroless images for minimal attack surface",
            "Use multi-stage builds to keep production images small",
            "Regularly scan images for vulnerabilities with Trivy or Snyk",
            "Remove unnecessary packages and files to reduce image size",
        ],
        "confidence": 0.95,
    },
    "DKR-SEC-001": {
        "risk": "Containers running as root can exploit container vulnerabilities to escape and compromise the host.",
        "impact": "Root container access increases attack surface and potential damage from container breakout.",
        "fix_example": '''FROM node:18.17.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

# Create non-root user and group
RUN groupadd --gid 1000 appgroup && \\
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set proper ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

EXPOSE 3000
CMD ["node", "server.js"]''',
    },
}


class AIFixEnrichmentService:
    """AI-powered fix enrichment service with caching and guaranteed fallback."""

    def __init__(self, llm_provider: BaseLLMProvider | None = None):
        self.llm_provider = llm_provider

        # Determine if we should use mock based on provider and API keys
        provider = settings.LLM_PROVIDER.lower()
        if provider == "mock":
            self._use_mock = True
        elif provider == "gemini":
            self._use_mock = not settings.GEMINI_API_KEY
        elif provider == "openai":
            self._use_mock = not settings.OPENAI_API_KEY
        elif provider == "anthropic":
            self._use_mock = not settings.ANTHROPIC_API_KEY
        else:
            self._use_mock = True  # Default to mock for unknown providers

        self._cache: dict[str, dict[str, Any]] = {}  # In-memory cache

    def _get_cache_key(self, rule_id: str, file_content_hash: str) -> str:
        """Generate cache key from rule_id and file content hash."""
        return f"{rule_id}:{file_content_hash}"

    def _hash_content(self, content: str) -> str:
        """Hash file content for cache key."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def generate_fix(self, finding: dict[str, Any], file_content: str = "") -> dict[str, Any]:
        """
        Generate AI fix suggestion for a finding with guaranteed fallback.

        Args:
            finding: Finding dict with rule_id, title, severity, file_type
            file_content: Optional actual file content for context

        Returns:
            dict with summary, risk, fix_code, full_example, impact, confidence
        """
        rule_id = finding.get("rule_id", "")
        logger.info("Generating fix", rule_id=rule_id, use_mock=self._use_mock, provider=settings.LLM_PROVIDER)

        # Check cache first
        cache_key = self._get_cache_key(
            rule_id,
            self._hash_content(file_content) if file_content else "no_content"
        )

        if cache_key in self._cache:
            logger.debug("Cache hit for fix", rule_id=rule_id)
            return self._cache[cache_key]

        # ALWAYS attempt AI first (even if mock), fallback to static
        result = None
        if not self._use_mock:
            try:
                logger.info("Calling AI fix generator", rule_id=rule_id, provider=settings.LLM_PROVIDER)
                result = await self._generate_ai_fix(finding, file_content)
                logger.info("AI fix generated successfully", rule_id=rule_id, confidence=result.get("confidence"))
            except Exception as e:
                logger.warning("AI fix generation failed, using mock", rule_id=rule_id, error=str(e))

        # Use mock if AI failed or not configured
        if result is None:
            logger.info("Using mock fix generator", rule_id=rule_id)
            result = self._generate_mock_fix(finding)

        # Cache result
        self._cache[cache_key] = result
        return result

    async def _generate_ai_fix(self, finding: dict[str, Any], file_content: str) -> dict[str, Any]:
        """Generate fix using LLM."""
        if not self.llm_provider:
            self.llm_provider = get_llm_provider()

        prompt = self._build_fix_prompt(finding, file_content)
        response = await self.llm_provider.generate(prompt)

        return self._parse_ai_response(response, finding)

    def _build_fix_prompt(self, finding: dict[str, Any], file_content: str) -> str:
        """Build prompt for AI fix generation."""
        rule_id = finding.get("rule_id", "UNKNOWN")
        title = finding.get("rule_name", "Unknown Issue")
        severity = finding.get("severity", "MEDIUM")
        file_type = finding.get("file_type", "unknown")
        description = finding.get("description", "")

        return f"""You are an expert DevOps engineer. Generate a production-ready fix for this issue.

ISSUE DETAILS:
- Rule ID: {rule_id}
- Title: {title}
- Severity: {severity}
- File Type: {file_type}
- Description: {description}

{'FILE CONTENT:' if file_content else ''}
{file_content if file_content else 'N/A'}

Generate a response in this EXACT JSON format:
{{
  "summary": "Simple 1-2 sentence explanation of the issue",
  "risk": "Why this is dangerous (security, reliability, or performance impact)",
  "fix_code": "Production-ready fix code (use proper escaping for newlines)",
  "full_example": "Complete corrected file snippet showing the fix in context",
  "impact": "Security/reliability improvement from applying this fix",
  "confidence": 0.85
}}

REQUIREMENTS:
1. Fix code must be production-ready (not pseudocode)
2. Include proper error handling where applicable
3. Follow security best practices
4. Use specific versions (not 'latest')
5. Include comments explaining key changes

Respond ONLY with the JSON, no other text."""

    def _parse_ai_response(self, response: str, finding: dict[str, Any]) -> dict[str, Any]:
        """Parse AI response into structured format."""
        import re

        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response)

            return {
                "summary": result.get("summary", finding.get("description", "")),
                "risk": result.get("risk", ""),
                "fix_code": result.get("fix_code", ""),
                "full_example": result.get("full_example", ""),
                "impact": result.get("impact", ""),
                "confidence": float(result.get("confidence", 0.8)),
            }
        except Exception as e:
            logger.warning("Failed to parse AI response", error=str(e))
            return self._generate_mock_fix(finding)

    def _generate_mock_fix(self, finding: dict[str, Any]) -> dict[str, Any]:
        """Generate mock fix (fallback when AI unavailable)."""
        rule_id = finding.get("rule_id", "")

        # Check static FIX_EXAMPLES first - THIS IS THE GUARANTEED FALLBACK
        if rule_id in FIX_EXAMPLES:
            logger.debug(f"Using static fix example for {rule_id}")
            return {
                "summary": finding.get("description", ""),
                **FIX_EXAMPLES[rule_id],
                "confidence": 0.95,
            }

        # Default mock fix (last resort)
        logger.debug(f"No static fix for {rule_id}, using default mock")
        return {
            "summary": finding.get("description", "Issue detected in configuration."),
            "risk": "This issue may impact security, reliability, or performance.",
            "fix_code": "# Apply recommended fix based on best practices\n# See documentation for specific guidance",
            "full_example": "# Example configuration with fix applied\n# Replace with your specific configuration",
            "impact": "Improves security posture and follows industry best practices.",
            "confidence": 0.75,
        }


class FindingsEnricher:
    """Production-grade findings enricher with AI-first approach and guaranteed fallback."""

    def __init__(self):
        self._fix_examples = FIX_EXAMPLES
        self._ai_service: AIFixEnrichmentService | None = None

    def _get_ai_service(self) -> AIFixEnrichmentService:
        """Get or create AI enrichment service."""
        if self._ai_service is None:
            self._ai_service = AIFixEnrichmentService()
        return self._ai_service

    def enrich_finding(self, finding: RuleFinding) -> RuleFinding:
        """
        Enrich a single finding with static data (GUARANTEED FALLBACK).
        
        This method ALWAYS works and provides baseline enrichment.
        """
        # Look up fix example by rule_id
        fix_data = self._fix_examples.get(finding.rule_id, {})

        # Apply enrichment (only if not already set)
        if not finding.summary and "summary" in fix_data:
            finding.summary = fix_data["summary"]
        if not finding.risk and "risk" in fix_data:
            finding.risk = fix_data["risk"]
        if not finding.impact and "impact" in fix_data:
            finding.impact = fix_data["impact"]
        if not finding.impact_analysis and "impact" in fix_data:
            finding.impact_analysis = fix_data["impact"]
        if not finding.fix_code and "fix_code" in fix_data:
            finding.fix_code = fix_data["fix_code"]
        if not finding.fix_example and "fix_example" in fix_data:
            finding.fix_example = fix_data["fix_example"]
        if not finding.full_example and "full_example" in fix_data:
            finding.full_example = fix_data["full_example"]
        if not finding.best_practices and "best_practices" in fix_data:
            finding.best_practices = fix_data["best_practices"]
        if not finding.confidence and "confidence" in fix_data:
            finding.confidence = fix_data["confidence"]

        # Add documentation URL
        if not finding.documentation_url:
            finding.documentation_url = get_documentation_url(finding.rule_id)

        # Mark as static if no AI enrichment
        if not hasattr(finding, 'ai_generated') or not finding.ai_generated:
            finding.ai_generated = False

        return finding

    async def enrich_finding_async(self, finding: RuleFinding, file_content: str = "") -> RuleFinding:
        """
        Enrich a finding with AI-first approach (ALWAYS attempts AI, guaranteed fallback).
        
        Flow:
        1. Attempt AI enrichment (with mock fallback)
        2. Apply static enrichment for any missing fields
        """
        try:
            ai_service = self._get_ai_service()
            ai_fix = await ai_service.generate_fix({
                "rule_id": finding.rule_id,
                "rule_name": finding.rule_name,
                "severity": str(finding.severity.value if hasattr(finding.severity, 'value') else finding.severity).lower(),
                "file_type": finding.file_path.split('.')[-1] if finding.file_path and '.' in finding.file_path else "unknown",
                "description": finding.description,
            }, file_content)

            # Apply AI enrichment (merge with existing data)
            if ai_fix:
                if ai_fix.get("summary") and (not finding.summary or finding.summary == finding.description):
                    finding.summary = ai_fix.get("summary", finding.summary)
                if ai_fix.get("risk") and not finding.risk:
                    finding.risk = ai_fix.get("risk", finding.risk)
                if ai_fix.get("fix_code") and not finding.fix_code:
                    finding.fix_code = ai_fix.get("fix_code", finding.fix_code)
                if ai_fix.get("fix_example") and not finding.fix_example:
                    finding.fix_example = ai_fix.get("fix_example", finding.fix_example)
                if ai_fix.get("full_example") and not finding.full_example:
                    finding.full_example = ai_fix.get("full_example", finding.full_example)
                if ai_fix.get("impact") and not finding.impact:
                    finding.impact = ai_fix.get("impact", finding.impact)
                if ai_fix.get("impact") and not finding.impact_analysis:
                    finding.impact_analysis = ai_fix.get("impact", finding.impact_analysis)
                if ai_fix.get("confidence", 0) > (finding.confidence or 0):
                    finding.confidence = ai_fix.get("confidence", finding.confidence)

                # Mark as AI-generated
                finding.ai_generated = True

                logger.info(
                    "AI enrichment applied",
                    rule_id=finding.rule_id,
                    confidence=finding.confidence,
                    ai_generated=finding.ai_generated,
                )

        except Exception as e:
            logger.warning(
                "AI enrichment failed, using static fallback",
                rule_id=finding.rule_id,
                error=str(e),
            )

        # Apply static enrichment for any missing fields (GUARANTEED FALLBACK)
        return self.enrich_finding(finding)

    async def enrich_findings_async(
        self,
        findings: list[RuleFinding],
        file_contents: dict[str, str] = None,
    ) -> list[RuleFinding]:
        """Enrich multiple findings with AI-first approach."""
        file_contents = file_contents or {}
        enriched_findings = []

        for finding in findings:
            file_content = file_contents.get(finding.file_path, "")
            enriched = await self.enrich_finding_async(finding, file_content)
            enriched_findings.append(enriched)

        logger.info(
            "Findings enrichment complete",
            total_findings=len(enriched_findings),
            ai_enriched=sum(1 for f in enriched_findings if getattr(f, 'ai_generated', False)),
            static_enriched=sum(1 for f in enriched_findings if not getattr(f, 'ai_generated', False)),
        )

        return enriched_findings


# Convenience functions for synchronous enrichment (used in sync scan service)
def enrich_findings(findings: list[RuleFinding]) -> list[RuleFinding]:
    """Synchronous enrichment using static fallback only."""
    enricher = FindingsEnricher()
    return [enricher.enrich_finding(f) for f in findings]


async def enrich_findings_with_ai(
    findings: list[RuleFinding],
    file_contents: dict[str, str] = None,
) -> list[RuleFinding]:
    """Async enrichment with AI-first approach."""
    enricher = FindingsEnricher()
    return await enricher.enrich_findings_async(findings, file_contents)
