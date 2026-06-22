# Security Audit Report: Data Isolation Vulnerabilities

**Date:** 2026-06-20  
**Scope:** Authorization and data filtering across all API endpoints  
**Goal:** Prevent users from viewing other users' scan results, findings, reports, and dashboard data

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH     | 5  |
| MEDIUM   | 6  |
| LOW      | 3  |

---

## CRITICAL Vulnerabilities

### C-1: `GET /api/v1/findings/{finding_id}` — Ownership check uses wrong variable

**File:** `backend/app/api/v1/routes/findings.py:173`

**Bug:** Line 173 references `result` instead of `scan_result`:

```python
# Line 155-158: finding query
result = await db.execute(select(Finding).where(Finding.id == finding_uuid))
finding = result.scalar_one_or_none()

# Line 166-172: scan ownership query
scan_result = await db.execute(
    select(Scan).where(Scan.id == finding.scan_id, Scan.user_id == current_user.id)
)
scan = result.scalar_one_or_none()  # BUG: should be scan_result, not result
```

Since `result` still holds the `Finding` result (which is truthy), the `if not scan` check on line 175 **never fails**. Any authenticated user can retrieve any finding by ID regardless of ownership.

**Impact:** Total data leak of all findings across all users.

---

## HIGH Vulnerabilities

### H-1: `GET /api/v1/scans/{scan_id}` — No ownership check for unauthenticated users

**File:** `backend/app/api/v1/routes/scans.py:128`

**Current logic (lines 140-143):** When `current_user` is authenticated, query filters by `Scan.user_id == current_user.id`. But when `current_user is None` (no auth), **no filter is applied** — any scan can be retrieved by ID.

**Impact:** An unauthenticated user can enumerate scan IDs and retrieve detailed scan results including scores, status, and metadata of any user's scans.

### H-2: `GET /api/v1/scans/{scan_id}/progress` — No ownership check for unauthenticated users

**File:** `backend/app/api/v1/routes/scans.py:212`

**Current logic (lines 221-224):** Same issue as H-1. When `current_user is None`, any scan's progress can be retrieved.

**Impact:** Attackers can monitor active scans and extract progress/status information for any scan.

### H-3: `GET /api/v1/suggestions/{suggestion_id}` — No ownership check

**File:** `backend/app/api/v1/routes/ai_suggestions.py:174`

**Current logic:** Queries `AISuggestion` directly by ID without verifying the suggestion belongs to a scan owned by the current user.

**Impact:** Any authenticated user can view any AI suggestion by ID, including fix code and detailed analysis.

### H-4: `POST /api/v1/suggestions/generate/{finding_id}` — No ownership check

**File:** `backend/app/api/v1/routes/ai_suggestions.py:353`

**Current logic:** Queries `Finding` by ID without verifying the finding belongs to a scan owned by the current user.

**Impact:** Any authenticated user can trigger AI suggestion generation on any finding by ID.

### H-5: `POST /api/v1/public/status/{scan_id}` — Returns any scan's status

**File:** `backend/app/api/v1/routes/public_scans.py:278`

**Current logic:** This public endpoint (no auth required) queries `Scan` by ID without any user_id filter. It returns status, progress, and completion data for any scan, including authenticated users' scans.

**Impact:** Attackers can probe any scan ID to extract real-time status and metadata.

---

## MEDIUM Vulnerabilities

### M-1: `GET /api/v1/suggestions/{suggestion_id}/apply` — No ownership check

**File:** `backend/app/api/v1/routes/ai_suggestions.py:214`

Queries suggestion by ID without verifying user owns the associated scan.

### M-2: `GET /api/v1/suggestions/{suggestion_id}/create-pr` — No ownership check

**File:** `backend/app/api/v1/routes/ai_suggestions.py:270`

Queries suggestion by ID without ownership check. Also queries scan by ID (line 280) without ownership check.

### M-3: `POST /api/v1/suggestions/{suggestion_id}/ignore` — No ownership check

**File:** `backend/app/api/v1/routes/ai_suggestions.py:322`

Queries suggestion by ID without ownership check.

