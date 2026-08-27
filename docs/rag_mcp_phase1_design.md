# Phase 1 — RAG + MCP Knowledge Layer: Design Decisions

Status: approved decisions, implementation next.
Scope: knowledge foundation only. **Nothing here touches the scan pipeline.**
Scanner behavior, rule engine, scan lifecycle, Result Page UI, and LLM provider
selection remain unchanged.

## Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Vector store | **pgvector on existing Postgres 15** | Postgres 15 already in `docker-compose.yml`; no new service; transactional with `findings`/`scans`; reuses Alembic migrations and existing Redis. |
| Embeddings | **Auto-router** with local default | `EMBEDDING_PROVIDER=auto` (default): use OpenAI embeddings if `OPENAI_API_KEY` present, else a local offline model (`sentence-transformers`, no API key). Overridable to `openai` or `local` in `.env`. RAG must work under the current `LLM_PROVIDER=mock` default. |
| Embedding library | `langchain-huggingface` (small, CPU) via existing LangChain | Avoids a second framework; CPU-friendly for DEV; `sentence-transformers` family already implicit via LangChain. |
| MCP vs RAG split | RAG = "what DevArchAI knows" (rules, curated docs, internal knowledge). MCP = "current/external info" (live AWS/Azure state, official docs). | Keeps deterministic scanner rules authoritative; MCP/RAG enrich context only. |
| Priority order | 1) live env data, 2) current official docs, 3) DevArchAI curated knowledge, 4) general external knowledge | Explicit source ranking for retrieval and MCP resolution. |
| MCP failure | Circuit breaker + timeout + retry; **never** fails the scan. Returns `status=skipped`/`unavailable` context. | Requirement: scan must never fail because MCP fails. |
| Secrets | Central redaction layer; MCP contexts redacted before store/prompt; no credentials logged. | Requirement: MCP must never leak secrets. |
| Rules authority | Scanner/rule engine unchanged; RAG indexes existing rule IDs (see `technology_inventory.yaml`). | Requirement: no rule rewrites in this phase. |

## Layer responsibilities

- `app/rag/` — knowledge retrieval. Wraps pgvector store; `rule_id`-first
  retrieval with metadata filters (technology, rule_id, category, severity,
  source_type, source_name, authority, version, rag_version). Ingestion
  pipeline: Loader → Cleaner → Chunker → Metadata → Embedding → pgvector.
  Reuses `app/knowledge/` providers/cache/metrics.
- `app/mcp/` — external context gateway. Technology router (Kubernetes,
  Terraform, Docker, CI/CD, AWS, Azure…), doc-vs-live split,
  `requires_live_context()` / `get_live_context()` decision logic, timeouts,
  retries, circuit breaker, secret redaction, source labeling, graceful
  degradation.

## Deliverables (next)

1. `backend/app/rag/data/technology_inventory.yaml` — ✅ done (rule IDs from source).
2. pgvector migration (Alembic) + `knowledge_documents`, `rag_chunks`, `mcp_context` tables.
3. Embedding auto-router (`openai` / `local`).
4. RAG retrieval service + Redis cache keys (`devarchai:rag:chunk:{hash}`,
   `devarchai:mcp:ctx:{tech}:{hash}`).
5. MCP router + circuit breaker + redaction.
6. API service stubs (`get_rule_knowledge`, `retrieve_context`,
   `requires_live_context`, `get_live_context`) — no scan-pipeline wiring.
7. Metrics (`rag_query`, `rag_cache_hit/miss`, `mcp_request/success/failure/timeout/skipped`, `knowledge_version`).
8. Tests: rule-id retrieval, tech filtering, cache, MCP routing/timeout/redaction, scanner regression.

## Explicit non-goals (this phase)

- No changes to scanner/rules/scan lifecycle/Result Page/LLM provider selection.
- No final AI recommendation pipeline (template/AI enrichment stays as-is).
- No microservices; no new infrastructure services beyond pgvector extension.
