# DevArchAI - Production SaaS Architecture Redesign

**Document Version:** 1.0  
**Date:** March 6, 2026  
**Author:** Senior Software Architect

---

## Executive Summary

This document provides a comprehensive architecture redesign for DevArchAI, transforming it from a prototype into a production-grade, multi-tenant SaaS platform. The current codebase demonstrates solid foundational patterns but requires significant restructuring to support enterprise-scale operations, proper tenant isolation, billing integration, and horizontal scalability.

---

## 1. Current Architecture Analysis

### 1.1 Technology Stack

| Layer | Technology | Version | Assessment |
|-------|------------|---------|------------|
| **Backend Framework** | FastAPI | 0.109.0 | ✅ Good choice |
| **Frontend Framework** | React | 18.2.0 | ✅ Good choice |
| **Database** | PostgreSQL | 15 | ✅ Good choice |
| **Cache** | Redis | 7 | ✅ Good choice |
| **ORM** | SQLAlchemy | 2.0.25 | ✅ Good choice |
| **Task Queue** | Celery | 5.3.6 | ⚠️ Not fully utilized |
| **LLM Integration** | LangChain | 0.1.4 | ⚠️ Basic implementation |
| **State Management** | Zustand | 4.5.0 | ✅ Good choice |
| **Data Fetching** | React Query | 5.17.9 | ✅ Good choice |
| **UI Library** | shadcn/ui + Radix | - | ✅ Good choice |

### 1.2 Current Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         DevArchAI Current                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────────────────────────────┐    │
│  │   React     │───▶│         FastAPI Backend             │    │
│  │  Frontend   │    │  ┌───────────────────────────────┐  │    │
│  │             │    │  │  API Routes (v1)              │  │    │
│  └─────────────┘    │  │  - scans/                     │  │    │
│                     │  │  - reports/                   │  │    │
│  ┌─────────────┐    │  │  - repositories/              │  │    │
│  │   GitHub    │───▶│  │  - auth/                      │  │    │
│  │   Repo URL  │    │  └───────────────────────────────┘  │    │
│  └─────────────┘    │                                     │    │
│                     │  ┌───────────────────────────────┐  │    │
│                     │  │  Services Layer               │  │    │
│                     │  │  - analysis.py                │  │    │
│                     │  │  - scan_service.py            │  │    │
│                     │  │  - github.py                  │  │    │
│                     │  └───────────────────────────────┘  │    │
│                     │                                     │    │
│                     │  ┌───────────────────────────────┐  │    │
│                     │  │  Parsers + Rules              │  │    │
│                     │  └───────────────────────────────┘  │    │
│                     │                                     │    │
│                     │  ┌───────────────────────────────┐  │    │
│                     │  │  AI Engine                    │  │    │
│                     │  └───────────────────────────────┘  │    │
│                     └─────────────────────────────────────┘    │
│                               │                                 │
│              ┌────────────────┼────────────────┐               │
│              ▼                ▼                ▼               │
│     ┌────────────────┐ ┌────────────┐ ┌──────────────┐        │
│     │   PostgreSQL   │ │   Redis    │ │  Temp Files  │        │
│     │   (Local/RDS)  │ │  (Cache)   │ │  /tmp        │        │
│     └────────────────┘ └────────────┘ └──────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Current Data Model

```
User (1) ──────< (N) Repository
   │                    │
   │                    │ (1)
   │                    ▼
   │              (N) Scan
   │                    │
   │                    │ (1)
   │                    ▼
   │              (N) Finding
   │                    │
   │                    │ (1)
   ▼                    ▼
(N) Scan          (0..1) Report
```

### 1.4 Current API Structure

```
/api/v1/
├── /health           - Health checks
├── /auth/*           - Authentication (basic JWT)
├── /scans/*          - Scan CRUD + analysis trigger
├── /repositories/*   - Repository management
├── /reports/*        - Report retrieval
└── /analyze          - Legacy analysis endpoint
```

---

## 2. Problems in Current Codebase

### 2.1 Critical Architecture Issues

| Priority | Issue | Impact | Severity |
|----------|-------|--------|----------|
| **P0** | No multi-tenancy support | Cannot support SaaS billing | 🔴 Critical |
| **P0** | Background workers use in-memory dict | No horizontal scaling, data loss on restart | 🔴 Critical |
| **P0** | No proper queue system integration | Celery installed but not used | 🔴 Critical |
| **P1** | Missing tenant/organization model | Cannot implement team features | 🟠 High |
| **P1** | No subscription/billing layer | Cannot monetize | 🟠 High |
| **P1** | Scan worker stores state in memory | Race conditions, no fault tolerance | 🟠 High |
| **P2** | No API versioning strategy | Breaking changes will break clients | 🟡 Medium |
| **P2** | Mixed synchronous/asynchronous patterns | Potential deadlocks | 🟡 Medium |
| **P2** | No rate limiting implementation | DoS vulnerability | 🟡 Medium |
| **P2** | Hardcoded anonymous user | Security concern | 🟡 Medium |
| **P3** | No audit logging | Compliance issues | 🟢 Low |
| **P3** | No feature flags | Cannot do gradual rollouts | 🟢 Low |
| **P3** | Frontend has placeholder pages | Incomplete UX | 🟢 Low |

### 2.2 Code Quality Issues

#### Backend

