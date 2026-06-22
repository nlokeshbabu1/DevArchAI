#!/usr/bin/env python3
"""
Simple Gemini API Test

This script tests if your Gemini API key is configured and working.

SETUP:
1. Get your Gemini API key from: https://aistudio.google.com/apikey
2. Edit the .env file and add your key:
   GEMINI_API_KEY=your_actual_api_key_here
3. Run this script:
   python scripts/test_gemini_simple.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

print("=" * 70)
print("🧪 Gemini API Test - DevArchAI")
print("=" * 70)
print()

# Check configuration
gemini_api_key = os.getenv("GEMINI_API_KEY")
llm_provider = os.getenv("LLM_PROVIDER", "mock")

print("📋 Configuration:")
print(f"  LLM Provider: {llm_provider}")
print(f"  GEMINI_API_KEY: {'✅ Set' if gemini_api_key else '❌ Not Set'}")

if gemini_api_key:
    print(f"  API Key (first 15 chars): {gemini_api_key[:15]}...")
    print(f"  API Key Length: {len(gemini_api_key)}")
print()

# Check if API key is set
if not gemini_api_key or gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
    print("❌ ERROR: Gemini API key not configured!")
    print()
    print("📝 SETUP INSTRUCTIONS:")
    print("  1. Get your API key from: https://aistudio.google.com/apikey")
    print("  2. Edit the .env file in the project root")
    print("  3. Add your key:")
    print("     GEMINI_API_KEY=AIzaSy...your_actual_key_here")
    print("  4. Set LLM_PROVIDER=gemini")
    print("  5. Run this script again")
    print()
    print("=" * 70)
    sys.exit(1)

# Try to import and test Gemini
print("🚀 Testing Gemini API...")
print()

try:
    import google.generativeai as genai
    
    # Configure Gemini
    genai.configure(api_key=gemini_api_key)
    
    # Create model
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Test prompt
    test_prompt = """You are a DevOps expert. Generate a fix for this issue in JSON format:

Issue: Docker container runs as root user
Severity: HIGH

Respond with this exact JSON format:
{
  "summary": "Brief explanation",
  "risk": "Security risk description",
  "impact": "Business impact",
  "fix_code": "Dockerfile fix",
  "confidence": 0.9
}

Respond ONLY with the JSON, no other text."""

    print("📝 Sending test prompt to Gemini...")
    print()
    
    # Generate response
    response = model.generate_content(test_prompt)
    
    print("✅ API Call Successful!")
    print()
    
    # Parse response
    response_text = response.text.strip()
    
    # Clean markdown if present
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    response_text = response_text.strip()
    
    print("📊 Gemini Response:")
    print("-" * 70)
    print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
    print("-" * 70)
    print()
    
    # Try to parse as JSON
    import json
    try:
        data = json.loads(response_text)
        
        print("✅ Response is valid JSON!")
        print()
        
        # Check required fields
        required_fields = ["summary", "risk", "impact", "fix_code", "confidence"]
        print("📋 Field Validation:")
        
        all_present = True
        for field in required_fields:
            present = field in data
            status = "✅" if present else "❌"
            print(f"  {status} {field}: {'Present' if present else 'Missing'}")
            if present:
                value = str(data[field])
                if len(value) > 80:
                    value = value[:80] + "..."
                print(f"      Value: {value}")
            
            if not present:
                all_present = False
        
        print()
        
        # Validate confidence
        if "confidence" in data:
            conf = data["confidence"]
            if isinstance(conf, (int, float)) and 0 <= conf <= 1:
                print(f"✅ Confidence is valid: {conf}")
            else:
                print(f"❌ Confidence is invalid: {conf}")
                all_present = False
        
        print()
        print("=" * 70)
        
        if all_present:
            print("🎉 SUCCESS: Gemini API is working correctly!")
            print("   All required AI fields are being generated.")
            print("=" * 70)
            print()
            print("✅ Your DevArchAI platform is ready to use Gemini AI!")
            print()
            sys.exit(0)
        else:
            print("⚠️  PARTIAL: Some fields missing in response")
            print("=" * 70)
            sys.exit(1)
        
    except json.JSONDecodeError as e:
        print(f"⚠️  Response is not valid JSON: {e}")
        print()
        print("   This might be a formatting issue with the AI response.")
        print("   The API is working, but the prompt may need adjustment.")
        print()
        sys.exit(1)
    
except ImportError:
    print("❌ ERROR: Google Gemini library not installed!")
    print()
    print("📝 INSTALLATION:")
    print("  Run: pip install google-generativeai")
    print()
    sys.exit(1)
    
except Exception as e:
    print(f"❌ ERROR: API test failed!")
    print(f"   Error: {str(e)}")
    print()
    print("   Possible causes:")
    print("   1. Invalid API key")
    print("   2. Network issue")
    print("   3. Gemini service unavailable")
    print("   4. Rate limit exceeded")
    print()
    print("   Please check your API key and try again.")
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)
