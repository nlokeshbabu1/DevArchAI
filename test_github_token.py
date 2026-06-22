"""Diagnostic script to check GitHub token validity."""
import asyncio
import httpx

# You need to get your actual token from the database
# For now, this script will help you test a token

async def test_github_token(token: str):
    """Test if a GitHub token is valid and has the right scopes."""
    
    print(f"\n{'='*60}")
    print(f"Testing GitHub Token")
    print(f"{'='*60}")
    print(f"Token length: {len(token)}")
    print(f"Token prefix: {token[:20]}...")
    print()
    
    # Test 1: Check token via GitHub API
    async with httpx.AsyncClient() as client:
        print("Test 1: Checking token via GitHub API...")
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=10.0,
        )
        
        if response.status_code == 200:
            user = response.json()
            print(f"✅ Token is valid!")
            print(f"   User: {user.get('login')}")
            print(f"   Scopes: {response.headers.get('X-OAuth-Scopes', 'Not available')}")
        else:
            print(f"❌ Token is INVALID!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    # Test 2: Try git clone with oauth2 method
    print("\nTest 2: Testing git clone with oauth2 method...")
    import subprocess
    import tempfile
    import os
    
    test_repo = "https://github.com/nlokeshbabu1/nodejs-application.git"
    auth_url = f"https://oauth2:{token}@github.com/nlokeshbabu1/nodejs-application.git"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", auth_url, tmpdir],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Git clone with oauth2 succeeded!")
            else:
                print("❌ Git clone with oauth2 FAILED!")
                print(f"   Error: {result.stderr}")
                
                # Try with x-access-token
                print("\nTest 3: Testing git clone with x-access-token method...")
                auth_url_x = f"https://x-access-token:{token}@github.com/nlokeshbabu1/nodejs-application.git"
                
                result2 = subprocess.run(
                    ["git", "clone", "--depth", "1", auth_url_x, tmpdir],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result2.returncode == 0:
                    print("✅ Git clone with x-access-token succeeded!")
                else:
                    print("❌ Git clone with x-access-token ALSO FAILED!")
                    print(f"   Error: {result2.stderr}")
                    return False
                    
        except subprocess.TimeoutExpired:
            print("❌ Git clone timed out")
            return False
    
    print(f"\n{'='*60}")
    print("Token test complete")
    print(f"{'='*60}\n")
    return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python test_github_token.py <YOUR_GITHUB_TOKEN>")
        print("\nTo get your token:")
        print("1. Check your browser's localStorage for the JWT token")
        print("2. Or query the database:")
        print("   SELECT github_access_token FROM users WHERE email_hash = '<your_email_hash>';")
        sys.exit(1)
    
    token = sys.argv[1]
    asyncio.run(test_github_token(token))