```python
# ❌ PROBLEM: In-memory worker pool (workers/scan_worker.py)
_worker_pool: dict[int, ScanWorker] = {}  # Lost on restart!

# ❌ PROBLEM: No proper Celery integration
# Celery is in requirements.txt but never configured or used

# ❌ PROBLEM: Mixed sync/async in analysis service
async def analyze_repository(self, repo_path: str, ...):
    # Async method but calls sync operations
    files_to_analyze = self._scan_repository(repo_path)  # Sync
    parsed_files = self._parse_files(files_to_analyze)    # Sync
```

#### Frontend

```typescript
// ❌ PROBLEM: No error boundary or proper error handling
export const api = axios.create({...})
// No interceptors for auth token refresh
// No global error handling

// ❌ PROBLEM: Missing pages referenced in App.tsx
<Route path="/reports" element={<ReportsPlaceholder />} />
<Route path="/settings" element={<SettingsPlaceholder />} />
// These should be fully implemented
```

### 2.3 Security Concerns

1. **No rate limiting** - API vulnerable to abuse
2. **Weak secret key default** - `SECRET_KEY` defaults to `change-me-in-production`
3. **No input sanitization** - Repository URLs not validated
4. **No CSRF protection** - Missing for state-changing operations
5. **No request size limits** - Potential DoS via large payloads
6. **Anonymous user access** - No proper guest vs authenticated separation

### 2.4 Scalability Blockers

1. **Single-node worker pool** - Cannot distribute load
2. **No connection pooling configuration** - Database will bottleneck
3. **No caching strategy** - Every request hits database
4. **No CDN integration** - Static assets served from app server
5. **No horizontal pod autoscaling config** - Cannot auto-scale

---

## 3. Recommended Product Architecture

### 3.1 Target Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DevArchAI SaaS Platform                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        CloudFlare / AWS CloudFront                   │    │
│  │                        (CDN + WAF + DDoS Protection)                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Application Load Balancer                       │    │
│  │                    (AWS ALB / NGINX Ingress)                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│         ┌────────────────────────────┼────────────────────────────┐         │
│         │                            │                            │         │
│         ▼                            ▼                            ▼         │
│  ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐│
│  │  Frontend       │         │  API Gateway    │         │  WebSocket      ││
│  │  Service        │         │  Service        │         │  Service        ││
│  │  (React SPA)    │         │  (FastAPI)      │         │  (Real-time)    ││
│  │  :3000          │         │  :8000          │         │  :8001          ││
│  └─────────────────┘         └─────────────────┘         └─────────────────┘│
│         │                            │                            │         │
│         │                            │                            │         │
│         └────────────────────────────┼────────────────────────────┘         │
│                                      │                                       │
│         ┌────────────────────────────┼────────────────────────────┐         │
│         │                            │                            │         │
│         ▼                            ▼                            ▼         │
│  ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐│
│  │  Task Queue     │         │  Cache Layer    │         │  Search         ││
│  │  (Celery +      │         │  (Redis         │         │  (Elasticsearch ││
│  │   RabbitMQ)     │         │   Cluster)      │         │   / Meilisearch)││
│  └─────────────────┘         └─────────────────┘         └─────────────────┘│
│         │                            │                                       │
│         ▼                            │                                       │
│  ┌─────────────────┐                 │                                       │
│  │  Worker Pool    │                 │                                       │
│  │  (Auto-scaling) │                 │                                       │
│  │  - Scan Workers │                 │                                       │
│  │  - Report Gen   │                 │                                       │
│  │  - Email        │                 │                                       │
│  │  - Webhooks     │                 │                                       │
│  └─────────────────┘                 │                                       │
│         │                            │                                       │
│         └────────────────────────────┼────────────────────────────┐         │
│                                      │                            │         │
│                                      ▼                            ▼         │
│                          ┌─────────────────┐            ┌─────────────────┐ │
│                          │  Primary DB     │            │  Object Storage │ │
│                          │  (PostgreSQL    │            │  (S3 / GCS)     │ │
│                          │   with PgBouncer)│           │  - Reports      │ │
│                          │  - Row Level    │            │  - Temp Files   │ │
│                          │    Security     │            │  - Assets       │ │
│                          └─────────────────┘            └─────────────────┘ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Observability Stack                               │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │    │
│  │  │ Metrics  │  │ Logging  │  │ Tracing  │  │ Alerting │            │    │
│  │  │Prometheus│  │   ELK    │  │ Jaeger   │  │PagerDuty │            │    │
│  │  │Grafana   │  │CloudWatch│  │          │  │Slack     │            │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    External Integrations                             │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │    │
│  │  │  Stripe  │  │  Auth0/  │  │  SendGrid│  │  GitHub  │            │    │
│  │  │  Billing │  │  Cognito │  │  Email   │  │  OAuth   │            │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Multi-Tenancy Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Tenant Data Model                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Organization (Tenant)                                          │
│  ├── id, name, slug, plan, billing_info                        │
│  ├── settings, features, quotas                                │
│  │                                                              │
│  ├── (1) ────< (N) User (Members)                              │
│  │           └── role: owner, admin, member, viewer            │
│  │                                                              │
│  ├── (1) ────< (N) Project                                      │
│  │           └── Repository grouping                            │
│  │                                                              │
│  ├── (1) ────< (N) Repository                                   │
│  │           └── GitHub/GitLab/Bitbucket repos                 │
│  │                                                              │
│  └── (1) ────< (N) Scan                                         │
│              └── Analysis jobs with findings                   │
│                                                                  │
│  ─────────────────────────────────────────────────────────      │
│  Row Level Security: All queries filtered by organization_id   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 SaaS Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SaaS User Journey                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. SIGN UP                                                              │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐                       │
│     │  Email/  │───▶│  Verify  │───▶│  Create  │                       │
│     │  OAuth   │    │  Email   │    │  Org     │                       │
│     └──────────┘    └──────────┘    └──────────┘                       │
│                                                                          │
│  2. ONBOARDING                                                           │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐                       │
│     │  Select  │───▶│  Connect │───▶│  First   │                       │
│     │  Plan    │    │  GitHub  │    │  Project │                       │
│     └──────────┘    └──────────┘    └──────────┘                       │
│                                                                          │
│  3. CORE WORKFLOW                                                        │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐                       │
│     │  Add     │───▶│  Trigger │───▶│  View    │                       │
│     │  Repo    │    │  Scan    │    │  Results │                       │
│     └──────────┘    └──────────┘    └──────────┘                       │
│           │                                      │                      │
│           │              ┌───────────────────────┘                      │
│           │              │                                              │
│           ▼              ▼                                              │
│     ┌──────────────────────────┐                                       │
│     │   Background Processing  │                                       │
│     │   ┌──────────────────┐   │                                       │
│     │   │ 1. Clone Repo    │   │                                       │
│     │   │ 2. Parse Files   │   │                                       │
│     │   │ 3. Run Rules     │   │                                       │
│     │   │ 4. AI Analysis   │   │                                       │
│     │   │ 5. Generate Score│   │                                       │
│     │   │ 6. Store Report  │   │                                       │
│     │   └──────────────────┘   │                                       │
│     └──────────────────────────┘                                       │
│                                                                          │
│  4. RETENTION                                                            │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐                       │
│     │Scheduled │───▶│  Trend   │───▶│  Alert   │                       │
│     │  Scans   │    │ Analysis │    │ on Issues│                       │
│     └──────────┘    └──────────┘    └──────────┘                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.4 API Gateway Architecture

