# DevArchAI - Deployment & Infrastructure Guide

> **Version:** 1.0.0  
> **Status:** Production-Ready  
> **Last Updated:** April 14, 2026

---

## 1. Overview

This document provides complete deployment instructions for DevArchAI, covering local development, staging, and production environments using Docker, Kubernetes, and CI/CD pipelines.

**Environments:**
- **Development:** Local machine with Docker Compose
- **Staging:** Kubernetes cluster (staging namespace)
- **Production:** Kubernetes cluster (production namespace)

---

## 2. Local Development Setup

### 2.1 Prerequisites

```bash
# Required software
- Docker 24.0+
- Docker Compose 2.20+
- Python 3.11+
- Node.js 18+
- PostgreSQL 15 (optional, can use Docker)
- Redis 7 (optional, can use Docker)

# Recommended tools
- VS Code with Python, ESLint extensions
- Postman or Insomnia (API testing)
- pgAdmin or DBeaver (database management)
```

### 2.2 Quick Start

```bash
# Clone repository
git clone https://github.com/devarchai/platform.git
cd platform

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### 2.3 Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/devarchai
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
      - GITHUB_TOKEN=${GITHUB_TOKEN:-}
      - SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-in-production}
    volumes:
      - ./backend/app:/app/app
      - temp_data:/tmp/devarchai
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=devarchai
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Celery Worker (optional, for async tasks)
  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.workers.celery_config worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/devarchai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  # Celery Beat (periodic tasks)
  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.workers.celery_config beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/devarchai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
  redis_data:
  temp_data:
```

### 2.4 Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.5 Frontend Dockerfile

```dockerfile
# frontend/Dockerfile
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:80 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

---

## 3. Environment Configuration

### 3.1 Environment Variables

```bash
# .env.example

# ===========================================
# Application Settings
# ===========================================
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
FRONTEND_URL=http://localhost:3000

# ===========================================
# Database
# ===========================================
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/devarchai
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# ===========================================
# Redis
# ===========================================
REDIS_URL=redis://localhost:6379/0

# ===========================================
# Celery
# ===========================================
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ===========================================
# LLM Configuration
# ===========================================
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
MISTRAL_API_KEY=your-mistral-api-key
LLM_MODEL=gemini-2.0-flash
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.3

# ===========================================
# GitHub Integration
# ===========================================
GITHUB_TOKEN=your-github-token
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://localhost:3000/auth/github/callback

# ===========================================
# Security
# ===========================================
SECRET_KEY=your-secret-key-min-32-characters-long
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ===========================================
# AWS S3
# ===========================================
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET_NAME=devarchai-reports

# ===========================================
# Payment Providers
# ===========================================
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
RAZORPAY_KEY_ID=rzp_test_xxx
RAZORPAY_KEY_SECRET=your-razorpay-secret

# ===========================================
# Logging
# ===========================================
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 4. Kubernetes Deployment

### 4.1 Namespace Setup

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: devarchai-staging
  labels:
    environment: staging

---
apiVersion: v1
kind: Namespace
metadata:
  name: devarchai-production
  labels:
    environment: production
```

### 4.2 Secrets Management

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: devarchai-secrets
  namespace: devarchai-production
type: Opaque
stringData:
  DATABASE_URL: "postgresql+asyncpg://user:password@postgres:5432/devarchai"
  REDIS_URL: "redis://redis:6379/0"
  SECRET_KEY: "your-production-secret-key"
  GEMINI_API_KEY: "your-gemini-api-key"
  GITHUB_TOKEN: "your-github-token"
  STRIPE_SECRET_KEY: "sk_live_xxx"
  AWS_ACCESS_KEY_ID: "your-aws-key"
  AWS_SECRET_ACCESS_KEY: "your-aws-secret"
```

**Apply secrets:**
```bash
kubectl apply -f k8s/secrets.yaml
```

### 4.3 Backend Deployment

```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devarchai-backend
  namespace: devarchai-production
  labels:
    app: devarchai-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: devarchai-backend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: devarchai-backend
    spec:
      serviceAccountName: devarchai-backend
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
      
      containers:
      - name: backend
        image: devarchai/backend:latest
        ports:
        - containerPort: 8000
          protocol: TCP
        
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DEBUG
          value: "false"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: devarchai-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: devarchai-secrets
              key: REDIS_URL
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: devarchai-secrets
              key: SECRET_KEY
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: devarchai-secrets
              key: GEMINI_API_KEY
        
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /api/v1/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL
        
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      
      volumes:
      - name: tmp
        emptyDir:
          medium: Memory
          sizeLimit: 1Gi
      
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - devarchai-backend
              topologyKey: kubernetes.io/hostname
```

