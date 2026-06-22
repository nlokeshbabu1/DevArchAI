"""
GitHub App Configuration Guide

Your GitHub App needs to be configured with these settings:

1. Go to: https://github.com/settings/apps/YOUR_APP_NAME
   (or https://github.com/organizations/YOUR_ORG/settings/apps/YOUR_APP_NAME)

2. Under "Identifying and authorizing users":
   - Callback URL: http://localhost:5174/auth/github/callback
   - Homepage URL: http://localhost:5174
   - ✅ Enable "Request user authorization (OAuth) during installation"

3. Under "Permissions" → "Repository permissions":
   - Contents: Read & write
   - Pull requests: Read & write
   - Metadata: Read-only (usually automatic)

4. Under "Permissions" → "User permissions":
   - Email addresses: Read-only

5. Under "Subscribe to events":
   - ✅ Push
   - ✅ Pull request

6. Save changes

7. Users need to reinstall/reauthorize the app to get new permissions

After this, the OAuth flow will work correctly and tokens will have repository access.
"""

import asyncio
import httpx

async def test_github_app_oauth_flow():
    """Test the GitHub App OAuth flow and check what permissions are granted."""
    
    print("\n" + "="*70)
    print("GitHub App OAuth Flow Test")
    print("="*70 + "\n")
    
    # Your current OAuth token from database
    token = "ghu_2yS0BQRRE9dfvaSF"  # From earlier test
    
    print("Testing your current OAuth token...")
    print(f"Token: {token[:20]}...\n")
    
    async with httpx.AsyncClient() as client:
        # Test 1: Check token validity
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
            scopes = response.headers.get('X-OAuth-Scopes', '')
            
            print(f"✅ Token is valid")
            print(f"   User: {user['login']}")
            print(f"   Scopes: '{scopes}'")
            print()
            
            if not scopes:
                print("❌ PROBLEM: Token has NO scopes!")
                print()
                print("This means your GitHub App is NOT configured to request")
                print("repository permissions during OAuth authorization.")
                print()
                print("SOLUTION:")
                print("1. Go to your GitHub App settings")
                print("2. Add 'Contents: Read & write' permission")
                print("3. Add 'Pull requests: Read & write' permission")
                print("4. Save and have users reauthorize the app")
                print()
            else:
                print(f"✅ Token has scopes: {scopes}")
                
        else:
            print(f"❌ Token is invalid: {response.status_code}")
            print(f"   Response: {response.text}")
    
    print("\n" + "="*70)
    print("Next Steps:")
    print("="*70)
    print()
    print("1. Check your GitHub App settings at:")
    print("   https://github.com/settings/apps")
    print()
    print("2. Look for 'Repository permissions' section")
    print("   - If it's missing, your app might be an OAuth App, not a GitHub App")
    print()
    print("3. If you see it, enable:")
    print("   - Contents: Read & write")
    print("   - Pull requests: Read & write")
    print()
    print("4. After saving, users must reauthorize the app")
    print()


if __name__ == "__main__":
    asyncio.run(test_github_app_oauth_flow())
