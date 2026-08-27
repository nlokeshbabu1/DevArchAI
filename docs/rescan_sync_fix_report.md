# Rescan Synchronization Fix Report

## 1. Root Cause Analysis

### RC1: Event Loop Closed Prematurely in Background Thread

**File:** `backend/app/api/v1/routes/unified_scan.py` — `_run_scan_in_background()`

The background scan thread created a new event loop, ran initialization, then **closed the loop** before calling `SyncScanService.execute_scan()`. Every subsequent progress update called `_safe_await()` which had to create/destroy a new event loop for each call via `asyncio.run()`. This fragile pattern could silently fail, leaving the progress store stuck at an intermediate state.

**Impact:** Progress store updates silently fail → frontend polling keeps getting `status: "running"` forever → overlay stays on "Cloning Repository 0%".

### RC2: `_safe_await()` Silently Swallows All Exceptions

**File:** `backend/app/workers/tasks/scan_repository.py` — `_safe_await()` (line 89-93)

The outer `except Exception as e: logger.warning(...); return None` catches **any** error and returns `None`. When progress store updates fail (due to RC1 or other issues), the scan continues and DB is updated to `COMPLETED`, but the progress store never transitions to `"completed"`. The frontend polls indefinitely against a stale `"running"` status.

**Impact:** Progress store permanently stuck at `status: "running"` even though scan is `COMPLETED` in the database.

### RC3: Frontend Only Handles Subset of Backend Status Values

**File:** `frontend/src/hooks/useRepositoryScan.ts` (old code, lines 90-93)

The `startPolling()` callback checked only 4 status values:
```
isComplete: data.status === 'completed',
isFailed: data.status === 'failed',
isScanning: data.status === 'running' || data.status === 'pending'
```

But the backend `ScanStatus` enum uses 6 values: `pending`, `queued`, `processing`, `completed`, `failed`, `cancelled`. The progress store uses: `pending`, `running`, `completed`, `failed`.

If the progress store entry is missing and the DB fallback returns `status: "processing"`, no frontend condition matches:
- `isScanning = false` (wrong — scan IS running)
- `isComplete = false`
- `isFailed = false`

→ **Triple-false limbo state**. The overlay stays open but shows no progress.

### RC4: Polling Has No DB Fallback

**File:** `backend/app/api/v1/routes/unified_scan.py` — `get_scan_status()` (old code)

The polling endpoint returned progress store data directly. If the progress store had a stale `"running"` entry (from RC1/RC2), it was returned as-is. The DB status was only consulted when the progress store had **no** entry at all — never as a cross-check for stale entries.

### RC5: No Watchdog Timeout in Frontend

**File:** `frontend/src/hooks/useRepositoryScan.ts` (old code)

The frontend had no mechanism to detect stuck progress. If progress didn't move and status never became `"completed"` or `"failed"`, polling continued indefinitely with no timeout or fallback.

### RC6: WebSocket Completion Event May Not Reach Client

**File:** `backend/app/workers/tasks/scan_repository.py` — `execute_scan()` completion broadcast

`broadcast_progress(status="completed")` sends `type: "scan_complete"` via WebSocket. But if `_safe_await()` fails (RC1/RC2), the broadcast never happens. Even if it works, WebSocket is unreliable — reconnection (3 retries with exponential backoff) may exhaust retries before the single completion event fires.

---

## 2. Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/app/api/v1/routes/unified_scan.py` | **Fix** | Keep event loop alive in `_run_scan_in_background`; pass persistent loop to `SyncScanService`; rewrite `get_scan_status` with DB-fallback-first logic |
| `backend/app/workers/tasks/scan_repository.py` | **Fix** | Add `event_loop` param to `SyncScanService`; add `_exec_async()` wrapper; improve `_safe_await()` with persistent loop support and better error logging |
| `backend/app/services/scan_progress_store.py` | **Fix** | Add `_cleanup_scan()` method; add `_last_progress` tracking for staleness detection |
| `frontend/src/hooks/useRepositoryScan.ts` | **Fix** | Complete rewrite: handle all backend status values, add 30s watchdog timer, add DB fallback on timeout, add debug logging |
| `frontend/src/pages/repositories/RepositoryResultsPage.tsx` | **Fix** | Don't close overlay on completion; include `isComplete`/`isFailed` in overlay `isOpen` check |