### 4.4 Frontend Deployment

```yaml
# k8s/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devarchai-frontend
  namespace: devarchai-production
  labels:
    app: devarchai-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: devarchai-frontend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: devarchai-frontend
    spec:
      containers:
      - name: frontend
        image: devarchai/frontend:latest
        ports:
        - containerPort: 80
          protocol: TCP
        
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 10
        
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 4.5 Services

```yaml
# k8s/services.yaml
apiVersion: v1
kind: Service
metadata:
  name: devarchai-backend
  namespace: devarchai-production
spec:
  selector:
    app: devarchai-backend
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: ClusterIP

---
apiVersion: v1
kind: Service
metadata:
  name: devarchai-frontend
  namespace: devarchai-production
spec:
  selector:
    app: devarchai-frontend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
```

### 4.6 Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: devarchai-ingress
  namespace: devarchai-production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
spec:
  tls:
  - hosts:
    - app.devarchai.com
    - api.devarchai.com
    secretName: devarchai-tls
  rules:
  - host: api.devarchai.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: devarchai-backend
            port:
              number: 8000
  - host: app.devarchai.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: devarchai-frontend
            port:
              number: 80
```

### 4.7 Horizontal Pod Autoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: devarchai-backend-hpa
  namespace: devarchai-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: devarchai-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 5. Database Migrations

### 5.1 Alembic Configuration

```python
# alembic.ini
[alembic]
script_location = backend/app/db/migrations
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/devarchai

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 5.2 Migration Workflow

```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "add_new_table"

# Review migration file
# Edit backend/app/db/migrations/versions/xxx_add_new_table.py

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check current version
alembic current

# View migration history
alembic history
```

### 5.3 Production Migration

```bash
# Run migrations in Kubernetes
kubectl exec -it deployment/devarchai-backend -n devarchai-production -- \
  alembic upgrade head

# Verify migration
kubectl exec -it deployment/devarchai-backend -n devarchai-production -- \
  alembic current
```

---

## 6. CI/CD Pipeline

### 6.1 GitHub Actions Workflow

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME_BACKEND: ${{ github.repository }}/backend
  IMAGE_NAME_FRONTEND: ${{ github.repository }}/frontend

jobs:
  # ===========================================
  # Test Job
  # ===========================================
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: devarchai_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Cache Python dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('backend/requirements.txt') }}
    
    - name: Install backend dependencies
      run: |
        cd backend
        pip install -r requirements.txt
    
    - name: Run backend tests
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/devarchai_test
        REDIS_URL: redis://localhost:6379/0
      run: |
        cd backend
        pytest --cov=app --cov-report=xml --cov-report=html
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json
    
    - name: Install frontend dependencies
      run: |
        cd frontend
        npm ci
    
    - name: Run frontend tests
      run: |
        cd frontend
        npm test -- --coverage
    
    - name: Run security audit
      run: |
        cd backend
        pip-audit
        safety check
        
        cd ../frontend
        npm audit --audit-level=high

  # ===========================================
  # Build and Push Docker Images
  # ===========================================
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    
    permissions:
      contents: read
      packages: write
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME_BACKEND }}
    
    - name: Build and push backend
      uses: docker/build-push-action@v4
      with:
        context: ./backend
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
    
    - name: Extract frontend metadata
      id: frontend-meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME_FRONTEND }}
    
    - name: Build and push frontend
      uses: docker/build-push-action@v4
      with:
        context: ./frontend
        push: true
        tags: ${{ steps.frontend-meta.outputs.tags }}
        labels: ${{ steps.frontend-meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  # ===========================================
  # Deploy to Staging
  # ===========================================
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.STAGING_KUBECONFIG }}
    
    - name: Deploy to staging
      run: |
        kubectl set image deployment/devarchai-backend \
          backend=${{ env.REGISTRY }}/${{ env.IMAGE_NAME_BACKEND }}:${{ github.sha }} \
          -n devarchai-staging
        
        kubectl set image deployment/devarchai-frontend \
          frontend=${{ env.REGISTRY }}/${{ env.IMAGE_NAME_FRONTEND }}:${{ github.sha }} \
          -n devarchai-staging
        
        kubectl rollout status deployment/devarchai-backend -n devarchai-staging --timeout=300s
        kubectl rollout status deployment/devarchai-frontend -n devarchai-staging --timeout=300s

  # ===========================================
  # Deploy to Production
  # ===========================================
  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.PRODUCTION_KUBECONFIG }}
    
    - name: Run database migrations
      run: |
        kubectl exec -it deployment/devarchai-backend -n devarchai-production -- \
          alembic upgrade head
    
    - name: Deploy to production
      run: |
        kubectl set image deployment/devarchai-backend \
          backend=${{ env.REGISTRY }}/${{ env.IMAGE_NAME_BACKEND }}:${{ github.sha }} \
          -n devarchai-production
        
        kubectl set image deployment/devarchai-frontend \
          frontend=${{ env.REGISTRY }}/${{ env.IMAGE_NAME_FRONTEND }}:${{ github.sha }} \
          -n devarchai-production
        
        kubectl rollout status deployment/devarchai-backend -n devarchai-production --timeout=600s
        kubectl rollout status deployment/devarchai-frontend -n devarchai-production --timeout=600s
    
    - name: Verify deployment
      run: |
        sleep 30
        curl -f https://api.devarchai.com/health || exit 1
        curl -f https://app.devarchai.com || exit 1
```

