# DevArchAI - Architecture Migration Plan

**Document Version:** 1.0  
**Date:** March 6, 2026  
**Status:** Ready for Implementation

---

## 1. Current Architecture Summary

### 1.1 Backend Overview

| Component | Current State | Assessment |
|-----------|---------------|------------|
| **Framework** | FastAPI 0.109.0 | ✅ Good |
| **Structure** | `app/` with modular folders | ⚠️ Partially organized |
| **Database** | PostgreSQL + SQLAlchemy 2.0 | ✅ Good |
| **Auth** | JWT + API Keys | ✅ Implemented |
| **Task Queue** | Celery (installed but unused) | ❌ Not configured |
| **Workers** | In-memory dict (`_worker_pool`) | ❌ Critical issue |
| **Multi-tenancy** | None (user-centric) | ❌ Missing |

### 1.2 Frontend Overview

| Component | Current State | Assessment |
|-----------|---------------|------------|
| **Framework** | React 18 + TypeScript | ✅ Good |
| **Build Tool** | Vite | ✅ Good |
| **State** | Zustand + React Query | ✅ Good |
| **UI** | shadcn/ui + Tailwind | ✅ Good |
| **Routing** | React Router v6 | ✅ Good |
| **API Client** | Basic axios | ⚠️ Missing interceptors |
| **Pages** | 4 pages (2 placeholders) | ⚠️ Incomplete |

### 1.3 Current Backend Structure

```
backend/app/
├── api/
│   ├── v1/
│   │   ├── router.py
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── health.py
│   │       ├── scans.py
│   │       ├── repositories.py
│   │       ├── reports.py
│   │       └── repo_analysis.py
│   └── routes/ (duplicate?)
├── core/
│   ├── security.py
│   ├── exceptions.py
│   └── logging.py
├── db/
│   ├── base.py
│   └── session.py
├── models/
│   ├── user.py
│   ├── scan.py
│   ├── finding.py
│   ├── report.py
│   ├── repository.py
│   └── schemas.py
├── services/
│   ├── analysis.py
│   ├── scan_service.py
│   ├── github.py
│   └── cache.py
├── workers/
│   └── scan_worker.py (in-memory!)
├── parsers/
├── rules/
├── rule_engine/
├── ai_engine/
├── scoring/
└── utils/
```

### 1.4 Current Frontend Structure

```
frontend/src/
├── components/
│   ├── Layout.tsx
│   ├── RepoAnalyzerInput.tsx
│   ├── ui.tsx
│   └── (missing organized folders)
├── pages/
│   ├── Home.tsx
│   ├── Dashboard.tsx
│   ├── Report.tsx
│   └── index.ts
├── services/
│   └── api.ts (basic)
├── types/
│   └── (missing)
├── lib/
│   └── utils.ts
└── App.tsx
```

---

## 2. Gaps Analysis: Current vs Target Architecture

### 2.1 Critical Gaps (P0)

| # | Gap | Current | Target | Impact |
|---|-----|---------|--------|--------|
| 1 | **Multi-tenancy** | User-centric model | Organization-based | Cannot support SaaS billing |
| 2 | **Task Queue** | In-memory worker pool | Celery + Redis/RabbitMQ | No horizontal scaling |
| 3 | **Organization Model** | Missing | Required | No team features |
| 4 | **Row-Level Security** | Missing | Required | No tenant isolation |
| 5 | **Billing Integration** | Missing | Stripe | Cannot monetize |

### 2.2 High Priority Gaps (P1)

| # | Gap | Current | Target | Impact |
|---|-----|---------|--------|--------|
| 1 | **API Structure** | Mixed endpoints | Clean resource-based | Maintainability |
| 2 | **Service Layer** | Some services exist | Complete service layer | Business logic separation |
| 3 | **Repository Pattern** | Direct DB access | Repository abstraction | Testability |
| 4 | **Frontend API Layer** | Basic axios | Organized endpoints | Error handling |
| 5 | **Audit Logging** | Missing | Required | Compliance |
| 6 | **Rate Limiting** | Missing | Required | DoS protection |

### 2.3 Medium Priority Gaps (P2)

