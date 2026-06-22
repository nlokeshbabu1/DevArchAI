# Multiprocessing AI Enrichment

## Overview

This document explains the **multiprocessing architecture** used for AI enrichment in the DevArchAI platform, why it's necessary, and how it solves critical event loop conflicts.

---

## 🎯 The Problem: uvloop Event Loop Conflicts

### Background

Our DevSecOps SaaS platform uses:
- **FastAPI** - Async web framework
- **Uvicorn** - ASGI server with **uvloop** (high-performance event loop)
- **Mistral AI / Gemini / OpenAI** - LLM providers for AI enrichment
- **Asyncio** - Python's async/await framework

### The Conflict

When running AI enrichment synchronously within FastAPI's request handlers, we encountered this critical error:

```
❌ AI enrichment failed: this event loop is already running.
```

**Root Cause:**
1. FastAPI/Uvicorn runs on **uvloop** - a high-performance asyncio event loop
2. AI enrichment requires calling `asyncio.run()` or `loop.run_until_complete()`
3. **uvloop doesn't support nested event loops** - you can't run an event loop inside another running event loop
4. `nest_asyncio` (a common fix) **doesn't work with uvloop** - it explicitly raises: `Can't patch loop of type <class 'uvloop.Loop'>`

### Failed Attempts

| Approach | Result | Why It Failed |
|----------|--------|---------------|
| `asyncio.run()` directly | ❌ | "event loop is already running" |
| `nest_asyncio.apply()` | ❌ | "Can't patch loop of type uvloop.Loop" |
| `loop.run_until_complete()` | ❌ | "Cannot run the event loop while another loop is running" |
| ThreadPoolExecutor | ❌ | Still inherits parent's uvloop |

---

## ✅ The Solution: Multiprocessing

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN PROCESS (FastAPI)                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Uvicorn Server (uvloop event loop)                 │   │
│  │  - Handles HTTP requests                            │   │
│  │  - Runs scan_repository.py                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                               │
│                             │ 1. Serialize findings        │
│                             │ 2. Spawn child process       │
│                             ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  multiprocessing.Pool(processes=1)                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                               │
│                             │ 3. Pass serialized data      │
│                             ▼                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              │
┌─────────────────────────────────────────────────────────────┐
│                  CHILD PROCESS (Isolated)                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  _run_ai_enrichment_in_process()                    │   │
│  │  - Creates NEW asyncio event loop                  │   │
│  │  - Calls Mistral/Gemini/OpenAI APIs                │   │
│  │  - Returns enriched findings                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ✅ No uvloop conflict - fresh event loop!                 │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Module-Level Function

```python
# backend/app/workers/tasks/scan_repository.py

def _run_ai_enrichment_in_process(findings_data, file_contents_data):
    """
    Run AI enrichment in a separate process with its own event loop.
    
    ⚠️ MUST be at module level for multiprocessing to work!
    (Cannot be a nested function - pickle can't serialize it)
    """
    from app.services.findings_enricher import enrich_findings_with_ai
    from app.rule_engine.base import RuleFinding, Severity, Category
    import asyncio
    
    # Recreate findings from serialized data
    findings = []
    for f_data in findings_data:
        finding = RuleFinding(
            rule_id=f_data['rule_id'],
            rule_name=f_data['rule_name'],
            severity=Severity(f_data['severity']),
            category=Category(f_data['category']),
            description=f_data['description'],
            # ... reconstruct all fields
        )
        findings.append(finding)
    
    # Create NEW event loop for this process (avoids uvloop conflict)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        enriched = loop.run_until_complete(
            enrich_findings_with_ai(findings, file_contents_data)
        )
        return enriched
    finally:
        loop.close()
```

**Why Module-Level?**
- `multiprocessing` uses **pickle** to serialize functions
- Pickle can only serialize module-level functions
- Nested functions (defined inside other functions) **cannot be pickled**

#### 2. Serialization & Process Execution

```python
# Serialize findings for multiprocessing
findings_data = []
for f in rule_findings:
    findings_data.append({
        'rule_id': f.rule_id,
        'rule_name': f.rule_name,
        'severity': f.severity.value,
        'category': f.category.value,
        'description': f.description,
        'file_path': f.file_path,
        # ... all necessary fields
    })

# Run AI enrichment in separate process
with multiprocessing.Pool(processes=1) as pool:
    enriched_findings = pool.apply(
        _run_ai_enrichment_in_process, 
        (findings_data, file_contents)
    )
```

#### 3. Merge Results Back

```python
# Merge enriched data back into original findings
enriched_map = {f.rule_id: f for f in enriched_findings}
for finding in rule_findings:
    if finding.rule_id in enriched_map:
        enriched = enriched_map[finding.rule_id]
        # Copy AI-generated fields
        if not finding.summary and enriched.summary:
            finding.summary = enriched.summary
        if not finding.risk and enriched.risk:
            finding.risk = enriched.risk
        if not finding.fix_code and enriched.fix_code:
            finding.fix_code = enriched.fix_code
        # ... copy all AI fields
        if enriched.ai_generated:
            finding.ai_generated = True
        # Copy diff fields from metadata
        if enriched.metadata.get('before_code'):
            finding.metadata['before_code'] = enriched.metadata['before_code']
        # ... etc