```
/api
├── /v1                          # Current API version
│   ├── /auth                    # Authentication
│   │   ├── POST /register       # User registration
│   │   ├── POST /login          # User login
│   │   ├── POST /logout         # User logout
│   │   ├── POST /refresh        # Token refresh
│   │   ├── POST /forgot-password
│   │   └── POST /reset-password
│   │
│   ├── /organization            # Tenant management
│   │   ├── GET  /               # Get current org
│   │   ├── PUT  /               # Update org
│   │   ├── GET  /members        # List members
│   │   ├── POST /members        # Invite member
│   │   ├── PUT  /members/:id    # Update role
│   │   └── DELETE /members/:id  # Remove member
│   │
│   ├── /projects                # Project grouping
│   │   ├── GET    /             # List projects
│   │   ├── POST   /             # Create project
│   │   ├── GET    /:id          # Get project
│   │   ├── PUT    /:id          # Update project
│   │   └── DELETE /:id          # Delete project
│   │
│   ├── /repositories            # Repository management
│   │   ├── GET    /             # List repositories
│   │   ├── POST   /             # Add repository
│   │   ├── GET    /:id          # Get repository
│   │   ├── PUT    /:id          # Update repository
│   │   ├── DELETE /:id          # Remove repository
│   │   └── POST   /:id/sync     # Sync from source
│   │
│   ├── /scans                   # Scan jobs
│   │   ├── GET    /             # List scans
│   │   ├── POST   /             # Create scan
│   │   ├── GET    /:id          # Get scan status
│   │   ├── POST   /:id/cancel   # Cancel scan
│   │   └── DELETE /:id          # Delete scan
│   │
│   ├── /findings                # Security findings
│   │   ├── GET    /             # List findings (filtered)
│   │   ├── GET    /:id          # Get finding details
│   │   ├── PUT    /:id          # Update finding (status)
│   │   └── POST   /bulk-update  # Bulk operations
│   │
│   ├── /reports                 # Generated reports
│   │   ├── GET    /             # List reports
│   │   ├── GET    /:id          # Get report
│   │   ├── GET    /:id/download # Download (JSON/PDF)
│   │   └── POST   /:id/share    # Generate share link
│   │
│   ├── /dashboard               # Dashboard data
│   │   ├── GET /summary         # Org summary
│   │   ├── GET /trends          # Score trends
│   │   ├── GET /metrics         # Key metrics
│   │   └── GET /alerts          # Active alerts
│   │
│   ├── /billing                 # Subscription & billing
│   │   ├── GET  /subscription   # Get subscription
│   │   ├── POST /subscription   # Create/update subscription
│   │   ├── GET  /invoices       # List invoices
│   │   ├── GET  /usage          # Current usage
│   │   └── POST /checkout       # Stripe checkout
│   │
│   └── /settings                # Organization settings
│       ├── GET  /               # Get settings
│       ├── PUT  /               # Update settings
│       ├── GET  /integrations   # List integrations
│       └── POST /integrations   # Add integration
│
├── /v2                          # Future API version
│   └── ...                      # Backward compatible
│
└── /webhooks                    # Incoming webhooks
    ├── /github                  # GitHub webhook events
    └── /stripe                  # Stripe webhook events
```

---