---

## 7. Monitoring & Observability

### 7.1 Prometheus Metrics

```python
# backend/app/services/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Scan metrics
SCAN_TOTAL = Counter(
    'scans_total',
    'Total scans initiated'
)

SCAN_COMPLETED = Counter(
    'scans_completed',
    'Total scans completed successfully'
)

SCAN_FAILED = Counter(
    'scans_failed',
    'Total scans failed'
)

# AI metrics
AI_REQUESTS = Counter(
    'ai_requests_total',
    'Total AI API requests',
    ['provider', 'model']
)

AI_COST = Counter(
    'ai_cost_usd_total',
    'Total AI API cost in USD',
    ['provider']
)

# Active scans gauge
ACTIVE_SCANS = Gauge(
    'scans_active',
    'Currently active scans'
)
```

### 7.2 Grafana Dashboard

```json
{
  "dashboard": {
    "title": "DevArchAI Production Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Active Scans",
        "type": "singlestat",
        "targets": [
          {
            "expr": "scans_active"
          }
        ]
      },
      {
        "title": "Scan Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(scans_completed[5m]) / rate(scans_total[5m])",
            "legendFormat": "Success Rate"
          }
        ]
      }
    ]
  }
}
```

### 7.3 Alerting Rules

```yaml
# k8s/alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: devarchai-alerts
  namespace: monitoring
spec:
  groups:
  - name: devarchai.rules
    rules:
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value }}% over the last 5 minutes"
    
    - alert: HighLatency
      expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "High latency detected"
        description: "95th percentile latency is {{ $value }}s"
    
    - alert: PodCrashLooping
      expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
      for: 15m
      labels:
        severity: critical
      annotations:
        summary: "Pod crash looping"
        description: "Pod {{ $labels.pod }} is restarting frequently"
    
    - alert: LowDiskSpace
      expr: kubelet_volume_stats_available_bytes / kubelet_volume_stats_capacity_bytes < 0.1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Low disk space"
        description: "Disk space is below 10% on {{ $labels.persistentvolumeclaim }}"
```

---

## 8. Backup & Disaster Recovery

### 8.1 Database Backup

```bash
#!/bin/bash
# backup-db.sh

BACKUP_DIR="/backups/postgresql"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACK_DIR/devarchai_$TIMESTAMP.dump"

# Create backup
pg_dump -U postgres -d devarchai -F c -f "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

# Upload to S3
aws s3 cp "$BACKUP_FILE.gz" s3://devarchai-backups/database/

# Delete backups older than 30 days
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

**Cron Job:**
```cron
# Run backup daily at 2 AM
0 2 * * * /scripts/backup-db.sh >> /var/log/backup.log 2>&1
```

### 8.2 Disaster Recovery Plan

**RTO (Recovery Time Objective):** 4 hours  
**RPO (Recovery Point Objective):** 1 hour

**Recovery Steps:**
```
1. Detect outage → Automated alerts from Prometheus
2. Assess damage → Check logs, metrics, user reports
3. Activate DR plan → Notify team, update status page
4. Restore from backup:
   a. Provision new database instance
   b. Restore latest backup
   c. Apply WAL logs up to failure point
   d. Verify data integrity
