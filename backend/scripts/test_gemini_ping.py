#!/usr/bin/env python3
"""Minimal Gemini connectivity test — uses ~10-20 tokens total.

Usage (from backend/):
    python scripts/test_gemini_ping.py

Does NOT run RAG, MCP, or full K8s copilot — only verifies API key + model.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


async def main() -> int:
    from app.ai.engine import get_llm_provider
    from app.config import settings

    print("Gemini ping test")
    print(f"  LLM_PROVIDER: {settings.LLM_PROVIDER}")
    print(f"  LLM_MODEL:    {settings.LLM_MODEL}")
    print(f"  API key:      {'set' if settings.GEMINI_API_KEY else 'MISSING'}")

    if settings.LLM_PROVIDER != "gemini":
        print("\nWARN: LLM_PROVIDER is not 'gemini' — backend will not use Gemini for AI jobs.")
        print("      Set LLM_PROVIDER=gemini in backend/.env and restart uvicorn.")

    if not settings.GEMINI_API_KEY:
        print("\nFAIL: GEMINI_API_KEY not set")
        return 1

    provider = get_llm_provider()
    print(f"  Resolved:     {provider.__class__.__name__}")

    if provider.__class__.__name__ != "GeminiProvider":
        print("\nFAIL: get_llm_provider() did not return GeminiProvider")
        return 1

    try:
        reply = await provider.generate("Reply with exactly: OK")
        print(f"\nOK: {reply.strip()[:80]}")
        print("\nGemini is configured correctly. Restart backend to pick up .env changes.")
        return 0
    except Exception as exc:
        print(f"\nFAIL: {exc}")
        if "404" in str(exc) or "NOT_FOUND" in str(exc):
            print("\nHint: model name may be invalid. Try:")
            print("  LLM_MODEL=gemini-2.5-flash-lite")
            print("  LLM_MODEL=gemini-2.0-flash")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