---

## 3. Frontend Fixes

### Status Handling (all backend enum values)

Added helper functions:
- `isTerminalStatus(status)` — returns `true` for `completed`, `failed`, `cancelled`
- `isScanningStatus(status)` — returns `true` for `running`, `pending`, `processing`, `queued`, `starting`

The `startPolling()` callback now applies these to **every** response, ensuring no status value produces the triple-false limbo state.

### Watchdog Timer (30 seconds)

If no progress update is received for 30 seconds, the watchdog:
1. Fetches scan status directly from `GET /scans/{scanId}` (DB-backed endpoint)
2. If DB says `completed`/`failed`/`cancelled`, force-updates `ScanState` accordingly
3. Stops polling

The watchdog resets on every polling tick where progress has advanced. This prevents premature timeout during legitimate long scans.

### Polling Improvements

1. Polling only stops when `isTerminalStatus()` returns `true`
2. No status value bypasses the state machine (every path is handled)
3. Structured debug logging via `console.warn('[ScanSync]', ...)` — captures scan_id, status, progress, and state transitions

---

## 4. Backend Fixes

### Persistent Event Loop

`_run_scan_in_background()` now:
1. Creates a single event loop at the start
2. Uses it for all progress store initialization
3. Passes it to `SyncScanService` as `event_loop`
4. Keeps it alive throughout `execute_scan()`
5. Cleans up only in the `finally` block

### Improved `_safe_await()`

- Accepts optional `loop` parameter for persistent loop
- Uses `loop.run_until_complete(coro)` when loop is available and not running
- Falls back to `asyncio.run(coro)` when no loop is provided
- Logs errors at `error` level (not `warning`) when persistent loop fails

### SyncScanService._exec_async()

Wrapper method that calls `_safe_await(coro, loop=self.event_loop)`, ensuring all progress store operations use the persistent loop.

### DB-Fallback-First Polling Endpoint

`GET /scan/status/{scan_id}` now:
1. Always fetches DB status first
2. If DB says `COMPLETED`/`FAILED`/`CANCELLED`, returns DB status immediately and cleans up stale progress store entries
3. Only returns progress store data for in-flight states
4. Logs the source (DB vs progress store) for debugging

---

## 5. React Query Fixes

The `invalidateRelevantQueries()` function was already present but now:
- Called reliably from both polling completion AND watchdog timeout
- Invalidates `['repositories']`, `['scans']`, and repository-specific keys
- The `auto-refetch` effect (line 108-112 of `RepositoryResultsPage.tsx`) triggers `refetch()` when `isComplete` becomes true

---

## 6. Polling Improvements

| Aspect | Before | After |
|--------|--------|-------|
| Status coverage | 4 values (missing `processing`, `queued`, `cancelled`) | All 6 status values handled |
| Stop condition | `completed` or `failed` | `completed`, `failed`, or `cancelled` |
| DB fallback | Only when progress store empty | Always cross-checks DB for terminal states |
| Watchdog | None | 30-second timeout with direct DB fetch |
| Error handling | Stops polling on error | Logs error, continues polling |

---

## 7. State Machine Implementation

### Backend Scan Status Transitions

```
PENDING ──► PROCESSING ──► COMPLETED
  │                            │
  ├──► QUEUED ──► PROCESSING  │
  │                            │
  └──► FAILED ◄───────────────┘
  └──► CANCELLED
```

### Frontend Scan State

```
isActive + isScanning → overlay shows "Scan in Progress"
isComplete → overlay shows "Scan Complete" with score comparison + severity breakdown
isFailed → overlay shows "Scan Failed" with error + retry option
```

### Overlay Stage Progression