## 4. Suggested Folder Structure

### 4.1 Backend Structure (Production-Ready)

```
backend/
├── src/
│   └── devarchai/
│       ├── __init__.py
│       │
│       ├── main.py                    # Application factory
│       ├── config.py                  # Configuration management
│       │
│       ├── api/                       # API Layer
│       │   ├── __init__.py
│       │   ├── deps.py                # FastAPI dependencies
│       │   ├── middleware/            # Custom middleware
│       │   │   ├── __init__.py
│       │   │   ├── authentication.py  # JWT auth middleware
│       │   │   ├── rate_limiter.py    # Rate limiting
│       │   │   ├── request_logger.py  # Request logging
│       │   │   └── error_handler.py   # Global error handling
│       │   │
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── router.py          # API v1 router aggregation
│       │       │
│       │       └── endpoints/
│       │           ├── __init__.py
│       │           ├── auth.py        # Authentication endpoints
│       │           ├── organizations.py
│       │           ├── projects.py
│       │           ├── repositories.py
│       │           ├── scans.py
│       │           ├── findings.py
│       │           ├── reports.py
│       │           ├── dashboard.py
│       │           ├── billing.py
│       │           ├── webhooks.py
│       │           └── health.py
│       │
│       ├── core/                      # Core utilities
│       │   ├── __init__.py
│       │   ├── security.py            # JWT, password hashing
│       │   ├── exceptions.py          # Custom exceptions
│       │   ├── validators.py          # Input validators
│       │   ├── constants.py           # Application constants
│       │   └── telemetry.py           # OpenTelemetry setup
│       │
│       ├── db/                        # Database layer
│       │   ├── __init__.py
│       │   ├── base.py                # SQLAlchemy base
│       │   ├── session.py             # Session management
│       │   ├── engine.py              # Database engine
│       │   │
│       │   ├── repositories/          # Data access layer
│       │   │   ├── __init__.py
│       │   │   ├── base.py            # Generic repository
│       │   │   ├── user_repo.py
│       │   │   ├── organization_repo.py
│       │   │   ├── project_repo.py
│       │   │   ├── repository_repo.py
│       │   │   ├── scan_repo.py
│       │   │   └── finding_repo.py
│       │   │
│       │   └── migrations/            # Alembic migrations
│       │       ├── env.py
│       │       ├── script.py.mako
│       │       └── versions/
│       │
│       ├── models/                    # SQLAlchemy models
│       │   ├── __init__.py
│       │   ├── base.py                # Base model with common fields
│       │   ├── user.py
│       │   ├── organization.py
│       │   ├── project.py
│       │   ├── repository.py
│       │   ├── scan.py
│       │   ├── finding.py
│       │   ├── report.py
│       │   ├── subscription.py
│       │   ├── audit_log.py
│       │   └── mixins/
│       │       ├── __init__.py
│       │       ├── timestamp.py       # Created/updated timestamps
│       │       ├── soft_delete.py     # Soft delete mixin
│       │       └── tenant.py          # Organization ID mixin
│       │
│       ├── schemas/                   # Pydantic schemas
│       │   ├── __init__.py
│       │   ├── common.py              # Common response schemas
│       │   ├── auth.py
│       │   ├── organization.py
│       │   ├── project.py
│       │   ├── repository.py
│       │   ├── scan.py
│       │   ├── finding.py
│       │   ├── report.py
│       │   ├── billing.py
│       │   └── webhooks.py
│       │
│       ├── services/                  # Business logic layer
│       │   ├── __init__.py
│       │   ├── base.py                # Service base class
│       │   ├── auth_service.py
│       │   ├── organization_service.py
│       │   ├── project_service.py
│       │   ├── repository_service.py
│       │   ├── scan_service.py
│       │   ├── report_service.py
│       │   ├── billing_service.py
│       │   ├── notification_service.py
│       │   └── webhook_service.py
│       │
│       ├── analysis/                  # Analysis domain
│       │   ├── __init__.py
│       │   ├── pipeline.py            # Analysis pipeline orchestrator
│       │   │
│       │   ├── parsers/               # File parsers
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── terraform_parser.py
│       │   │   ├── kubernetes_parser.py
│       │   │   ├── dockerfile_parser.py
│       │   │   └── cicd_parser.py
│       │   │
│       │   ├── rules/                 # Analysis rules
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── registry.py
│       │   │   ├── security_rules.py
│       │   │   ├── scalability_rules.py
│       │   │   ├── reliability_rules.py
│       │   │   ├── cost_rules.py
│       │   │   └── observability_rules.py
│       │   │
│       │   ├── scoring/               # Scoring engine
│       │   │   ├── __init__.py
│       │   │   ├── engine.py
│       │   │   ├── weights.py
│       │   │   └── calculator.py
│       │   │
│       │   └── ai/                    # AI analysis
│       │       ├── __init__.py
│       │       ├── llm_provider.py    # LLM abstraction
│       │       ├── explanation_engine.py
│       │       ├── summary_generator.py
│       │       └── prompts/
│       │           ├── __init__.py
│       │           ├── executive_summary.py
│       │           ├── risk_analysis.py
│       │           └── recommendations.py
│       │
│       ├── workers/                   # Background workers
│       │   ├── __init__.py
│       │   ├── celery_app.py          # Celery configuration
│       │   ├── tasks/
│       │   │   ├── __init__.py
│       │   │   ├── scan_tasks.py      # Scan execution
│       │   │   ├── report_tasks.py    # Report generation
│       │   │   ├── email_tasks.py     # Email notifications
│       │   │   ├── webhook_tasks.py   # Outgoing webhooks
│       │   │   └── cleanup_tasks.py   # Data cleanup
│       │   └── schedulers/
│       │       ├── __init__.py
│       │       └── periodic_tasks.py  # Celery Beat tasks
│       │
│       ├── integrations/              # External integrations
│       │   ├── __init__.py
│       │   ├── github/
│       │   │   ├── __init__.py
│       │   │   ├── client.py
│       │   │   ├── oauth.py
│       │   │   └── webhook_handler.py
│       │   ├── stripe/
│       │   │   ├── __init__.py
│       │   │   ├── client.py
│       │   │   └── webhook_handler.py
│       │   ├── email/
│       │   │   ├── __init__.py
│       │   │   ├── sendgrid.py
│       │   │   └── templates.py
│       │   └── storage/
│       │       ├── __init__.py
│       │       ├── s3.py
│       │       └── local.py
│       │
│       └── utils/                     # Shared utilities
│           ├── __init__.py
│           ├── logging.py
│           ├── pagination.py
│           ├── caching.py
│           └── helpers.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   ├── factories/                     # Test data factories
│   │   ├── user_factory.py
│   │   ├── organization_factory.py
│   │   └── scan_factory.py
│   │
│   ├── unit/                          # Unit tests
│   │   ├── test_parsers/
│   │   ├── test_rules/
│   │   ├── test_services/
│   │   └── test_workers/
│   │
│   ├── integration/                   # Integration tests
│   │   ├── test_api/
│   │   ├── test_database/
│   │   └── test_workers/
│   │
│   └── e2e/                           # End-to-end tests
│       └── test_workflows/
│
├── scripts/
│   ├── __init__.py
│   ├── seed_data.py                   # Database seeding
│   ├── generate_migrations.py
│   └── cleanup_old_scans.py
│
├── requirements/
│   ├── base.txt                       # Core dependencies
│   ├── dev.txt                        # Development dependencies
│   ├── prod.txt                       # Production dependencies
│   └── test.txt                       # Testing dependencies
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── setup.py
└── README.md
```

