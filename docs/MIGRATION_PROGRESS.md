# DevArchAI - Architecture Migration Progress

**Last Updated:** March 6, 2026  
**Status:** Phase 1 Complete - Foundation & Multi-Tenancy

---

## Migration Progress Summary

### ✅ Phase 1: Foundation & Multi-Tenancy (COMPLETE)

#### Backend Structure Created

```
backend/src/devarchai/
├── __init__.py                    ✅ Created
├── main.py                        ✅ Created (FastAPI app factory)
├── config.py                      ✅ Created (Enhanced with all settings)
│
├── api/
│   ├── __init__.py                ✅ Created
│   ├── deps.py                    ✅ Created (FastAPI dependencies)
│   ├── middleware/                📁 Created (empty - to implement)
│   └── v1/
│       ├── router.py              ✅ Created
│       └── endpoints/
│           ├── __init__.py        ✅ Created
│           ├── auth.py            ✅ Created (with org creation)
│           ├── health.py          ✅ Created
│           ├── organizations.py   ✅ Created (full CRUD)
│           ├── repositories.py    ✅ Created (stubs)
│           ├── scans.py           ✅ Created (stubs)
│           ├── findings.py        ✅ Created (stubs)
│           ├── reports.py         ✅ Created (stubs)
│           ├── dashboard.py       ✅ Created (stubs)
│           └── billing.py         ✅ Created (stubs)
│
├── core/
│   ├── __init__.py                ✅ Created
│   ├── security.py                ✅ Created (JWT + API keys)
│   ├── exceptions.py              ✅ Created (comprehensive)
│   └── logging.py                 ✅ Created (structlog)
│
├── db/
│   ├── __init__.py                ✅ Created
│   ├── base.py                    ✅ Created (SQLAlchemy base)
│   └── session.py                 ✅ Created (async session)
│
├── models/
│   ├── __init__.py                ✅ Created
│   ├── base.py                    📁 To create
│   ├── mixins/
│   │   └── __init__.py            ✅ Created
│   ├── user.py                    ✅ Created (with org membership)
│   ├── organization.py            ✅ Created (multi-tenancy core)
│   ├── project.py                 ✅ Created
│   ├── repository.py              ✅ Created (with org_id)
│   ├── scan.py                    ✅ Created (with org_id)
│   ├── finding.py                 ✅ Created (with org_id)
│   ├── report.py                  ✅ Created (with org_id)
│   ├── subscription.py            ✅ Created
│   └── audit_log.py               ✅ Created
│
├── schemas/
│   ├── __init__.py                ✅ Created
│   ├── common.py                  ✅ Created
│   ├── auth.py                    ✅ Created
│   └── organization.py            ✅ Created
│
├── services/
│   └── (to migrate from app/services)
│
├── analysis/
│   └── (to migrate from app/parsers, app/rules, etc.)
│
├── workers/
│   ├── __init__.py                ✅ Created
│   ├── celery_app.py              ✅ Created (Celery config)
│   └── tasks/
│       ├── __init__.py            ✅ Created
│       ├── scan_tasks.py          ✅ Created
│       ├── report_tasks.py        ✅ Created
│       └── email_tasks.py         ✅ Created
│
└── integrations/
    └── (to implement)
```

#### Frontend Structure Created

```
frontend/src/
├── app/                           📁 Created (empty)
├── api/
│   ├── client.ts                  ✅ Created (axios with interceptors)
│   └── endpoints/
│       ├── index.ts               ✅ Created
│       ├── auth.ts                ✅ Created
│       ├── organizations.ts       ✅ Created
│       ├── scans.ts               ✅ Created
│       ├── reports.ts             ✅ Created
│       └── dashboard.ts           ✅ Created
│
├── components/
│   ├── ui/                        📁 Created (empty)
│   ├── layout/                    📁 Created (empty)
│   ├── auth/                      📁 Created (empty)
│   ├── dashboard/                 📁 Created (empty)
│   ├── repositories/              📁 Created (empty)
│   ├── scans/                     📁 Created (empty)
│   ├── findings/                  📁 Created (empty)
│   ├── reports/                   📁 Created (empty)
│   ├── billing/                   📁 Created (empty)
│   └── settings/                  📁 Created (empty)
│
├── pages/
│   ├── auth/                      📁 Created (empty)
│   ├── dashboard/                 📁 Created (empty)
│   ├── projects/                  📁 Created (empty)
│   ├── repositories/              📁 Created (empty)
│   ├── scans/                     📁 Created (empty)
│   ├── findings/                  📁 Created (empty)
│   ├── reports/                   📁 Created (empty)
│   ├── billing/                   📁 Created (empty)
│   └── settings/                  📁 Created (empty)
│
├── hooks/                         📁 Created (empty)
├── stores/                        📁 Created (empty)
├── types/                         📁 Created (empty)
├── utils/                         📁 Created (empty)
└── assets/                        📁 Created (empty)
```

---

## What's Working Now

### Backend

1. **New Application Structure**
   - FastAPI app factory in `src/devarchai/main.py`
   - Enhanced configuration with all SaaS settings
   - Proper logging with structlog

2. **Multi-Tenancy Models**
   - Organization model with plan tracking
   - OrganizationMember for user-org relationships
   - All resource models updated with `organization_id`
   - Row-level security ready (needs DB migration)

3. **Authentication**
   - JWT tokens (access + refresh)
   - API key support for enterprise
   - User registration creates organization automatically
   - Token refresh endpoint

