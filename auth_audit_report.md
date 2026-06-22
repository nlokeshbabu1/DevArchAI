# Authentication & Authorization Audit Report

## Summary

Audit of OAuth user identity mapping, frontend state management, and tenant isolation across backend API endpoints and frontend React state.

**Severity Breakdown**: 1 CRITICAL, 3 HIGH, 1 MEDIUM, 1 LOW

---

## 1. [CRITICAL] GitLab OAuth user duplicate on email change

**Files**: `backend/app/api/v1/routes/gitlab_auth.py:214-216`  
**Type**: Identity Mapping

The GitLab OAuth callback looks up existing users only by `email_hash`:

```python
result = await db.execute(select(User).where(User.email_hash == email_hash))
user = result.scalar_one_or_none()
```

If a GitLab user changes their email on GitLab and logs in again, `email_hash` won't match any existing user. A **new User row** is created with the same `gitlab_id` — producing duplicate accounts. The original user's scans, findings, and repositories remain orphaned under the old account.

**Fix**: Look up by `gitlab_id` first (exact identity match), then by `email_hash`. When found by email hash, backfill `gitlab_id`.

---

## 2. [HIGH] React Query cache persists across user sessions

**Files**:
- `frontend/src/lib/api.ts:68-85` — interceptor reads token from localStorage
- `frontend/src/stores/auth-store.ts:82-92` — `login()` does not clear query cache
- `frontend/src/pages/Dashboard.tsx:102-139` — queries have `staleTime: 0` but return stale cached data while refetching

**Type**: Cross-User Data Leakage (visual + potential)

When User A logs in, then User B logs in via GitLab from the **same browser tab** (no full page reload):

1. `GitlabCallback.tsx` stores new token and calls `login()` + `navigate('/dashboard')`
2. Dashboard mounts — React Query has stale cached data from User A's session
3. With `staleTime: 0`, React Query **returns the stale User A data immediately** while refetching in the background
4. For ~100-500ms, User B sees User A's dashboard data (repos, scores, finding counts)

The API interceptor reads from `localStorage` which was updated by `GitlabCallback.tsx`, so the refetch uses the correct token. But the **visual flash** of stale data is a data exposure.

**Fix**: Call `queryClient.clear()` in `GitlabCallback.tsx` (and `GithubCallback.tsx`, `Login.tsx`, `Register.tsx`) after `login()` completes, before navigating to dashboard.

---

## 3. [HIGH] Repository import modal always shows GitLab as "Connect" (unconnected)

**Files**:
- `frontend/src/pages/repositories/RepositoriesPage.tsx:515-519` — hardcoded `connected: false`
- `backend/app/api/v1/routes/auth.py:73-90` — `user_to_response` missing provider status
- `backend/app/api/v1/routes/gitlab_auth.py:73-84` — same

**Type**: Frontend UX / Capability

The integration cards on the Repositories page hardcode GitLab as disconnected:

```tsx
{ name: 'GitLab', icon: Gitlab, connected: false },
```

When a GitLab OAuth user visits this page, they see "Connect" for GitLab even though they are already authenticated. The "Import Repository" modal shows "GitHub not connected" errors because it only handles GitHub repos.

**Fix**:
1. Add `has_gitlab` field to `user_to_response()` in both `auth.py` and `gitlab_auth.py`
2. Update `RepositoriesPage.tsx` to derive `gitlabConnected` from user data
3. Show appropriate messaging in the import modal for GitLab-connected users

---

## 4. [HIGH] User identity mapping — `/_safe_email` fallback hides broken identity

**Files**:
- `backend/app/api/v1/routes/auth.py:58-70` — `_safe_email` in auth.py
- `backend/app/api/v1/routes/gitlab_auth.py:59-70` — `_safe_email` in gitlab_auth.py
- `backend/app/core/encryption.py:25-27` — Fernet key derivation from `SECRET_KEY`

**Type**: Identity Mapping / Configuration

`_safe_email()` returns `username@email.local` when email decryption fails. This happens if `ENCRYPTION_KEY` is not set and `SECRET_KEY` changes between app restarts (which is the default in development mode — `settings.py` generates a random `SECRET_KEY` if none is provided).

When the email falls back, every user endpoint and JWT claim reports `username@email.local` — breaking identity resolution, email notifications, and user recognition.

**Root cause**: `EncryptionService.__init__` in `encryption.py:25-27` derives the Fernet key from `SECRET_KEY` if `ENCRYPTION_KEY` is not set:
```python
if not self.key:
    derived = base64.urlsafe_b64encode(
        hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    )
```

**Fix**: Log a startup warning if `ENCRYPTION_KEY` is not set. Add `ENCRYPTION_KEY` to the default `.env.example` with a strong random default. Document that changing it invalidates all stored encrypted data.

---

## 5. [MEDIUM] Auth store persist + direct localStorage dual-write inconsistency

**Files**:
- `frontend/src/pages/auth/GitlabCallback.tsx:26-29` — sets localStorage directly
- `frontend/src/stores/auth-store.ts:82-92` — `login()` sets token in Zustand state (persisted)
- `frontend/src/lib/api.ts:70` — interceptor reads from localStorage

**Type**: State Management

The auth token is stored in two places:
1. Zustand persisted store (`auth-storage` localStorage key) via `login()`
2. Direct `localStorage.setItem('access_token', ...)` in `GitlabCallback.tsx`

The API interceptor reads from `localStorage`, not the Zustand store. If any code path changes the token in the store without also updating `localStorage`, the API interceptor uses a stale/missing token.

**Fix**: Unify storage: let the Zustand persist middleware be the single source of truth. Add a Zustand subscription that syncs `token` to `localStorage` for the API interceptor.

---

## 6. [LOW] No startup validation of encryption key consistency

**File**: `backend/app/core/encryption.py`  
**Type**: Configuration

There's no startup check that the encryption key can decrypt existing data. If `SECRET_KEY` or `ENCRYPTION_KEY` changes, the first user registration encrypts with the new key, but existing encrypted emails become undecipherable. The only indication is a `logger.warning` in `_safe_email`.

**Fix**: Add a startup health check that attempts to re-encrypt a known value and verify round-trip integrity.

---

## Root Cause Map

```
User A logs in via GitLab
  → Creates user with encrypted email (Key K1)
  → Dashboard caches queries
User A continues working
  → Data isolated (JWT + user_id filtering)
User B logs in via GitLab (same browser, no full reload)
  → GitLab OAuth: lookup by email_hash only [CRITICAL #1]
    → If email changed: DUPLICATE user created
  → Frontend: localStorage updated, login() called [MEDIUM #5]
    → Zustand store updated, but React Query cache NOT cleared
  → Dashboard mounts: stale User A data displayed [HIGH #2]
    → Refetch with User B token → correct data appears
  → Repositories page: GitLab shows "Connect" [HIGH #3]
  → User profile: _safe_email falls back [HIGH #4]
    → Breaks identity if ENCRYPTION_KEY changed
```

## Fix Priority Order

1. **#1**: GitLab OAuth identity lookup (prevents duplicates, fixes mapping)
2. **#2**: Frontend query cache invalidation on login (prevents cross-user data flash)
3. **#3**: Repository import modal provider detection (fixes UX for GitLab users)
4. **#4**: Encryption key configuration guidance (prevents email fallback)
5. **#5**: Auth store / localStorage sync (prevents token drift)
6. **#6**: Encryption startup validation (preventative)