### M-4: `POST /api/v1/suggestions/{suggestion_id}/mark-fixed` — No ownership check

**File:** `backend/app/api/v1/routes/ai_suggestions.py:341`

Queries suggestion by ID without ownership check.

### M-5: `POST /api/v1/suggestions/{suggestion_id}/copy-fix` — No ownership check

**File:** `backend/app/api/v1/routes/ai_suggestions.py:454`

Queries suggestion by ID without ownership check.

### M-6: `POST /api/v1/suggestions/{suggestion_id}/rescan` — No ownership check

**File:** `backend/app/api/v1/routes/ai_suggestions.py:494`

Queries suggestion by ID without ownership check. Also queries scan by ID (line 501) without ownership check.

---

## LOW Vulnerabilities

### L-1: `GET /api/v1/analyze/repo/list` — Returns all analyses for all users

**File:** `backend/app/api/v1/routes/repo_analysis.py:259`

No user filter — returns `RepoAnalysis` entries for all users. The `RepoAnalysis` model has no `user_id` column, so user-based filtering is not possible without a schema migration.

### L-2: `GET /api/v1/analyze/repo/{analysis_id}` — No ownership check

**File:** `backend/app/api/v1/routes/repo_analysis.py:309`

No user filter. Any user can view any analysis result.

### L-3: `GET /api/v1/analyze/repo/{analysis_id}/best-practices` — No ownership check

**File:** `backend/app/api/v1/routes/repo_analysis.py:380`

No user filter. Any user can view any analysis's best practices.

---

## Endpoints Verified as Secure

| Endpoint | File | Reason |
|----------|------|--------|
| `GET /api/v1/scans` | scans.py:82 | Filters by `Scan.user_id == current_user.id` |
| `POST /api/v1/scans` | scans.py:408 | Creates scan with `user_id=current_user.id` |
| `POST /api/v1/scans/{scan_id}/cancel` | scans.py:259 | Filters by `Scan.user_id == current_user.id` |
| `GET /api/v1/scans/{scan_id}/findings` | scans.py:305 | Checks `scan.user_id == current_user.id` (ownership check) |
| `GET /api/v1/findings` | findings.py:21 | Filters by scan IDs scoped to `Scan.user_id == current_user.id` |
| `GET /api/v1/dashboard/*` | dashboard.py | All endpoints filter by `Scan.user_id == current_user.id` |
| `GET /api/v1/reports` | reports.py:116 | Joins with Scan and filters by `Scan.user_id == current_user.id` |
| `GET /api/v1/reports/scan/{scan_id}/latest` | reports.py:150 | Filters by `Scan.user_id == current_user.id` |
| `GET /api/v1/reports/{report_id}` | reports.py:176 | Uses `_get_owned_report` with user_id |
| `GET /api/v1/reports/{scan_id}/download` | reports.py:195 | Uses `_get_accessible_scan_for_download` with ownership check |
| `GET /api/v1/reports/{report_id}/summary` | reports.py:264 | Uses `_get_owned_report` with user_id |
| `DELETE /api/v1/reports/{report_id}` | reports.py:292 | Uses `_get_owned_report` with user_id |
| `GET /api/v1/suggestions` | ai_suggestions.py:36 | Filters by scan IDs scoped to `Scan.user_id == current_user.id` |
| `GET /api/v1/suggestions/{scan_id}` | ai_suggestions.py:139 | Checks `scan.user_id == current_user.id` |
| `GET /api/v1/repositories` | repositories.py:99 | Filters by `Repository.user_id == current_user.id` |
| `GET /api/v1/repositories/{repo_id}` | repositories.py:207 | Filters by `Repository.user_id == current_user.id` |
| `PUT /api/v1/repositories/{repo_id}` | repositories.py:234 | Filters by `Repository.user_id == current_user.id` |
| `DELETE /api/v1/repositories/{repo_id}` | repositories.py:272 | Filters by `Repository.user_id == current_user.id` |
| `POST /api/v1/repositories/{repo_id}/scan` | repositories.py:302 | Filters by `Repository.user_id == current_user.id` |
| `GET /api/v1/scan/status/{scan_id}` | unified_scan.py:322 | Checks `scan.user_id == current_user.id` |
| `GET /api/v1/scan/results/{scan_id}` | unified_scan.py:405 | Checks `scan.user_id == current_user.id` |
| `POST /api/v1/scan/start` | unified_scan.py:141 | Creates scan with `user_id=current_user.id` |