4. **Organization Management**
   - Create organization
   - List user's organizations
   - Get/update organization
   - Member listing
   - Member invite (stub)
   - Member remove

5. **Celery Configuration**
   - Celery app configured
   - Scan tasks defined
   - Report tasks defined
   - Email tasks defined

### Frontend

1. **API Client**
   - Axios instance with base URL
   - Request interceptor (auth token, org ID)
   - Response interceptor (401 handling, token refresh)
   - Automatic redirect to login on auth failure

2. **API Endpoints**
   - Auth endpoints (login, register, profile)
   - Organization endpoints (CRUD, members)
   - Scan endpoints (list, create, cancel)
   - Report endpoints (list, get, download)
   - Dashboard endpoints (summary, trends)

---

## What Needs to Be Done

### Phase 2: API Layer & Services (IN PROGRESS)

- [ ] Move existing services to new structure
- [ ] Implement repository pattern
- [ ] Create service layer for business logic
- [ ] Add rate limiting middleware
- [ ] Add request logging middleware
- [ ] Implement exception handlers

### Phase 3: Analysis Domain Migration

- [ ] Move parsers to `analysis/parsers/`
- [ ] Move rules to `analysis/rules/`
- [ ] Move scoring to `analysis/scoring/`
- [ ] Move AI engine to `analysis/ai/`
- [ ] Create analysis pipeline orchestrator

### Phase 4: Frontend Implementation

- [ ] Move existing components to new structure
- [ ] Implement auth pages (login, register)
- [ ] Implement organization selection
- [ ] Implement dashboard page
- [ ] Implement scans page
- [ ] Implement reports page
- [ ] Add Zustand stores
- [ ] Add custom hooks

### Phase 5: Database Migrations

- [ ] Create Alembic migration for organizations
- [ ] Create migration for organization_members
- [ ] Add organization_id to existing tables
- [ ] Enable row-level security
- [ ] Create RLS policies

### Phase 6: Integration & Testing

- [ ] Wire up Celery workers
- [ ] Test scan execution flow
- [ ] Test multi-tenancy isolation
- [ ] Test authentication flow
- [ ] End-to-end testing

---

## Files to Preserve from Old Structure

These files from `backend/app/` need to be migrated:

### Services
- [ ] `app/services/analysis.py` → `src/devarchai/analysis/pipeline.py`
- [ ] `app/services/scan_service.py` → `src/devarchai/services/scan_service.py`
- [ ] `app/services/github.py` → `src/devarchai/integrations/github/client.py`

### Parsers
- [ ] `app/parsers/base.py` → `src/devarchai/analysis/parsers/base.py`
- [ ] `app/parsers/terraform.py` → `src/devarchai/analysis/parsers/terraform_parser.py`
- [ ] `app/parsers/kubernetes.py` → `src/devarchai/analysis/parsers/kubernetes_parser.py`
- [ ] `app/parsers/dockerfile.py` → `src/devarchai/analysis/parsers/dockerfile_parser.py`
- [ ] `app/parsers/cicd.py` → `src/devarchai/analysis/parsers/cicd_parser.py`

### Rules
- [ ] `app/rules/base.py` → `src/devarchai/analysis/rules/base.py`
- [ ] `app/rules/registry.py` → `src/devarchai/analysis/rules/registry.py`
- [ ] `app/rules/security.py` → `src/devarchai/analysis/rules/security_rules.py`
- [ ] `app/rules/scalability.py` → `src/devarchai/analysis/rules/scalability_rules.py`
- [ ] `app/rules/reliability.py` → `src/devarchai/analysis/rules/reliability_rules.py`
- [ ] `app/rules/cost.py` → `src/devarchai/analysis/rules/cost_rules.py`
- [ ] `app/rules/observability.py` → `src/devarchai/analysis/rules/observability_rules.py`

### Scoring
- [ ] `app/scoring/engine.py` → `src/devarchai/analysis/scoring/engine.py`

### AI
- [ ] `app/ai_engine/explanation_engine.py` → `src/devarchai/analysis/ai/explanation_engine.py`

### Existing Routes (for backward compatibility)
- Keep `app/api/v1/routes/` temporarily
- Create redirect wrappers in new endpoints
- Deprecate after migration complete

---

## Quick Start (New Structure)

### Backend

```bash
cd backend

# Set Python path to include new structure
export PYTHONPATH=/home/lokesh/AI-Engine/DevArchAI/backend/src:$PYTHONPATH

# Run with uvicorn
uvicorn devarchai.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies (if needed)
npm install

# Run development server
npm run dev
```

---

## Testing the New Structure

### Test Authentication

```bash
# Register new user (creates org automatically)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "securepassword123",
    "organization_name": "Test Org"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepassword123"
  }'
```

### Test Organizations

```bash
# Get current user's org (requires auth token)
curl -X GET http://localhost:8000/api/v1/organizations/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# List organizations
curl -X GET http://localhost:8000/api/v1/organizations \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Next Steps

1. **Immediate:**
   - Test the new authentication endpoints
   - Verify organization creation on registration
   - Test multi-tenancy with multiple users

2. **This Week:**
   - Migrate scan_service.py
   - Migrate analysis pipeline
   - Wire up Celery for background scans

3. **Next Week:**
   - Complete frontend auth pages
   - Implement organization switcher
   - Connect dashboard to real data

---

## Notes

- The old `app/` structure is preserved for reference
- All new code goes in `src/devarchai/`
- Migration is incremental - both can coexist temporarily
- Use `PYTHONPATH` to switch between old and new structure during migration