| # | Gap | Current | Target | Impact |
|---|-----|---------|--------|--------|
| 1 | **Folder Naming** | Inconsistent | Consistent snake_case | Developer experience |
| 2 | **Analysis Module** | Scattered parsers/rules | Unified `analysis/` domain | Clarity |
| 3 | **Frontend Components** | Flat structure | Organized by feature | Scalability |
| 4 | **Error Handling** | Basic | Global error boundaries | UX |
| 5 | **TypeScript Types** | Missing | Complete type coverage | Type safety |

---

## 3. Proposed Redesigned Architecture

### 3.1 Architecture Principles

1. **Domain-Driven Design** - Organize by business domain
2. **Separation of Concerns** - Clear layer boundaries
3. **Multi-Tenancy First** - Organization isolation at core
4. **Async-First** - Background processing for heavy tasks
5. **Security by Default** - Auth, rate limiting, validation

### 3.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DevArchAI Redesigned                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────────────────────────────┐    │
│  │   React     │───▶│         FastAPI Gateway             │    │
│  │  Frontend   │    │  ┌───────────────────────────────┐  │    │
│  │             │    │  │  Middleware Layer             │  │    │
│  └─────────────┘    │  │  - Auth                       │  │    │
│                     │  │  - Rate Limiting              │  │    │
│                     │  │  - Request Logging            │  │    │
│                     │  └───────────────────────────────┘  │    │
│                     │                                     │    │
│                     │  ┌───────────────────────────────┐  │    │
│                     │  │  API Endpoints (v1)           │  │    │
│                     │  └───────────────────────────────┘  │    │
│                     │                                     │    │
│                     │  ┌───────────────────────────────┐  │    │
│                     │  │  Services (Business Logic)    │  │    │
│                     │  └───────────────────────────────┘  │    │
│                     │                                     │    │
│                     │  ┌───────────────────────────────┐  │    │
│                     │  │  Repositories (Data Access)   │  │    │
│                     │  └───────────────────────────────┘  │    │
│                     └─────────────────────────────────────┘    │
│                               │                                 │
│              ┌────────────────┼────────────────┐               │
│              ▼                ▼                ▼               │
│     ┌────────────────┐ ┌────────────┐ ┌──────────────┐        │
│     │   PostgreSQL   │ │   Redis    │ │   Celery     │        │
│     │   (with RLS)   │ │  (Cache)   │ │   Workers    │        │
│     └────────────────┘ └────────────┘ └──────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Data Model Changes

```sql
-- NEW: Organizations table (tenant)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- MODIFIED: Users table (add org relationship)
ALTER TABLE users ADD COLUMN current_org_id UUID REFERENCES organizations(id);

-- NEW: Organization Members (many-to-many)
CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    user_id UUID REFERENCES users(id),
    role VARCHAR(50) DEFAULT 'member',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

-- MODIFIED: All resource tables add organization_id
ALTER TABLE scans ADD COLUMN organization_id UUID REFERENCES organizations(id);
ALTER TABLE repositories ADD COLUMN organization_id UUID REFERENCES organizations(id);
ALTER TABLE findings ADD COLUMN organization_id UUID REFERENCES organizations(id);
ALTER TABLE reports ADD COLUMN organization_id UUID REFERENCES organizations(id);

-- Enable Row Level Security
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE repositories ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- RLS Policies (example for scans)
CREATE POLICY org_isolation_scans ON scans
    FOR ALL
    USING (organization_id = current_setting('app.current_org_id')::uuid);
```

---

## 4. Updated Folder Structure

### 4.1 Backend - Target Structure

