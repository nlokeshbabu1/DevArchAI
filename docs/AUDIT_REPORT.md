# DevArchAI Platform Audit Report

**Date:** March 6, 2026  
**Auditor:** Senior SaaS Platform Architect

---

## Executive Summary

The DevArchAI platform has a **solid foundation** with working repository scanning, rule engine, and scoring system. However, several critical integrations are broken or missing, preventing AI suggestions from appearing in the UI.

---

## 🔴 Critical Issues

### 1. AI Explanations Not Being Generated

**Location:** `app/services/scan_service.py`, `app/ai_engine/explanation_engine.py`

**Problem:**
- `scan_service.py` imports from `app.rule_engine.base` but rules are in `app/rules/base.py`
- Wrong import path: `from app.rule_engine.base import RuleFinding`
- Should be: `from app.rules.base import RuleFinding`

**Impact:** AI explanations never get generated because the service can't import the correct classes.

**Fix Required:**
```python
# Change in scan_service.py
from app.rules.base import RuleFinding  # Correct path
from app.rules.registry import RuleRegistry  # If exists
```

### 2. Scan Service Uses Wrong Module Paths

**Location:** `app/services/scan_service.py`

**Current Imports (BROKEN):**
```python
from app.rule_engine.base import RuleFinding
from app.rule_engine.rule_runner import RuleRunner
from app.ai_engine.explanation_engine import ExplanationEngine
from app.scoring.engine import ScoringEngine
from app.utils.file_loader import FileLoader
from app.utils.repo_downloader import RepoDownloader
```

**Should Be:**
```python
from app.rules.base import RuleFinding
from app.rules.base import RuleRegistry  # Use registry from rules module
from app.ai_engine.explanation_engine import ExplanationEngine
from app.scoring.engine import ScoringEngine
# FileLoader and RepoDownloader need to be verified
```

### 3. Missing File Loader and Repo Downloader

**Location:** `app/utils/`

**Files Missing:**
- `app/utils/file_loader.py` - Does not exist
- `app/utils/repo_downloader.py` - Does not exist

**But We Have:**
- `app/utils/repository_scanner.py` - EXISTS and works

**Fix:** Update `scan_service.py` to use `RepositoryScanner` instead.

### 4. Celery Task Not Using New Task Module

**Location:** `app/workers/scan_worker.py` vs `app/workers/tasks/scan_repository.py`

**Problem:**
- API routes use old `execute_scan_background` from `app/workers/scan_worker.py`
- New Celery task exists in `app/workers/tasks/scan_repository.py` but is never called

**Fix:** Update API to use Celery task:
```python
from app.workers.tasks.scan_repository import scan_repository_task

# In endpoint:
result = scan_repository_task.delay(scan.id, scan.repository_url)
scan.celery_task_id = result.id
```

### 5. Rule Engine Module Path Confusion

**Location:** `app/rule_engine/` vs `app/rules/`

**Problem:**
- `app/rule_engine/` directory exists but is mostly empty
- `app/rules/` has all the actual rules
- `scan_service.py` tries to import from non-existent `app.rule_engine.rule_runner`

**Fix:** Either:
1. Delete `app/rule_engine/` and update imports to use `app/rules/`
2. Or move rules to `app/rule_engine/`

**Recommendation:** Use `app/rules/` (already populated with 31 rules)

---

## 🟡 High Priority Issues

### 6. Frontend Report Page Uses Mock Data

**Location:** `frontend/src/pages/Report.tsx`

**Problem:**
```typescript
const { data: report, isLoading } = useQuery({
  queryKey: ['report', id],
  queryFn: async () => {
    return { /* HARDCODED MOCK DATA */ }
  },
})
```

**Fix:** Replace with actual API call:
```typescript
import { reportsApi } from '@/api/endpoints/reports'

queryFn: async () => {
  return await reportsApi.getReport(id!)
},
```

### 7. Missing Authentication UI

**Location:** `frontend/src/pages/auth/`, `frontend/src/components/auth/`

**Problem:**
- Directories exist but are EMPTY
- Backend auth endpoints work (`/api/v1/auth/login`, `/api/v1/auth/register`)
- No way for users to log in

