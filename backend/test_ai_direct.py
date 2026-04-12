#!/usr/bin/env python3
"""Direct AI enrichment test."""
import asyncio
import sys
sys.path.insert(0, '/home/lokesh/AI-Engine/DevArchAI/backend')

from app.services.findings_enricher import AIFixEnrichmentService
from app.config import settings

print("🤖 AI ENRICHMENT DIRECT TEST")
print("=" * 80)
print(f"Mistral API Key: {'✅ Configured' if settings.MISTRAL_API_KEY else '❌ Not set'}")
print(f"LLM Provider: {settings.LLM_PROVIDER}")
print()

test_finding = {
    "rule_id": "DKR-SEC-001",
    "rule_name": "Container Running as Root",
    "severity": "high",
    "file_type": "dockerfile",
    "description": "Container runs as root user",
    "recommendation": "Add USER instruction to run as non-root"
}

async def test_ai():
    ai_service = AIFixEnrichmentService()
    print(f"AI Service initialized: use_mock={ai_service._use_mock}")
    print()
    
    print("📤 Sending to AI for enrichment...")
    result = await ai_service.generate_fix(test_finding)
    
    print("📥 AI Response received!")
    print()
    print(f"Rule: {result.get('rule_id', 'N/A')}")
    print(f"Summary: {str(result.get('summary', 'N/A'))[:150]}")
    print(f"Risk: {str(result.get('risk', 'N/A'))[:100]}")
    print(f"Fix Code: {str(result.get('fix_code', 'N/A'))[:100]}")
    print(f"Confidence: {result.get('confidence', 'N/A')}")
    print(f"AI Generated: {result.get('ai_generated', False)}")
    print()
    
    if result.get('summary') and len(str(result['summary'])) > 30:
        print("✅ AI IS WORKING - Generated real content!")
    else:
        print("⚠️  Using mock/static fallback")

asyncio.run(test_ai())