```
backend/
├── src/
│   └── devarchai/
│       ├── __init__.py
│       ├── main.py                    # ✅ Keep, update imports
│       ├── config.py                  # ✅ Keep, add new settings
│       │
│       ├── api/                       # 🔄 Reorganize
│       │   ├── __init__.py
│       │   ├── deps.py                # ✅ Move from app/core
│       │   ├── middleware/            # 🆕 Create
│       │   │   ├── __init__.py
│       │   │   ├── authentication.py  # 🆕 Create
│       │   │   ├── rate_limiter.py    # 🆕 Create
│       │   │   └── request_logger.py  # 🆕 Create
│       │   │
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── router.py          # ✅ Keep from app/api/v1
│       │       │
│       │       └── endpoints/         # 🔄 Rename from routes
│       │           ├── __init__.py
│       │           ├── auth.py        # ✅ Move from routes
│       │           ├── health.py      # ✅ Move from routes
│       │           ├── organizations.py  # 🆕 Create
│       │           ├── projects.py    # 🆕 Create
│       │           ├── repositories.py   # ✅ Move from routes
│       │           ├── scans.py       # ✅ Move from routes
│       │           ├── findings.py    # 🆕 Create
│       │           ├── reports.py     # ✅ Move from routes
│       │           ├── dashboard.py   # 🆕 Create
│       │           └── billing.py     # 🆕 Create
│       │
│       ├── core/                      # ✅ Keep structure
│       │   ├── __init__.py
│       │   ├── security.py            # ✅ Move from app/core
│       │   ├── exceptions.py          # ✅ Move from app/core
│       │   ├── logging.py             # ✅ Move from app/core
│       │   ├── constants.py           # 🆕 Create
│       │   └── validators.py          # 🆕 Create
│       │
│       ├── db/                        # ✅ Keep structure
│       │   ├── __init__.py
│       │   ├── base.py                # ✅ Keep
│       │   ├── engine.py              # 🆕 Extract from session.py
│       │   ├── session.py             # ✅ Keep
│       │   │
│       │   ├── repositories/          # 🆕 Create (pattern)
│       │   │   ├── __init__.py
│       │   │   ├── base.py            # 🆕 Create
│       │   │   ├── user_repo.py       # 🆕 Create
│       │   │   ├── organization_repo.py  # 🆕 Create
│       │   │   ├── scan_repo.py       # 🆕 Create
│       │   │   └── finding_repo.py    # 🆕 Create
│       │   │
│       │   └── migrations/            # ✅ Keep (Alembic)
│       │
│       ├── models/                    # ✅ Keep, add new models
│       │   ├── __init__.py
│       │   ├── base.py                # 🆕 Create (common fields)
│       │   ├── user.py                # ✅ Move, modify for multi-tenancy
│       │   ├── organization.py        # 🆕 Create
│       │   ├── project.py             # 🆕 Create
│       │   ├── repository.py          # ✅ Move, add org_id
│       │   ├── scan.py                # ✅ Move, add org_id
│       │   ├── finding.py             # ✅ Move, add org_id
│       │   ├── report.py              # ✅ Move, add org_id
│       │   ├── subscription.py        # 🆕 Create
│       │   └── audit_log.py           # 🆕 Create
│       │
│       ├── schemas/                   # ✅ Keep, reorganize
│       │   ├── __init__.py
│       │   ├── common.py              # ✅ Keep
│       │   ├── auth.py                # ✅ Keep
│       │   ├── organization.py        # 🆕 Create
│       │   ├── project.py             # 🆕 Create
│       │   ├── repository.py          # ✅ Move
│       │   ├── scan.py                # ✅ Move
│       │   ├── finding.py             # ✅ Move
│       │   ├── report.py              # ✅ Move
│       │   └── billing.py             # 🆕 Create
│       │
│       ├── services/                  # ✅ Keep, expand
│       │   ├── __init__.py
│       │   ├── base.py                # 🆕 Create
│       │   ├── auth_service.py        # 🆕 Extract from routes
│       │   ├── organization_service.py   # 🆕 Create
│       │   ├── scan_service.py        # ✅ Move, update
│       │   ├── report_service.py      # 🆕 Create
│       │   ├── billing_service.py     # 🆕 Create
│       │   └── notification_service.py   # 🆕 Create
│       │
│       ├── analysis/                  # 🆕 New domain module
│       │   ├── __init__.py
│       │   ├── pipeline.py            # 🆕 Create (orchestrator)
│       │   │
│       │   ├── parsers/               # ✅ Move from app/parsers
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── terraform_parser.py
│       │   │   ├── kubernetes_parser.py
│       │   │   ├── dockerfile_parser.py
│       │   │   └── cicd_parser.py
│       │   │
│       │   ├── rules/                 # ✅ Merge rules + rule_engine
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── registry.py
│       │   │   ├── security_rules.py
│       │   │   ├── scalability_rules.py
│       │   │   ├── reliability_rules.py
│       │   │   ├── cost_rules.py
│       │   │   └── observability_rules.py
│       │   │
│       │   ├── scoring/               # ✅ Move
│       │   │   ├── __init__.py
│       │   │   └── engine.py
│       │   │
│       │   └── ai/                    # ✅ Merge ai_engine
│       │       ├── __init__.py
│       │       └── explanation_engine.py
│       │
│       ├── workers/                   # 🔄 Complete rewrite
│       │   ├── __init__.py
│       │   ├── celery_app.py          # 🆕 Create (Celery config)
│       │   └── tasks/
│       │       ├── __init__.py
│       │       ├── scan_tasks.py      # 🆕 Create (Celery tasks)
│       │       ├── report_tasks.py    # 🆕 Create
│       │       └── email_tasks.py     # 🆕 Create
│       │
│       ├── integrations/              # 🆕 New
│       │   ├── __init__.py
│       │   ├── github/
│       │   │   ├── client.py
│       │   │   └── webhook.py
│       │   ├── stripe/
│       │   │   ├── client.py
│       │   │   └── webhook.py
│       │   └── email/
│       │       └── sendgrid.py
│       │
│       └── utils/                     # ✅ Keep
│           ├── __init__.py
│           ├── pagination.py
│           └── helpers.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
│
├── scripts/
│   ├── seed_data.py
│   └── generate_migrations.py
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

### 4.2 Frontend - Target Structure

```
frontend/
├── src/
│   ├── main.tsx                     # ✅ Keep
│   ├── App.tsx                      # ✅ Keep, update routes
│   ├── vite-env.d.ts                # ✅ Keep
│   │
│   ├── app/                         # 🆕 New (app config)
│   │   ├── store.ts                 # 🆕 Create (Zustand setup)
│   │   ├── query-client.ts          # 🆕 Create (React Query)
│   │   └── router.tsx               # 🆕 Create (route definitions)
│   │
│   ├── api/                         # 🆕 New (API layer)
│   │   ├── client.ts                # 🆕 Create (axios instance)
│   │   ├── interceptors.ts          # 🆕 Create (auth/error)
│   │   └── endpoints/
│   │       ├── auth.ts              # 🆕 Create
│   │       ├── organizations.ts     # 🆕 Create
│   │       ├── repositories.ts      # 🆕 Create
│   │       ├── scans.ts             # 🆕 Create
│   │       ├── findings.ts          # 🆕 Create
│   │       ├── reports.ts           # 🆕 Create
│   │       └── dashboard.ts         # 🆕 Create
│   │
│   ├── components/                  # 🔄 Reorganize
│   │   ├── ui/                      # 🆕 Base components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── table.tsx
│   │   │   ├── card.tsx             # ✅ Move from ui.tsx
│   │   │   ├── badge.tsx
│   │   │   └── progress.tsx
│   │   │
│   │   ├── layout/                  # 🆕 Layout components
│   │   │   ├── app-layout.tsx       # ✅ Move Layout.tsx
│   │   │   ├── sidebar.tsx
│   │   │   ├── header.tsx
│   │   │   └── navigation.tsx
│   │   │
│   │   ├── auth/                    # 🆕 Auth components
│   │   │   ├── login-form.tsx
│   │   │   ├── register-form.tsx
│   │   │   └── protected-route.tsx
│   │   │
│   │   ├── dashboard/               # 🆕 Dashboard components
│   │   │   ├── overview-cards.tsx
│   │   │   ├── score-chart.tsx
│   │   │   └── recent-scans.tsx
│   │   │
│   │   ├── repositories/            # 🆕 Repository components
│   │   │   ├── repo-list.tsx
│   │   │   ├── repo-card.tsx
│   │   │   └── repo-form.tsx
│   │   │
│   │   ├── scans/                   # 🆕 Scan components
│   │   │   ├── scan-list.tsx
│   │   │   ├── scan-card.tsx
│   │   │   ├── scan-progress.tsx
│   │   │   └── scan-trigger.tsx
│   │   │
│   │   ├── findings/                # 🆕 Finding components
│   │   │   ├── findings-table.tsx
│   │   │   ├── finding-detail.tsx
│   │   │   └── severity-badge.tsx
│   │   │
│   │   └── reports/                 # 🆕 Report components
│   │       ├── report-viewer.tsx
│   │       ├── report-summary.tsx
│   │       └── score-gauge.tsx
│   │
│   ├── pages/                       # ✅ Keep, expand
│   │   ├── auth/
│   │   │   ├── login-page.tsx       # 🆕 Create
│   │   │   └── register-page.tsx    # 🆕 Create
│   │   ├── dashboard/
│   │   │   └── dashboard-page.tsx   # ✅ Update
│   │   ├── repositories/
│   │   │   └── repositories-page.tsx  # 🆕 Create
│   │   ├── scans/
│   │   │   ├── scans-page.tsx       # 🆕 Create
│   │   │   └── scan-detail-page.tsx # 🆕 Create
│   │   ├── reports/
│   │   │   ├── reports-page.tsx     # 🆕 Create (replace placeholder)
│   │   │   └── report-detail-page.tsx  # ✅ Update Report.tsx
│   │   └── settings/
│   │       └── settings-page.tsx    # 🆕 Create (replace placeholder)
│   │
│   ├── hooks/                       # 🆕 New
│   │   ├── use-auth.ts
│   │   ├── use-scans.ts
│   │   ├── use-findings.ts
│   │   ├── use-reports.ts
│   │   └── use-polling.ts
│   │
│   ├── stores/                      # 🆕 New
│   │   ├── auth-store.ts
│   │   ├── ui-store.ts
│   │   └── scan-store.ts
│   │
│   ├── types/                       # 🆕 New
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── scan.ts
│   │   ├── finding.ts
│   │   └── report.ts
│   │
│   ├── utils/                       # ✅ Keep
│   │   └── cn.ts                    # ✅ Move from lib
│   │
│   └── assets/                      # ✅ Keep
│       └── images/
│
├── public/
├── tests/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── .env.example
```

---

## 5. Files to Move, Refactor, or Create

### 5.1 Backend - File Operations

#### Phase 1: Foundation (Week 1)

| Action | Source | Destination | Notes |
|--------|--------|-------------|-------|
| Move | `app/config.py` | `src/devarchai/config.py` | Add new settings |
| Move | `app/main.py` | `src/devarchai/main.py` | Update imports |
| Move | `app/core/security.py` | `src/devarchai/core/security.py` | Keep |
| Move | `app/core/exceptions.py` | `src/devarchai/core/exceptions.py` | Keep |
| Move | `app/core/logging.py` | `src/devarchai/core/logging.py` | Keep |
| Move | `app/db/base.py` | `src/devarchai/db/base.py` | Keep |
| Move | `app/db/session.py` | `src/devarchai/db/session.py` | Keep |
| Create | - | `src/devarchai/db/engine.py` | Extract from session |
| Create | - | `src/devarchai/db/repositories/base.py` | Generic repo |
| Create | - | `src/devarchai/models/base.py` | Common model fields |
| Create | - | `src/devarchai/models/organization.py` | **Critical** |
| Create | - | `src/devarchai/models/project.py` | New feature |
| Create | - | `src/devarchai/models/subscription.py` | Billing |
| Create | - | `src/devarchai/models/audit_log.py` | Compliance |

#### Phase 2: API Layer (Week 2)

| Action | Source | Destination | Notes |
|--------|--------|-------------|-------|
| Move | `app/api/v1/router.py` | `src/devarchai/api/v1/router.py` | Update imports |
| Move | `app/api/v1/routes/auth.py` | `src/devarchai/api/v1/endpoints/auth.py` | Rename folder |
| Move | `app/api/v1/routes/health.py` | `src/devarchai/api/v1/endpoints/health.py` | - |
| Move | `app/api/v1/routes/scans.py` | `src/devarchai/api/v1/endpoints/scans.py` | Update imports |
| Move | `app/api/v1/routes/repositories.py` | `src/devarchai/api/v1/endpoints/repositories.py` | - |
| Move | `app/api/v1/routes/reports.py` | `src/devarchai/api/v1/endpoints/reports.py` | - |
| Create | - | `src/devarchai/api/v1/endpoints/organizations.py` | **Critical** |
| Create | - | `src/devarchai/api/v1/endpoints/projects.py` | New |
| Create | - | `src/devarchai/api/v1/endpoints/findings.py` | New |
| Create | - | `src/devarchai/api/v1/endpoints/dashboard.py` | New |
| Create | - | `src/devarchai/api/v1/endpoints/billing.py` | **Critical** |
| Create | - | `src/devarchai/api/middleware/authentication.py` | New |
| Create | - | `src/devarchai/api/middleware/rate_limiter.py` | **Critical** |
| Create | - | `src/devarchai/api/deps.py` | Move from core |

#### Phase 3: Services & Domain (Week 3)

| Action | Source | Destination | Notes |
|--------|--------|-------------|-------|
| Move | `app/services/scan_service.py` | `src/devarchai/services/scan_service.py` | Update |
| Move | `app/services/analysis.py` | `src/devarchai/analysis/pipeline.py` | Rename |
| Move | `app/parsers/*` | `src/devarchai/analysis/parsers/` | Merge |
| Move | `app/rules/*` | `src/devarchai/analysis/rules/` | Merge |
| Move | `app/rule_engine/*` | `src/devarchai/analysis/rules/` | Merge |
| Move | `app/scoring/*` | `src/devarchai/analysis/scoring/` | - |
| Move | `app/ai_engine/*` | `src/devarchai/analysis/ai/` | Merge |
| Create | - | `src/devarchai/services/auth_service.py` | Extract from routes |
| Create | - | `src/devarchai/services/organization_service.py` | **Critical** |
| Create | - | `src/devarchai/services/billing_service.py` | **Critical** |
| Create | - | `src/devarchai/services/notification_service.py` | New |

#### Phase 4: Workers & Integration (Week 4)

| Action | Source | Destination | Notes |
|--------|--------|-------------|-------|
| Rewrite | `app/workers/scan_worker.py` | `src/devarchai/workers/celery_app.py` | **Critical** |
| Create | - | `src/devarchai/workers/tasks/scan_tasks.py` | Celery tasks |
| Create | - | `src/devarchai/workers/tasks/report_tasks.py` | New |
| Create | - | `src/devarchai/workers/tasks/email_tasks.py` | New |
| Create | - | `src/devarchai/integrations/github/client.py` | Move from services |
| Create | - | `src/devarchai/integrations/stripe/client.py` | **Critical** |
| Create | - | `src/devarchai/integrations/email/sendgrid.py` | New |

### 5.2 Frontend - File Operations

#### Phase 1: Foundation (Week 1)

| Action | Source | Destination | Notes |
|--------|--------|-------------|-------|
| Create | - | `src/app/store.ts` | Zustand setup |
| Create | - | `src/app/query-client.ts` | React Query |
| Create | - | `src/app/router.tsx` | Route definitions |
| Create | - | `src/api/client.ts` | Axios instance |
| Create | - | `src/api/interceptors.ts` | Auth/error handling |
| Move | `lib/utils.ts` | `src/utils/cn.ts` | Rename |

#### Phase 2: API Layer (Week 2)

| Action | Source | Destination | Notes |
|--------|--------|-------------|-------|
| Create | - | `src/api/endpoints/auth.ts` | Auth API |
| Create | - | `src/api/endpoints/organizations.ts` | Org API |
| Create | - | `src/api/endpoints/repositories.ts` | Repo API |
| Create | - | `src/api/endpoints/scans.ts` | Scan API |
| Create | - | `src/api/endpoints/findings.ts` | Findings API |
| Create | - | `src/api/endpoints/reports.ts` | Reports API |
| Create | - | `src/api/endpoints/dashboard.ts` | Dashboard API |

#### Phase 3: Components (Week 3)

| Action | Source | Destination | Notes |
|--------|--------|-------------|-------|
| Move | `components/Layout.tsx` | `src/components/layout/app-layout.tsx` | - |
| Move | `components/ui.tsx` | `src/components/ui/` | Split into files |
| Create | - | `src/components/auth/login-form.tsx` | New |
| Create | - | `src/components/auth/register-form.tsx` | New |
| Create | - | `src/components/auth/protected-route.tsx` | New |
| Create | - | `src/components/dashboard/overview-cards.tsx` | New |
| Create | - | `src/components/repositories/repo-list.tsx` | New |
| Create | - | `src/components/scans/scan-progress.tsx` | New |
| Create | - | `src/components/findings/findings-table.tsx` | New |

#### Phase 4: Pages (Week 4)

| Action | Source | Destination | Notes |
|--------|--------|-------------|-------|
| Create | - | `src/pages/auth/login-page.tsx` | New |
| Create | - | `src/pages/auth/register-page.tsx` | New |
| Move | `pages/Dashboard.tsx` | `src/pages/dashboard/dashboard-page.tsx` | Update |
| Move | `pages/Report.tsx` | `src/pages/reports/report-detail-page.tsx` | Update |
| Create | - | `src/pages/reports/reports-page.tsx` | Replace placeholder |
| Create | - | `src/pages/repositories/repositories-page.tsx` | New |
| Create | - | `src/pages/scans/scans-page.tsx` | New |
| Create | - | `src/pages/settings/settings-page.tsx` | Replace placeholder |

---

## 6. Step-by-Step Migration Plan

### Phase 1: Foundation & Multi-Tenancy (Week 1-2)

**Goal:** Establish new structure and add multi-tenancy support

#### Day 1-2: Backend Structure
```bash
# 1. Create new directory structure
mkdir -p backend/src/devarchai/{api,core,db,models,services,analysis,workers,integrations,utils}
mkdir -p backend/src/devarchai/api/{middleware,v1/endpoints}
mkdir -p backend/src/devarchai/db/repositories
mkdir -p backend/src/devarchai/analysis/{parsers,rules,scoring,ai}
mkdir -p backend/src/devarchai/workers/tasks
mkdir -p backend/src/devarchai/integrations/{github,stripe,email}

# 2. Copy core files
cp backend/app/{config.py,main.py} backend/src/devarchai/
cp backend/app/core/*.py backend/src/devarchai/core/
cp backend/app/db/{base.py,session.py} backend/src/devarchai/db/

# 3. Update imports in main.py
# Change: from app.config import settings
# To: from devarchai.config import settings
```

#### Day 3-4: Database Models
```bash
# 1. Create organization model
# 2. Update existing models with organization_id
# 3. Create migration scripts

# File: backend/src/devarchai/models/organization.py
from sqlalchemy import Column, String, Enum as SQLEnum
from app.db.base import Base
import enum

class PlanType(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(SQLEnum(PlanType), default=PlanType.FREE)
    # ... more fields
```

#### Day 5: Row-Level Security
```sql
-- Migration: Enable RLS
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE repositories ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access resources in their org
CREATE POLICY org_isolation ON scans
    FOR ALL
    USING (organization_id = current_setting('app.current_org_id')::uuid);
```

#### Day 6-7: Testing
- Test database migrations
- Test RLS policies
- Test organization CRUD operations

---

### Phase 2: API Layer & Authentication (Week 3-4)

**Goal:** Reorganize API endpoints and add middleware

#### Day 1-2: API Endpoints
```bash
# Move endpoint files
mkdir -p backend/src/devarchai/api/v1/endpoints
mv backend/app/api/v1/routes/*.py backend/src/devarchai/api/v1/endpoints/

# Update router.py imports
# Change: from app.api.v1.routes import auth
# To: from devarchai.api.v1.endpoints import auth
```

#### Day 3-4: Middleware
```python
# File: backend/src/devarchai/api/middleware/rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Usage in endpoints:
@router.get("/scans")
@limiter.limit("100/minute")
async def list_scans(request: Request, ...):
    ...
```

#### Day 5-7: Frontend API Layer
```typescript
// File: frontend/src/api/client.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Add auth interceptor
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add error interceptor for token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Attempt token refresh
    }
    return Promise.reject(error);
  }
);
```

---

### Phase 3: Services & Analysis Domain (Week 5-6)

**Goal:** Complete service layer and analysis module

#### Day 1-3: Service Layer
```bash
# Move and update services
mv backend/app/services/*.py backend/src/devarchai/services/

# Create new services
touch backend/src/devarchai/services/{auth_service,organization_service,billing_service}.py
```

#### Day 4-7: Analysis Module
```bash
# Consolidate analysis components
mv backend/app/parsers backend/src/devarchai/analysis/
mv backend/app/rules backend/src/devarchai/analysis/
mv backend/app/rule_engine backend/src/devarchai/analysis/
mv backend/app/scoring backend/src/devarchai/analysis/
mv backend/app/ai_engine backend/src/devarchai/analysis/

# Rename for consistency
mv backend/src/devarchai/analysis/parsers/terraform.py backend/src/devarchai/analysis/parsers/terraform_parser.py
mv backend/src/devarchai/analysis/rules/security.py backend/src/devarchai/analysis/rules/security_rules.py
```

---

### Phase 4: Workers & Celery Integration (Week 7-8)

**Goal:** Replace in-memory workers with Celery

#### Day 1-2: Celery Setup
```python
# File: backend/src/devarchai/workers/celery_app.py
from celery import Celery
from app.config import settings

celery_app = Celery(
    'devarchai',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['devarchai.workers.tasks.scan_tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
```

#### Day 3-4: Celery Tasks
```python
# File: backend/src/devarchai/workers/tasks/scan_tasks.py
from celery import states
from devarchai.workers.celery_app import celery_app
from devarchai.services.scan_service import ScanService
from devarchai.db.session import get_session_factory

@celery_app.task(bind=True, max_retries=3)
def execute_scan(self, scan_id: int):
    try:
        session_factory = get_session_factory()
        with session_factory() as db:
            scan_service = ScanService(db=db)
            # Execute scan logic
    except Exception as exc:
        raise self.retry(exc=exc)
```

#### Day 5-7: Frontend Components
```bash
# Reorganize frontend components
mkdir -p frontend/src/components/{ui,layout,auth,dashboard,repositories,scans,findings,reports}

# Move and split components
mv frontend/src/components/Layout.tsx frontend/src/components/layout/app-layout.tsx
mv frontend/src/components/ui.tsx frontend/src/components/ui/
```

---

### Phase 5: Frontend Pages & Integration (Week 9-10)

**Goal:** Complete frontend pages and integration

#### Day 1-3: Create Missing Pages
```bash
# Create auth pages
mkdir -p frontend/src/pages/auth
touch frontend/src/pages/auth/{login,register,forgot-password}-page.tsx

# Create settings page
mkdir -p frontend/src/pages/settings
touch frontend/src/pages/settings/settings-page.tsx
```

#### Day 4-5: State Management
```typescript
// File: frontend/src/stores/auth-store.ts
import { create } from 'zustand';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('access_token'),
  login: (token) => {
    localStorage.setItem('access_token', token);
    set({ token });
  },
  logout: () => {
    localStorage.removeItem('access_token');
    set({ token: null, user: null });
  },
}));
```

#### Day 6-7: Testing & Polish
- Test all user flows
- Fix TypeScript errors
- Add loading states
- Add error boundaries

---

### Phase 6: Testing & Deployment (Week 11-12)

**Goal:** Comprehensive testing and deployment preparation

#### Day 1-3: Backend Testing
```bash
# Run tests
cd backend
pytest tests/unit -v
pytest tests/integration -v

# Check coverage
pytest --cov=src/devarchai --cov-report=html
```

#### Day 4-5: Frontend Testing
```bash
# Run tests
cd frontend
npm run test
npm run build

# Check types
npx tsc --noEmit
```

#### Day 6-7: Deployment Prep
```bash
# Update Docker configuration
# Add health checks
# Configure environment variables
# Set up monitoring
```

---

## 7. Post-Migration Checklist

### Backend
- [ ] All imports updated to `devarchai` namespace
- [ ] Database migrations run successfully
- [ ] RLS policies tested
- [ ] Celery workers processing tasks
- [ ] Rate limiting active
- [ ] Authentication working (JWT + API key)
- [ ] Organization CRUD operations working
- [ ] All API endpoints responding

### Frontend
- [ ] Build completes without errors
- [ ] All routes working
- [ ] Authentication flow working
- [ ] API interceptors handling errors
- [ ] All pages implemented (no placeholders)
- [ ] TypeScript compilation successful
- [ ] Responsive design tested

### Infrastructure
- [ ] Docker Compose starts all services
- [ ] Health checks passing
- [ ] Database backups configured
- [ ] Monitoring dashboards set up
- [ ] CI/CD pipeline updated

---

## 8. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during migration | High | Backup database before migration |
| Downtime during cutover | Medium | Use blue-green deployment |
| Breaking existing API | High | Maintain backward-compatible endpoints |
| Celery configuration issues | Medium | Test thoroughly in staging |
| Frontend breaking changes | Medium | Feature flag new UI |

---

## 9. Success Metrics

- ✅ Zero data loss during migration
- ✅ < 5 minutes downtime during cutover
- ✅ All existing API endpoints still functional
- ✅ Celery processing 100+ scans/hour
- ✅ Frontend build time < 60 seconds
- ✅ API response time p95 < 500ms
- ✅ Zero critical security vulnerabilities

---

## Conclusion

This migration plan transforms DevArchAI from a prototype into a production-ready SaaS platform over 12 weeks. The key milestones are:

1. **Week 2:** Multi-tenancy foundation complete
2. **Week 4:** API layer reorganized with middleware
3. **Week 6:** Analysis domain consolidated
4. **Week 8:** Celery workers replacing in-memory pool
5. **Week 10:** Frontend complete with all pages
6. **Week 12:** Production deployment ready

Each phase includes testing to ensure stability. Backward compatibility is maintained where possible to avoid breaking existing integrations.