### 4.2 Frontend Structure (Production-Ready)

```
frontend/
├── src/
│   ├── main.tsx                       # Application entry point
│   ├── App.tsx                        # Root component
│   ├── vite-env.d.ts
│   │
│   ├── app/                           # Application configuration
│   │   ├── store.ts                   # Zustand store setup
│   │   ├── query-client.ts            # React Query setup
│   │   └── router.tsx                 # Route definitions
│   │
│   ├── api/                           # API layer
│   │   ├── client.ts                  # Axios instance
│   │   ├── interceptors.ts            # Auth/error interceptors
│   │   │
│   │   └── endpoints/
│   │       ├── auth.ts
│   │       ├── organizations.ts
│   │       ├── projects.ts
│   │       ├── repositories.ts
│   │       ├── scans.ts
│   │       ├── findings.ts
│   │       ├── reports.ts
│   │       ├── dashboard.ts
│   │       └── billing.ts
│   │
│   ├── components/                    # UI components
│   │   ├── ui/                        # Base UI components (shadcn)
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── table.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── progress.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── select.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/                    # Layout components
│   │   │   ├── app-layout.tsx
│   │   │   ├── sidebar.tsx
│   │   │   ├── header.tsx
│   │   │   ├── footer.tsx
│   │   │   └── navigation.tsx
│   │   │
│   │   ├── auth/                      # Auth components
│   │   │   ├── login-form.tsx
│   │   │   ├── register-form.tsx
│   │   │   ├── forgot-password-form.tsx
│   │   │   └── protected-route.tsx
│   │   │
│   │   ├── dashboard/                 # Dashboard components
│   │   │   ├── overview-cards.tsx
│   │   │   ├── score-chart.tsx
│   │   │   ├── recent-scans.tsx
│   │   │   ├── alerts-panel.tsx
│   │   │   └── activity-feed.tsx
│   │   │
│   │   ├── projects/                  # Project components
│   │   │   ├── project-list.tsx
│   │   │   ├── project-card.tsx
│   │   │   ├── project-form.tsx
│   │   │   └── project-selector.tsx
│   │   │
│   │   ├── repositories/              # Repository components
│   │   │   ├── repository-list.tsx
│   │   │   ├── repository-card.tsx
│   │   │   ├── repository-form.tsx
│   │   │   └── sync-status.tsx
│   │   │
│   │   ├── scans/                     # Scan components
│   │   │   ├── scan-list.tsx
│   │   │   ├── scan-card.tsx
│   │   │   ├── scan-progress.tsx
│   │   │   ├── scan-trigger.tsx
│   │   │   └── scan-filters.tsx
│   │   │
│   │   ├── findings/                  # Finding components
│   │   │   ├── findings-table.tsx
│   │   │   ├── finding-detail.tsx
│   │   │   ├── finding-filters.tsx
│   │   │   ├── severity-badge.tsx
│   │   │   └── bulk-actions.tsx
│   │   │
│   │   ├── reports/                   # Report components
│   │   │   ├── report-viewer.tsx
│   │   │   ├── report-summary.tsx
│   │   │   ├── score-gauge.tsx
│   │   │   ├── category-breakdown.tsx
│   │   │   └── export-buttons.tsx
│   │   │
│   │   ├── billing/                   # Billing components
│   │   │   ├── plan-card.tsx
│   │   │   ├── usage-meter.tsx
│   │   │   ├── invoice-list.tsx
│   │   │   └── payment-method.tsx
│   │   │
│   │   └── settings/                  # Settings components
│   │       ├── profile-form.tsx
│   │       ├── org-settings.tsx
│   │       ├── member-list.tsx
│   │       ├── invite-form.tsx
│   │       └── integrations.tsx
│   │
│   ├── pages/                         # Page components
│   │   ├── auth/
│   │   │   ├── login-page.tsx
│   │   │   ├── register-page.tsx
│   │   │   └── forgot-password-page.tsx
│   │   │
│   │   ├── dashboard/
│   │   │   └── dashboard-page.tsx
│   │   │
│   │   ├── projects/
│   │   │   ├── projects-page.tsx
│   │   │   └── project-detail-page.tsx
│   │   │
│   │   ├── repositories/
│   │   │   ├── repositories-page.tsx
│   │   │   └── repository-detail-page.tsx
│   │   │
│   │   ├── scans/
│   │   │   ├── scans-page.tsx
│   │   │   └── scan-detail-page.tsx
│   │   │
│   │   ├── findings/
│   │   │   └── findings-page.tsx
│   │   │
│   │   ├── reports/
│   │   │   ├── reports-page.tsx
│   │   │   └── report-detail-page.tsx
│   │   │
│   │   ├── billing/
│   │   │   ├── billing-page.tsx
│   │   │   └── checkout-page.tsx
│   │   │
│   │   └── settings/
│   │       ├── settings-page.tsx
│   │       ├── profile-page.tsx
│   │       └── organization-page.tsx
│   │
│   ├── hooks/                         # Custom hooks
│   │   ├── use-auth.ts
│   │   ├── use-user.ts
│   │   ├── use-organization.ts
│   │   ├── use-scans.ts
│   │   ├── use-findings.ts
│   │   ├── use-reports.ts
│   │   ├── use-billing.ts
│   │   ├── use-polling.ts
│   │   └── use-debounce.ts
│   │
│   ├── stores/                        # Zustand stores
│   │   ├── auth-store.ts
│   │   ├── organization-store.ts
│   │   ├── ui-store.ts
│   │   └── scan-store.ts
│   │
│   ├── types/                         # TypeScript types
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── organization.ts
│   │   ├── project.ts
│   │   ├── repository.ts
│   │   ├── scan.ts
│   │   ├── finding.ts
│   │   ├── report.ts
│   │   └── billing.ts
│   │
│   ├── utils/                         # Utility functions
│   │   ├── cn.ts                      # Class name utility
│   │   ├── formatters.ts              # Date/number formatters
│   │   ├── validators.ts              # Form validators
│   │   └── constants.ts
│   │
│   └── assets/                        # Static assets
│       ├── images/
│       ├── icons/
│       └── fonts/
│
├── public/
│   ├── favicon.ico
│   ├── manifest.json
│   └── robots.txt
│
├── tests/
│   ├── unit/
│   ├── components/
│   └── e2e/
│
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── .env.example
├── Dockerfile
└── README.md
```