```

---

## 📊 Performance Impact

### Overhead

| Operation | Time |
|-----------|------|
| Process spawn | ~50-100ms |
| Serialization | ~10-20ms per finding |
| Deserialization | ~10-20ms per finding |
| **Total overhead** | **~100-200ms** |

### Benefits

| Benefit | Impact |
|---------|--------|
| **No uvloop conflicts** | ✅ AI enrichment works reliably |
| **Isolation** | ✅ AI errors don't crash main server |
| **Timeout protection** | ✅ Can kill child process if LLM hangs |
| **Memory isolation** | ✅ LLM responses don't bloat main process |
| **Scalability** | ✅ Can increase `processes=N` for parallel enrichment |

### Trade-offs

- **Slight latency** (~100-200ms overhead per scan)
- **Memory usage** (child process duplicates parent memory)
- **Complexity** (serialization/deserialization logic)

**Verdict:** Trade-offs are **acceptable** for production reliability.

---

## 🔧 Configuration

### Process Pool Size

```python
# Single process (default - recommended for most cases)
with multiprocessing.Pool(processes=1) as pool:
    enriched_findings = pool.apply(...)

# Multiple processes (for high-throughput scenarios)
with multiprocessing.Pool(processes=4) as pool:
    # Use pool.map() for parallel processing
    enriched_findings = pool.map(_run_ai_enrichment_in_process, tasks)
```

**Recommendation:** Start with `processes=1` and scale based on load.

### Timeout Protection

```python
# Add timeout to prevent hanging
from multiprocessing import TimeoutError

with multiprocessing.Pool(processes=1) as pool:
    try:
        enriched_findings = pool.apply_async(
            _run_ai_enrichment_in_process, 
            (findings_data, file_contents)
        ).get(timeout=60)  # 60 second timeout
    except TimeoutError:
        logger.error("AI enrichment timed out, using fallback")
        rule_findings = enrich_findings(rule_findings)  # Static fallback
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "Can't pickle local object"

**Error:**
```
AttributeError: Can't pickle local object 'SyncScanService.execute_scan.<locals>._run_ai_enrichment_in_process'
```

**Cause:** Function defined inside another function (not module-level)

**Solution:** Move function to module level:

```python
# ❌ WRONG - nested function
def execute_scan(self, scan):
    def _run_ai_enrichment_in_process(...):  # Can't pickle this!
        ...

# ✅ CORRECT - module level
def _run_ai_enrichment_in_process(...):  # Pickle-friendly
    ...

def execute_scan(self, scan):
    ...
```

### Issue 2: "No module named 'app'"

**Error:**
```
ModuleNotFoundError: No module named 'app'
```

**Cause:** Child process can't find imports

**Solution:** Import inside the function:

```python
def _run_ai_enrichment_in_process(findings_data, file_contents_data):
    # Import HERE, not at module level
    from app.services.findings_enricher import enrich_findings_with_ai
    from app.rule_engine.base import RuleFinding, Severity, Category
    ...
```

### Issue 3: Findings not merging back correctly

**Symptom:** `ai_generated` still `False` after enrichment

**Cause:** Metadata fields not copied back

**Solution:** Explicitly copy all fields including metadata:

```python
# Copy diff fields from metadata
if enriched.metadata.get('before_code'):
    finding.metadata['before_code'] = enriched.metadata['before_code']
if enriched.metadata.get('after_code'):
    finding.metadata['after_code'] = enriched.metadata['after_code']
if enriched.metadata.get('unified_diff'):
    finding.metadata['unified_diff'] = enriched.metadata['unified_diff']
```

---

## 📈 Monitoring & Logging

### Key Log Messages

```log
🚀 Starting AI enrichment in separate process...
✅ AI enrichment applied: rule=DKR-SEC-001, ai_generated=True
✅ AI enrichment applied: rule=DKR-SEC-002, ai_generated=True
✅ AI enrichment completed successfully! Generated 9/9 AI findings
```

### Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| AI enrichment success rate | >95% | <90% |
| Average enrichment time | <5s | >10s |
| Process spawn failures | 0 | >1% |
| Fallback to static rate | <5% | >10% |

---

## 🚀 Future Enhancements

### 1. Async Process Pool

Consider using `aiomultiprocess` for better async integration:

```python
import aiomultiprocess

async with aiomultiprocess.Pool() as pool:
    enriched_findings = await pool.apply(_run_ai_enrichment_in_process, ...)
```

### 2. Distributed Enrichment

For high-scale deployments, move AI enrichment to a separate microservice:

```
┌──────────────┐      ┌──────────────┐
│   FastAPI    │─────▶│  AI Worker   │
│   Server     │      │   Service    │
└──────────────┘      └──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │  Mistral AI  │
                       │  Gemini API  │
                       │  OpenAI API  │
                       └──────────────┘
```

### 3. Caching Layer

Add Redis caching to avoid redundant LLM calls:

```python
cache_key = f"ai_fix:{rule_id}:{file_hash}"
cached = await redis.get(cache_key)
if cached:
    return json.loads(cached)
# ... call LLM ...
await redis.setex(cache_key, 3600, json.dumps(result))
```

---

## 📚 References

- [Python Multiprocessing Docs](https://docs.python.org/3/library/multiprocessing.html)
- [Uvicorn Event Loop](https://www.uvicorn.org/settings/#loop)
- [Uvloop GitHub](https://github.com/MagicStack/uvloop)
- [nest_asyncio GitHub](https://github.com/erdewit/nest_asyncio)
- [aiomultiprocess GitHub](https://github.com/pgkelley4/aiomultiprocess)

---

## ✅ Summary

**Problem:** uvloop doesn't support nested event loops, breaking AI enrichment.

**Solution:** Run AI enrichment in a **separate process** with its own event loop using `multiprocessing`.

**Result:** ✅ Reliable AI enrichment with Mistral/Gemini/OpenAI, no uvloop conflicts.

**Trade-off:** ~100-200ms overhead per scan (acceptable for production reliability).

---

*Last updated: March 29, 2026*
*Author: DevArchAI Engineering Team*
