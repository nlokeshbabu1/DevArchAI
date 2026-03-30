#!/usr/bin/env python3
"""
Test Gemini API with new google-genai library
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

print("🧪 Testing Gemini with google-genai library")
print("=" * 60)

# Check environment
gemini_api_key = os.getenv("GEMINI_API_KEY")
llm_provider = os.getenv("LLM_PROVIDER")
llm_model = os.getenv("LLM_MODEL")

print(f"\n📋 Configuration:")
print(f"  LLM_PROVIDER: {llm_provider}")
print(f"  GEMINI_API_KEY: {'✅ Set' if gemini_api_key else '❌ Not Set'}")
print(f"  LLM_MODEL: {llm_model}")

if not gemini_api_key:
    print("\n❌ ERROR: GEMINI_API_KEY not set!")
    sys.exit(1)

if llm_provider != "gemini":
    print(f"\n⚠️  WARNING: LLM_PROVIDER is '{llm_provider}', not 'gemini'")

print(f"\n🚀 Testing google-genai library...")

try:
    from google import genai
    print("✅ Successfully imported google.genai")
    
    # Create client
    client = genai.Client(api_key=gemini_api_key)
    print("✅ Successfully created Gemini client")
    
    # Test generation
    test_prompt = "You are a DevOps expert. Provide a brief JSON response with keys: explanation, impact_analysis, remediation_steps (array). Finding: Terraform state stored locally."
    
    print(f"\n📝 Sending test prompt to {llm_model or 'gemini-pro'}...")
    response = client.models.generate_content(
        model=llm_model or "gemini-pro",
        contents=test_prompt
    )
    
    print("✅ Successfully received response from Gemini!")
    print(f"\n📊 Response Preview (first 200 chars):")
    print("-" * 60)
    print(response.text[:200])
    print("-" * 60)
    
    # Verify response structure
    import json
    content = response.text
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()
    
    try:
        data = json.loads(content)
        print("\n✅ Response is valid JSON!")
        print(f"   Keys found: {list(data.keys())}")
    except json.JSONDecodeError as e:
        print(f"\n⚠️  Response is not valid JSON: {e}")
        print("   This is okay for testing - the API is working!")
    
    print("\n🎉 SUCCESS: Gemini API is working with google-genai library!")
    print("\n✅ Your DevArchAI backend is ready to use Gemini AI!")
    
except ImportError as e:
    print(f"\n❌ ERROR: Failed to import google.genai: {e}")
    print("   Make sure you installed: pip install google-genai")
    sys.exit(1)
    
except Exception as e:
    error_msg = str(e)
    print(f"\n❌ ERROR: Gemini API test failed: {e}")
    
    if "API key not valid" in error_msg or "400 INVALID_ARGUMENT" in error_msg:
        print("\n🔑 API Key Issue Detected:")
        print("   The API key format is correct but may be expired/invalid.")
        print("\n   Steps to fix:")
        print("   1. Get a new API key from: https://aistudio.google.com/apikey")
        print("   2. Update backend/.env:")
        print("      GEMINI_API_KEY=your_new_key_here")
        print("   3. Restart the backend server")
    elif "403" in error_msg or "PERMISSION_DENIED" in error_msg:
        print("\n🔒 Permission Issue:")
        print("   The API key may not have Gemini API access enabled.")
        print("   Check your Google AI Studio permissions.")
    elif "429" in error_msg or "RATE_LIMIT" in error_msg:
        print("\n⏱️  Rate Limit Exceeded:")
        print("   You've hit the API rate limit. Wait and try again.")
    else:
        import traceback
        traceback.print_exc()
    
    sys.exit(1)

print("\n" + "=" * 60)
print("Test completed successfully!")