---

## 5. Required Core Modules for the SaaS

### 5.1 Authentication & Authorization Module

```python
# Core responsibilities:
# - User registration/login (email + OAuth)
# - JWT token management (access + refresh)
# - Organization-based access control
# - Role-based permissions (owner, admin, member, viewer)
# - API key management for enterprise

class AuthService:
    async def register(self, email: str, password: str, org_name: str) -> User
    async def login(self, email: str, password: str) -> TokenPair
    async def refresh_token(self, refresh_token: str) -> TokenPair
    async def logout(self, user_id: int) -> None
    async def verify_token(self, token: str) -> TokenPayload
    async def reset_password(self, token: str, new_password: str) -> None

class PermissionService:
    def check_permission(self, user: User, resource: str, action: str) -> bool
    def get_user_roles(self, user_id: int, org_id: int) -> list[Role]
```

### 5.2 Multi-Tenancy Module

```python
# Core responsibilities:
# - Organization CRUD
# - Member management (invite, remove, role change)
# - Row-level security enforcement
# - Quota tracking per organization
# - Feature flags per plan

class OrganizationService:
    async def create(self, name: str, owner: User) -> Organization
    async def get_by_id(self, org_id: int) -> Organization
    async def get_by_slug(self, slug: str) -> Organization
    async def update(self, org_id: int, data: OrgUpdate) -> Organization
    async def delete(self, org_id: int) -> None

class MemberService:
    async def invite_member(self, org_id: int, email: str, role: Role) -> Invitation
    async def accept_invitation(self, token: str, user: User) -> Member
    async def update_role(self, org_id: int, user_id: int, role: Role) -> Member
    async def remove_member(self, org_id: int, user_id: int) -> None
```

### 5.3 Project & Repository Module