---

## Data Flow Analysis

### Scan Ownership Chain

```
User → Scan → Finding
   ↓       ↓
Repository  Report
   ↓
      AISuggestion
```

Every piece of data traces back to a `Scan`. The `Scan.user_id` field is the single source of truth for ownership. Any endpoint that returns scan-related data must verify it reaches a scan owned by the requesting user.

### Missing WHERE Clauses

| Table | Endpoint | Missing Filter |
|-------|----------|----------------|
| `Scan` | `GET /scans/{id}` | `WHERE Scan.user_id = current_user.id OR Scan.user_id IS NULL` (unauthenticated case) |
| `Scan` | `GET /scans/{id}/progress` | `WHERE Scan.user_id = current_user.id` (unauthenticated case) |
| `Scan` | `GET /public/status/{id}` | `WHERE Scan.user_id IS NULL` (should only expose anonymous scans) |
| `AISuggestion` | All `GET/POST /suggestions/{id}/*` | Must join through Scan to verify ownership |
| `RepoAnalysis` | `GET /analyze/repo/list` | No user_id column exists — requires schema change |

### JOIN Leaks

- `repositories.py:list_repositories` (lines 155-158): Queries findings by `Finding.scan_id == latest_scan.id` without filtering by user. Since `latest_scan` was obtained from a user-scoped query (`Scan.repository_id == repo.id` where `repo` was filtered by user), this is indirectly scoped — but it's fragile and relies on the scan belonging to the user. This is a moderate risk if a scan's repository_id is tampered with.

---

## Recommendations

### Immediate Fixes (implemented below)

| # | File | Fix |
|---|------|-----|
| 1 | `findings.py:173` | Change `result` → `scan_result` |
| 2 | `scans.py:get_scan` | Add check: if `current_user is None` and `scan.user_id is not None`, return 403 |
| 3 | `scans.py:get_scan_progress` | Add check: if `current_user is None` and `scan.user_id is not None`, return 403 |
| 4 | `ai_suggestions.py:get_suggestion` | Add helper: verify suggestion's scan belongs to current_user |
| 5 | `ai_suggestions.py:apply_fix` | Add ownership check before acting on suggestion |
| 6 | `ai_suggestions.py:create_pr` | Add ownership check before acting on suggestion |
| 7 | `ai_suggestions.py:ignore_suggestion` | Add ownership check before acting on suggestion |
| 8 | `ai_suggestions.py:mark_fixed` | Add ownership check before acting on suggestion |
| 9 | `ai_suggestions.py:generate_suggestion` | Add ownership check on finding before generating suggestion |
| 10 | `ai_suggestions.py:copy_fix` | Add ownership check before acting on suggestion |
| 11 | `ai_suggestions.py:rescan_after_fix` | Add ownership check before acting on suggestion |
| 12 | `public_scans.py:get_scan_status` | Add check: only return scans with `Scan.user_id IS NULL` |

### Recommended Follow-ups

| # | Issue | Mitigation |
|---|-------|------------|
| A | `RepoAnalysis` model has no `user_id` | Add `user_id` column and DB migration, update `list_analyses`, `get_analysis`, `get_missing_best_practices`, `delete_analysis` to filter by user |
| B | Unified scan `/scan/start` creates scan with `id=uuid4()` then overwrites `scan_id` | Ensure `scan.id` and `scan_id` are consistent from creation |
| C | `repositories.py:list_repositories` queries findings with indirect scoping | Add explicit `Scan.user_id == current_user.id` in findings subquery |
| D | Rate limiting on public endpoints | Add rate limiting to `/public/status/{scan_id}` to prevent scan ID enumeration |
