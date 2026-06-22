"""
Test Gemini API Integration - Real API Call Test

This script tests if your Gemini API key is working and generating AI fields correctly.

Usage:
    python scripts/test_gemini_api.py

Note: Make sure to add your GEMINI_API_KEY to the .env file first!
"""

import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file first
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
print(f"📄 Loading .env from: {env_path}")
print()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.findings_enricher import AIFixEnrichmentService
from app.rule_engine.base import RuleFinding, Severity, Category


async def test_gemini_api():
    """Test real Gemini API call."""
    print("=" * 60)
    print("🧪 Testing Gemini API Integration")
    print("=" * 60)
    print()
    
    # Check if API key is configured
    from app.config import settings
    
    print("📋 Configuration Check:")
    print(f"  LLM Provider: {settings.LLM_PROVIDER}")
    print(f"  Gemini API Key: {'✅ Set' if settings.GEMINI_API_KEY else '❌ Not Set'}")
    print(f"  Gemini API Key (first 10 chars): {settings.GEMINI_API_KEY[:10] + '...' if settings.GEMINI_API_KEY else 'None'}")
    print()
    
    if not settings.GEMINI_API_KEY:
        print("❌ ERROR: Gemini API key not configured!")
        print("   Please add GEMINI_API_KEY to your .env file")
        return False
    
    # Create test finding
    test_finding = {
        "rule_id": "TF-STATE-001",
        "rule_name": "Local Backend Not Allowed",
        "severity": "critical",
        "file_type": "terraform",
        "description": "Terraform uses local backend instead of remote S3 backend",
        "file_path": "terraform/main.tf"
    }
    
    print("📝 Test Finding:")
    print(f"  Rule ID: {test_finding['rule_id']}")
    print(f"  Severity: {test_finding['severity']}")
    print(f"  Description: {test_finding['description']}")
    print()
    
    # Create AI service
    ai_service = AIFixEnrichmentService()
    
    print(f"🤖 AI Service Config:")
    print(f"  Use Mock: {ai_service._use_mock}")
    print(f"  Provider: {settings.LLM_PROVIDER}")
    print()
    
    if ai_service._use_mock:
        print("⚠️  WARNING: Using mock mode!")
        print("   This means either:")
        print("   - LLM_PROVIDER is set to 'mock'")
        print("   - GEMINI_API_KEY is not set")
        print()
    
    print("🚀 Calling Gemini API...")
    print()
    
    try:
        # Call Gemini API
        result = await ai_service.generate_fix(test_finding)
        
        print("✅ API Call Successful!")
        print()
        
        # Validate response
        print("📊 Response Validation:")
        
        required_fields = [
            "summary",
            "risk",
            "impact",
            "fix_code",
            "full_example",
            "confidence"
        ]
        
        all_present = True
        for field in required_fields:
            present = field in result and result[field] is not None
            status = "✅" if present else "❌"
            print(f"  {status} {field}: {'Present' if present else 'Missing'}")
            if present and field != "confidence":
                # Show preview
                value = str(result[field])[:100]
                print(f"      Preview: {value}...")
            elif field == "confidence":
                print(f"      Value: {result.get(field)}")
            
            if not present:
                all_present = False
        
        print()
        
        # Validate confidence
        if "confidence" in result:
            confidence = result["confidence"]
            if isinstance(confidence, (int, float)) and 0 <= confidence <= 1:
                print(f"✅ Confidence is valid: {confidence}")
            else:
                print(f"❌ Confidence is invalid: {confidence} (must be 0-1)")
                all_present = False
        
        print()
        
        # Check if AI or static
        if result.get("confidence", 0) >= 0.9 and "Gemini" in str(result.get("summary", "")):
            print("✅ Response appears to be from Gemini AI")
        elif result.get("confidence", 0) >= 0.7:
            print("✅ Response appears to be AI-generated")
        else:
            print("⚠️  Response appears to be static fallback")
        
        print()
        print("=" * 60)
        
        if all_present:
            print("✅ SUCCESS: All AI fields generated correctly!")
            print("=" * 60)
            return True
        else:
            print("⚠️  PARTIAL: Some fields missing")
            print("=" * 60)
            return False
        
    except Exception as e:
        print(f"❌ ERROR: API call failed!")
        print(f"   Error: {str(e)}")
        print()
        print("   Possible causes:")
        print("   1. Invalid API key")
        print("   2. Network issue")
        print("   3. Gemini service unavailable")
        print("   4. Rate limit exceeded")
        print()
        import traceback
        traceback.print_exc()
        return False


async def test_full_enrichment_flow():
    """Test full enrichment flow with RuleFinding object."""
    print()
    print("=" * 60)
    print("🧪 Testing Full Enrichment Flow")
    print("=" * 60)
    print()
    
    from app.services.findings_enricher_new import FindingsEnricher
    
    # Create RuleFinding
    finding = RuleFinding(
        rule_id="DOCKER-001",
        rule_name="Container Runs as Root",
        severity=Severity.HIGH,
        category=Category.SECURITY,
        description="Docker container runs as root user",
        recommendation="Add USER instruction to run as non-root",
        file_path="Dockerfile"
    )
    
    print("📝 Test Finding:")
    print(f"  Rule ID: {finding.rule_id}")
    print(f"  Severity: {finding.severity}")
    print(f"  Description: {finding.description}")
    print()
    
    # Create enricher
    enricher = FindingsEnricher()
    
    print("🚀 Enriching finding...")
    print()
    
    try:
        # Enrich finding
        result = await enricher.enrich_finding_async(finding)
        
        print("✅ Enrichment Complete!")
        print()
        
        print("📊 Enriched Fields:")
        print(f"  Summary: {result.summary[:100] if result.summary else '❌ Missing'}...")
        print(f"  Risk: {result.risk[:100] if result.risk else '❌ Missing'}...")
        print(f"  Impact: {result.impact[:100] if result.impact else '❌ Missing'}...")
        print(f"  Fix Code: {result.fix_code[:100] if result.fix_code else '❌ Missing'}...")
        print(f"  Confidence: {result.confidence if result.confidence else '❌ Missing'}")
        print(f"  AI Generated: {result.ai_generated}")
        print()
        
        # Validate
        if result.summary and result.risk and result.fix_code:
            print("✅ SUCCESS: All fields enriched!")
            return True
        else:
            print("⚠️  Some fields missing")
            return False
        
    except Exception as e:
        print(f"❌ ERROR: Enrichment failed!")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print()
    
    # Test 1: Direct API call
    test1_passed = await test_gemini_api()
    
    # Test 2: Full enrichment flow
    test2_passed = await test_full_enrichment_flow()
    
    # Summary
    print()
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"  Gemini API Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  Full Flow Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("=" * 60)
    
    if test1_passed and test2_passed:
        print()
        print("🎉 ALL TESTS PASSED! Gemini API is working correctly!")
        print()
        return 0
    else:
        print()
        print("⚠️  Some tests failed. Check the errors above.")
        print()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