| Progress % | Stage | Label |
|-----------|-------|-------|
| 0-10 | 1/9 | Cloning Repository |
| 11-21 | 2/9 | Detecting Technologies |
| 22-32 | 3/9 | Running Terraform Rules |
| 33-43 | 4/9 | Running Kubernetes Rules |
| 44-54 | 5/9 | Running Docker Rules |
| 55-65 | 6/9 | Running CI/CD Rules |
| 66-76 | 7/9 | Running Secrets Scan |
| 77-87 | 8/9 | Generating AI Recommendations |
| 88-95 | 9/9 | Finalizing Report |
| 96-100 | ✅ | Complete |

---

## 8. Event Synchronization

### Three-Phase Completion Detection (defense in depth)

1. **WebSocket** (real-time, best case):
   - Backend broadcasts `type: "scan_complete"` with `status: "completed"`
   - Frontend `onComplete` callback fires immediately
   - Handles: ideal network conditions

2. **Polling** (fallback, 2s interval):
   - `GET /scan/status/{scanId}` returns DB status (always authoritative)
   - If DB says `COMPLETED`, frontend detects it within 2 seconds
   - Handles: missed WebSocket event, one failed poll request

3. **Watchdog** (last resort, 30s timeout):
   - After 30s without progress, fetches `GET /scans/{scanId}` directly
   - Force-updates state from DB
   - Handles: server restart, progress store corruption, network recovery

### Cleanup on completion

When polling endpoint detects DB terminal status, it calls `store._cleanup_scan(scan_id)` to remove the stale in-memory entry, preventing future stale reads.

---

## 9. Edge Cases Tested

| Scenario | Expected Behavior | Fix |
|----------|-------------------|-----|
| Normal scan completion | All stages progress, overlay shows complete | RC1 fix (event loop) + RC3 fix (status handling) |
| WebSocket message lost | Polling detects completion within 2s | RC4 fix (DB fallback) |
| Server restart during scan | Polling falls back to DB, detects completion | RC4 fix (DB-fallback-first) |
| Fast scan (<5s) | Overlay transitions quickly, shows completion | RC3 fix (all status values) |
| Slow scan (>5min) | Overlay stays synchronized, watchdog doesn't fire prematurely | RC5 fix (watchdog resets on progress) |
| Network interruption | Watchdog fires after 30s, fetches DB status | RC5 fix (30s watchdog) |
| Multiple rescan clicks | Creates single new scan, no duplicates | Pre-existing dedup in `/scan/start` |
| Progress store initialization failure | Falls back to DB, continues working | RC4 fix (DB always authoritative) |

---

## 10. Production Readiness Checklist

- [x] Backend lint passes (`ruff check`)
- [x] Backend types pass (`mypy --ignore-missing-imports`)
- [x] Frontend types pass (`tsc --noEmit`)
- [x] No silent exception swallowing — `_safe_await` now logs at `error` level
- [x] No dangling event loops — persistent loop cleaned up in `finally` block
- [x] No indefinite polling — 30s watchdog terminates stuck states
- [x] DB is source of truth for terminal states — progress store is advisory
- [x] Debug logging gated behind `DEBUG` constant (default `true`)
- [x] All 6 backend status values mapped in frontend state machine
- [x] Overlay never closes prematurely — stays open until user interaction
- [x] Auto-refresh fires on completion — React Query invalidated, `refetch()` called
- [x] Three-phase completion detection (WebSocket → Polling → Watchdog)

---

## Debug Log Output Reference

When `DEBUG=true` (default), frontend logs to `console.warn` with `[ScanSync]` prefix:

```
[ScanSync] Scan created: <uuid>
[ScanSync] Poll: status=running, progress=10%, prev=pending, terminal=false, scanning=true
[ScanSync] Poll: status=completed, progress=100%, prev=running, terminal=true, scanning=false
[ScanSync] Terminal status detected, stopping polling + watchdog
[ScanSync] Scan complete handler called
[ScanSync] Watchdog triggered — forcing DB status check for <uuid>
[ScanSync] Watchdog DB status: completed
[ScanSync] Watchdog detected terminal status: completed
```

Backend logs include:
```
📊 Returning scan status: scan_id=<uuid>, status=completed, progress=100
✅ Returning DB terminal status for scan <uuid>: completed
🗑️ Cleaning up stale progress store entry for completed scan <uuid>
🚀 Starting background scan for <uuid>
✅ Background scan completed: <uuid>, status=completed
```