```python
# Core responsibilities:
# - Project grouping for repositories
# - Repository CRUD with GitHub integration
# - Repository sync/refresh
# - Webhook management

class ProjectService:
    async def create(self, org_id: int, name: str, description: str) -> Project
    async def list(self, org_id: int, filters: Filter) -> list[Project]
    async def get(self, project_id: int) -> Project
    async def update(self, project_id: int, data: ProjectUpdate) -> Project
    async def delete(self, project_id: int) -> None

class RepositoryService:
    async def add_from_github(self, org_id: int, github_repo_id: int) -> Repository
    async def sync(self, repo_id: int) -> SyncResult
    async def list(self, project_id: int) -> list[Repository]
    async def get(self, repo_id: int) -> Repository
```

### 5.4 Scan & Analysis Module

```python
# Core responsibilities:
# - Scan job creation and tracking
# - Background analysis execution
# - Progress reporting
# - Result aggregation

class ScanService:
    async def create(self, repo_id: int, config: ScanConfig) -> Scan
    async def get(self, scan_id: int) -> Scan
    async def list(self, repo_id: int, filters: Filter) -> list[Scan]
    async def cancel(self, scan_id: int) -> Scan
    async def delete(self, scan_id: int) -> None

class AnalysisPipeline:
    async def execute(self, scan: Scan) -> AnalysisResult
    async def clone_repository(self, url: str, ref: str) -> str
    async def parse_files(self, repo_path: str) -> list[ParsedFile]
    async def run_rules(self, files: list[ParsedFile]) -> list[Finding]
    async def calculate_scores(self, findings: list[Finding]) -> Scores
    async def generate_report(self, result: AnalysisResult) -> Report
```

### 5.5 Findings & Reports Module

```python
# Core responsibilities:
# - Finding CRUD with status tracking
# - Report generation (JSON, PDF)
# - Report sharing
# - Historical comparison

class FindingService:
    async def list(self, scan_id: int, filters: Filter) -> list[Finding]
    async def get(self, finding_id: int) -> Finding
    async def update_status(self, finding_id: int, status: Status) -> Finding
    async def bulk_update(self, finding_ids: list[int], update: Update) -> list[Finding]

class ReportService:
    async def generate(self, scan_id: int, format: str) -> Report
    async def get(self, report_id: int) -> Report
    async def download(self, report_id: int, format: str) -> bytes
    async def share(self, report_id: int, expires_in: int) -> ShareLink
```

### 5.6 Billing & Subscription Module

```python
# Core responsibilities:
# - Stripe integration
# - Plan management (free, pro, enterprise)
# - Usage tracking and limits
# - Invoice generation

class BillingService:
    async def get_subscription(self, org_id: int) -> Subscription
    async def create_checkout_session(self, org_id: int, plan: str) -> CheckoutSession
    async def handle_webhook(self, event: StripeEvent) -> None
    async def get_usage(self, org_id: int) -> Usage
    async def get_invoices(self, org_id: int) -> list[Invoice]

# Plan limits example
PLAN_LIMITS = {
    "free": {
        "scans_per_month": 10,
        "repositories": 3,
        "team_members": 1,
        "report_retention_days": 7,
    },
    "pro": {
        "scans_per_month": 100,
        "repositories": 20,
        "team_members": 10,
        "report_retention_days": 90,
    },
    "enterprise": {
        "scans_per_month": -1,  # unlimited
        "repositories": -1,
        "team_members": -1,
        "report_retention_days": 365,
    },
}
```

### 5.7 Notification Module

```python
# Core responsibilities:
# - Email notifications
# - In-app notifications
# - Webhook delivery
# - Scheduled digests

class NotificationService:
    async def send_scan_complete(self, user_id: int, scan: Scan) -> None
    async def send_critical_finding(self, user_id: int, finding: Finding) -> None
    async def send_weekly_digest(self, user_id: int) -> None
    async def send_invitation(self, email: str, org: Organization, role: Role) -> None

class WebhookService:
    async def deliver(self, webhook: Webhook, event: Event) -> DeliveryResult
    async def retry(self, delivery_id: int) -> DeliveryResult
```

### 5.8 Dashboard & Analytics Module

```python
# Core responsibilities:
# - Aggregated metrics
# - Trend analysis
# - Alert generation
# - Export capabilities

class DashboardService:
    async def get_summary(self, org_id: int) -> DashboardSummary
    async def get_trends(self, org_id: int, period: str) -> Trends
    async def get_active_alerts(self, org_id: int) -> list[Alert]
    async def get_activity_feed(self, org_id: int) -> list[Activity]
```

---

## 6. Recommended Improvements for V1

### 6.1 Priority 1 (Must Have for Launch)

| # | Improvement | Effort | Impact | Description |
|---|-------------|--------|--------|-------------|
| 1 | **Implement Celery properly** | High | Critical | Replace in-memory worker pool with Celery + Redis/RabbitMQ |
| 2 | **Add multi-tenancy** | High | Critical | Organization model with row-level security |
| 3 | **Implement proper auth** | Medium | Critical | JWT with refresh tokens, OAuth integration |
| 4 | **Add rate limiting** | Low | High | Per-user and per-IP rate limiting |
| 5 | **Implement billing** | High | Critical | Stripe integration with subscription management |
| 6 | **Add audit logging** | Medium | High | Track all user actions for compliance |
| 7 | **Implement proper error handling** | Medium | High | Global error handler with proper responses |

### 6.2 Priority 2 (Should Have)

