"""MCP (live-context) gateway for DevArchAI Phase 1.

The MCP layer provides *current/external* information that DevArchAI does not
know about:

- live environment data (AWS / Azure scan state)
- current official documentation (fetched from curated official URLs)

It is deliberately separate from the RAG layer (RAG = "what DevArchAI knows").
All requests have timeouts, retries, per-technology circuit breakers, and
secret redaction. Providers never raise; failures become ``failed`` /
``timeout`` / ``skipped`` results so the scan pipeline is never affected.
"""