**Fix:** Create Login and Register pages.

### 8. No AI Fix Code Examples

**Location:** `app/ai_engine/llm_client.py`

**Problem:**
- LLM client generates explanations but NO code examples
- AI suggestions lack terraform/docker fix snippets

**Fix:** Enhance prompt to include code examples:
```python
prompt = f"""
Provide:
1. Explanation
2. Impact analysis
3. Remediation steps
4. CODE EXAMPLE (terraform/docker/kubernetes YAML)
"""
```

---

## 🟢 Medium Priority Issues

### 9. Scan Progress Not Shown in UI

**Location:** Frontend dashboard

**Problem:**
- Backend updates `scan.progress` field
- Frontend doesn't poll for progress

**Fix:** Add polling in scan component:
```typescript
const { data: scan } = useQuery({
  queryKey: ['scan', id],
  queryFn: () => scansApi.getScan(id),
  refetchInterval: (query) => {
    return query.state.data?.status === 'processing' ? 2000 : false
  },
})
```

### 10. API Response Missing AI Suggestions Field

**Location:** `app/api/v1/routes/scans.py`, `app/schemas/scan.py`

**Problem:**
- `ScanResponse` schema doesn't include `ai_suggestions` field
- Findings have `ai_explanation` but it's not exposed properly

**Fix:** Update schema:
```python
class ScanResponse(BaseModel):
    id: int
    status: str
    progress: int
    overall_score: float
    findings: List[FindingResponse]
    ai_suggestions: List[AISuggestion]  # ADD THIS
```

---

## ✅ What's Working

1. ✅ Repository Scanner (`app/utils/repository_scanner.py`)
2. ✅ File Parsers (Dockerfile, Terraform, Kubernetes, CI/CD)
3. ✅ Rule Engine (31 rules across 5 categories)
4. ✅ Scoring Engine
5. ✅ Database Models
6. ✅ Celery Configuration
7. ✅ API Endpoints (mostly)
8. ✅ Frontend Dashboard UI (design is good)

---

## 📋 Files Requiring Modification

| File | Issue | Priority |
|------|-------|----------|
| `app/services/scan_service.py` | Wrong imports, missing modules | 🔴 Critical |
| `app/api/v1/routes/scans.py` | Not using Celery tasks | 🔴 Critical |
| `app/schemas/scan.py` | Missing AI suggestions | 🟡 High |
| `frontend/src/pages/Report.tsx` | Mock data instead of API | 🟡 High |
| `frontend/src/pages/auth/` | Empty (create pages) | 🟡 High |
| `app/ai_engine/llm_client.py` | No code examples in prompts | 🟡 High |
| `app/workers/scan_worker.py` | Replace with Celery tasks | 🟡 High |

---

## 🛠️ Required Fixes (In Order)

### Phase 1: Backend (Critical)
1. Fix imports in `scan_service.py`
2. Update to use `RepositoryScanner`
3. Fix Celery task integration in API
4. Add AI code example generation

### Phase 2: API Response
1. Update `ScanResponse` schema
2. Add `ai_suggestions` field
3. Include code examples in response

### Phase 3: Frontend
1. Create Login page
2. Create Register page
3. Fix Report page to use real API
4. Add AI recommendations section
5. Add scan progress polling

---

## 📊 Impact Assessment

| Feature | Current State | After Fix |
|---------|--------------|-----------|
| Repository Scanning | ✅ Works | ✅ Works |
| File Detection | ✅ Works | ✅ Works |
| Rule Evaluation | ✅ Works | ✅ Works |
| AI Explanations | ❌ Broken | ✅ Works |
| AI Code Examples | ❌ Missing | ✅ Works |
| Auth UI | ❌ Missing | ✅ Works |
| Real-time Progress | ❌ Missing | ✅ Works |
| Dashboard Data | ⚠️ Mock | ✅ Real API |

---

## Next Steps

1. **Immediate:** Fix `scan_service.py` imports
2. **Today:** Update API to use Celery tasks
3. **Tomorrow:** Create auth UI
4. **This Week:** Fix frontend to use real data