| # | Improvement | Effort | Impact | Description |
|---|-------------|--------|--------|-------------|
| 1 | **Add caching layer** | Medium | High | Redis caching for API responses |
| 2 | **Implement WebSocket** | Medium | Medium | Real-time scan progress updates |
| 3 | **Add scheduled scans** | Medium | High | Cron-based recurring scans |
| 4 | **Implement webhooks** | Medium | Medium | Outgoing webhooks for integrations |
| 5 | **Add PDF report generation** | Low | Medium | Professional PDF reports |
| 6 | **Implement search** | Medium | Medium | Elasticsearch for finding search |
| 7 | **Add API documentation** | Low | Medium | OpenAPI/Swagger docs |

### 6.3 Priority 3 (Nice to Have)

| # | Improvement | Effort | Impact | Description |
|---|-------------|--------|--------|-------------|
| 1 | **Add dark mode** | Low | Low | UI theme toggle |
| 2 | **Implement SSO** | High | Medium | SAML/OIDC for enterprise |
| 3 | **Add mobile app** | High | Low | React Native app |
| 4 | **Implement chatbot** | Medium | Low | AI-powered Q&A about findings |
| 5 | **Add Slack integration** | Medium | Medium | Slack notifications |
| 6 | **Implement compliance reports** | Medium | Medium | SOC2, HIPAA checklists |

### 6.4 Infrastructure Improvements

```yaml
# docker-compose.prod.yml (excerpt)
services:
  api:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
      restart_policy:
        condition: on-failure
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    deploy:
      replicas: 5
      resources:
        limits:
          cpus: '2'
          memory: 2G

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru

  postgres:
    image: postgres:15-alpine
    deploy:
      resources:
        limits:
          memory: 4G
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### 6.5 Security Checklist for V1

- [ ] Implement rate limiting (100 req/min per user)
- [ ] Add request size limits (10MB max)
- [ ] Enable CORS with specific origins
- [ ] Add CSRF protection for state-changing operations
- [ ] Implement input validation on all endpoints
- [ ] Add SQL injection prevention (parameterized queries)
- [ ] Enable HTTPS only (HSTS headers)
- [ ] Implement proper session management
- [ ] Add security headers (CSP, X-Frame-Options, etc.)
- [ ] Implement proper logging (no sensitive data)
- [ ] Add vulnerability scanning in CI/CD
- [ ] Implement secret rotation
- [ ] Add database encryption at rest

### 6.6 Monitoring Setup

```yaml
# Key metrics to track
metrics:
  api:
    - request_latency_p50
    - request_latency_p95
    - request_latency_p99
    - error_rate
    - requests_per_second
  
  workers:
    - queue_depth
    - job_duration
    - job_failure_rate
    - worker_utilization
  
  business:
    - scans_per_day
    - active_users
    - conversion_rate
    - mrr
  
  infrastructure:
    - cpu_utilization
    - memory_utilization
    - disk_usage
    - database_connections
```

---

## 7. Migration Path from Current to Target

### Phase 1: Foundation (Weeks 1-2)

1. Restructure backend folder structure
2. Implement proper Celery setup
3. Add organization model and multi-tenancy
4. Implement row-level security

### Phase 2: Authentication (Weeks 3-4)

1. Implement JWT authentication
2. Add OAuth (GitHub, Google)
3. Implement role-based access control
4. Add API key management

### Phase 3: Billing (Weeks 5-6)

1. Integrate Stripe
2. Implement subscription management
3. Add usage tracking
4. Create billing UI

### Phase 4: Polish (Weeks 7-8)

1. Complete all frontend pages
2. Add real-time updates (WebSocket)
3. Implement notifications
4. Add comprehensive testing

---

## Appendix A: Database Schema (Target)

```sql
-- Organizations (Tenants)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    github_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Organization Members
CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    user_id UUID REFERENCES users(id),
    role VARCHAR(50) DEFAULT 'member',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Repositories
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    project_id UUID REFERENCES projects(id),
    github_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    default_branch VARCHAR(100) DEFAULT 'main',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Scans
CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    repository_id UUID REFERENCES repositories(id),
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    overall_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Findings
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    scan_id UUID REFERENCES scans(id),
    rule_id VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT,
    file_path VARCHAR(500),
    status VARCHAR(50) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_findings_org ON findings(organization_id);
CREATE INDEX idx_findings_scan ON findings(scan_id);
CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_scans_org ON scans(organization_id);
CREATE INDEX idx_repos_org ON repositories(organization_id);
```

---

## Appendix B: API Response Standards

```typescript
// Success response
{
  "data": { ... },
  "meta": {
    "request_id": "req_123456",
    "timestamp": "2026-03-06T10:00:00Z"
  }
}

// Paginated response
{
  "data": [...],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8
  }
}

// Error response
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      { "field": "email", "message": "Invalid email format" }
    ]
  },
  "meta": {
    "request_id": "req_123456",
    "timestamp": "2026-03-06T10:00:00Z"
  }
}
```

---

## Conclusion

This architecture redesign transforms DevArchAI from a prototype into a production-ready SaaS platform. The key changes focus on:

1. **Multi-tenancy** - Essential for SaaS billing and isolation
2. **Proper task queue** - Celery for reliable background processing
3. **Clean architecture** - Separation of concerns with services, repositories, and domain layers
4. **Security first** - Rate limiting, authentication, and audit logging
5. **Scalability** - Horizontal scaling ready with proper caching and database design

The recommended implementation path prioritizes critical features for launch while maintaining a clear roadmap for future enhancements.