5. Update DNS → Point to new database
6. Restart services → Deploy fresh instances
7. Monitor → Watch for errors, data inconsistencies
8. Post-mortem → Document incident, update runbooks
```

---

## 9. Scaling Strategy

### 9.1 Horizontal Scaling

```
Backend API:
  - Current: 3 replicas
  - Max: 10 replicas
  - Trigger: CPU > 70%, Memory > 80%
  - Cooldown: 5 minutes

Celery Workers:
  - Current: 2 workers
  - Max: 20 workers
  - Trigger: Queue depth > 100 tasks
  - Cooldown: 3 minutes

Database:
  - Read replicas: 2 (auto-scaled to 5)
  - Trigger: Read latency > 100ms
  - Connection pooling: PgBouncer
```

### 9.2 Database Scaling

```
Vertical Scaling:
  - Current: 4 CPU, 16GB RAM
  - Next tier: 8 CPU, 32GB RAM
  - Trigger: CPU > 80% sustained

Read Replicas:
  - Purpose: Offload read queries
  - Sync: Streaming replication
  - Failover: Automatic (Patroni)

Partitioning:
  - scans table: Monthly partitions
  - findings table: Monthly partitions
  - audit_logs table: Quarterly partitions
```

### 9.3 Caching Strategy

```
Redis Cache:
  - Session storage: 1GB
  - API response cache: 2GB
  - Rate limiting counters: 512MB
  - Scan progress cache: 1GB

Cache Invalidation:
  - TTL-based: 5 minutes for API responses
  - Event-based: On scan completion, findings update
  - Manual: Admin can clear specific cache keys

Cache Hit Rate Target: > 80%
```

---

## 10. Troubleshooting

### 10.1 Common Issues

**Issue: Pod won't start**
```bash
# Check pod status
kubectl get pods -n devarchai-production

# Check pod events
kubectl describe pod <pod-name> -n devarchai-production

# Check logs
kubectl logs <pod-name> -n devarchai-production

# Common causes:
# - Image pull error: Check image tag and registry credentials
# - CrashLoopBackOff: Check application logs
# - Pending: Insufficient resources, check node capacity
```

**Issue: Database connection failed**
```bash
# Check database status
kubectl get pods -n devarchai-production | grep postgres

# Test connection from backend pod
kubectl exec -it <backend-pod> -n devarchai-production -- \
  python -c "from app.db.session import engine; print(engine.connect())"

# Check database logs
kubectl logs <postgres-pod> -n devarchai-production

# Common causes:
# - Wrong credentials: Check secrets
# - Database not ready: Wait for initialization
# - Connection pool exhausted: Increase pool size
```

**Issue: High latency**
```bash
# Check metrics
kubectl top pods -n devarchai-production

# Check slow queries
kubectl exec -it <postgres-pod> -n devarchai-production -- \
  psql -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check network
kubectl exec -it <backend-pod> -n devarchai-production -- \
  curl -w "@curl-format.txt" -o /dev/null -s https://api.devarchai.com/health

# Common causes:
# - Database slow queries: Add indexes
# - Memory pressure: Increase limits
# - Network issues: Check service mesh
```

### 10.2 Debug Commands

```bash
# Get all resources
kubectl get all -n devarchai-production

# Check ingress
kubectl get ingress -n devarchai-production

# Check secrets
kubectl get secrets -n devarchai-production

# Check persistent volumes
kubectl get pv,pvc -n devarchai-production

# Check HPA
kubectl get hpa -n devarchai-production

# Check node resources
kubectl top nodes

# Port forward to backend
kubectl port-forward svc/devarchai-backend 8000:8000 -n devarchai-production

# Execute into pod
kubectl exec -it <pod-name> -n devarchai-production -- /bin/bash
```

---

*This document is maintained by the DevArchAI DevOps team. Last reviewed: April 14, 2026.*
