"""Manual test for PR creation on scan ec9898b8-1de0-4fe1-970d-b88f4c56f8bf"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_manual_pr_creation():
    # Connect to database
    db_url = "postgresql://lokesh:2001@localhost:5432/devarchai"
    
    print("Connecting to database...")
    conn = await asyncpg.connect(db_url)
    
    try:
        # Get scan details
        print("\n1. Getting scan details...")
        scan = await conn.fetchrow(
            "SELECT id, repository_url, branch, user_id FROM scans WHERE id = $1",
            "ec9898b8-1de0-4fe1-970d-b88f4c56f8bf"
        )
        
        if not scan:
            print("❌ Scan not found!")
            return
        
        print(f"✅ Scan found:")
        print(f"   Repository: {scan['repository_url']}")
        print(f"   Branch: {scan['branch']}")
        print(f"   User ID: {scan['user_id']}")
        
        # Get user's GitHub token
        print("\n2. Getting user's GitHub token...")
        user = await conn.fetchrow(
            "SELECT id, username, email_encrypted, github_access_token FROM users WHERE id = $1",
            scan['user_id']
        )
        
        if not user:
            print("❌ User not found!")
            return
        
        print(f"✅ User found:")
        print(f"   Username: {user['username']}")
        print(f"   GitHub Token: {user['github_access_token'][:20] if user['github_access_token'] else 'NONE'}...")
        print(f"   Token Length: {len(user['github_access_token']) if user['github_access_token'] else 0}")
        
        if not user['github_access_token']:
            print("\n❌ No GitHub token found! User needs to login with GitHub first.")
            return
        
        token = user['github_access_token']
        
        # Test the token
        print("\n3. Testing GitHub token validity...")
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=10.0,
            )
            
            if response.status_code == 200:
                github_user = response.json()
                scopes = response.headers.get('X-OAuth-Scopes', 'Not available')
                print(f"✅ Token is VALID!")
                print(f"   GitHub User: {github_user['login']}")
                print(f"   Scopes: {scopes}")
                
                if 'repo' not in scopes:
                    print("\n⚠️  WARNING: 'repo' scope is MISSING!")
                    print("   This token doesn't have repository write permissions.")
                    print("   User needs to: Logout → Login with GitHub again → Authorize with repo permissions")
                else:
                    print("\n✅ Token has 'repo' scope")
            else:
                print(f"❌ Token is INVALID!")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return
        
        # Test git clone with credential helper
        print("\n4. Testing git operations with credential helper...")
        import subprocess
        import tempfile
        
        repo_url = "https://github.com/nlokeshbabu1/nodejs-application.git"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create credential helper script
            cred_script = os.path.join(tmpdir, 'git-cred-helper.sh')
            with open(cred_script, 'w') as f:
                f.write(f'''#!/bin/bash
echo "protocol=https"
echo "host=github.com"
echo "username=oauth2"
echo "password={token}"
''')
            os.chmod(cred_script, 0o755)
            
            # Clone the repo
            print("   Cloning repository...")
            clone_result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", scan['branch'] or "main", repo_url, tmpdir],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if clone_result.returncode != 0:
                print(f"❌ Clone failed: {clone_result.stderr}")
                return
            
            print("✅ Clone succeeded")
            
            # Configure credential helper
            subprocess.run(
                ["git", "config", "credential.helper", f"!{cred_script}"],
                cwd=tmpdir,
                capture_output=True
            )
            
            # Create a test branch
            test_branch = "devarchai/test-manual-123"
            print(f"   Creating test branch: {test_branch}")
            subprocess.run(
                ["git", "checkout", "-b", test_branch],
                cwd=tmpdir,
                capture_output=True
            )
            
            # Create a test file
            test_file = os.path.join(tmpdir, "test-devarchai.txt")
            with open(test_file, 'w') as f:
                f.write("# DevArchAI Test\nThis is a test file.\n")
            
            subprocess.run(
                ["git", "add", "test-devarchai.txt"],
                cwd=tmpdir,
                capture_output=True
            )
            
            subprocess.run(
                ["git", "commit", "-m", "test: DevArchAI manual test"],
                cwd=tmpdir,
                capture_output=True
            )
            
            # Try to push
            print(f"   Pushing branch to {repo_url}...")
            push_result = subprocess.run(
                ["git", "push", "-u", "origin", test_branch],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if push_result.returncode == 0:
                print("✅ PUSH SUCCEEDED!")
                print(f"   Branch {test_branch} pushed successfully")
                
                # Cleanup: delete the test branch
                print("\n5. Cleaning up test branch...")
                delete_result = subprocess.run(
                    ["git", "push", "origin", "--delete", test_branch],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if delete_result.returncode == 0:
                    print("✅ Test branch deleted")
                else:
                    print(f"⚠️  Failed to delete test branch (you can delete it manually): {delete_result.stderr}")
                    
            else:
                print("❌ PUSH FAILED!")
                print(f"   Error: {push_result.stderr}")
                
                # Try with x-access-token
                print("\n6. Trying with x-access-token method...")
                auth_url = f"https://x-access-token:{token}@github.com/nlokeshbabu1/nodejs-application.git"
                
                push_result2 = subprocess.run(
                    ["git", "push", auth_url, f"refs/heads/{test_branch}:refs/heads/{test_branch}"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if push_result2.returncode == 0:
                    print("✅ PUSH with x-access-token SUCCEEDED!")
                else:
                    print("❌ PUSH with x-access-token ALSO FAILED!")
                    print(f"   Error: {push_result2.stderr}")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(test_manual_pr_creation())
