"""
Script to manually sync GitHub App installations from GitHub API to database.

Usage:
    python scripts/sync_github_installations.py
"""

import asyncio
import sys
from pathlib import Path

import httpx
import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import settings


def generate_github_app_jwt() -> str:
    """Generate JWT for GitHub App authentication."""
    import time
    from datetime import datetime, timezone, timedelta
    import base64

    app_id = settings.GITHUB_APP_ID
    private_key = settings.GITHUB_APP_PRIVATE_KEY

    if not private_key and settings.GITHUB_APP_PRIVATE_KEY_PATH:
        key_path = Path(settings.GITHUB_APP_PRIVATE_KEY_PATH)
        if key_path.exists():
            private_key = key_path.read_text(encoding="utf-8")

    if not app_id or not private_key:
        raise ValueError("Missing GitHub App credentials. Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY")

    # Decode private key if base64
    if not private_key.startswith("-----BEGIN"):
        try:
            private_key = base64.b64decode(private_key).decode("utf-8")
        except Exception:
            pass

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (9 * 60),
        "iss": str(app_id),
    }

    return jwt.encode(payload, private_key, algorithm="RS256")


async def sync_installations():
    """Fetch installations from GitHub API and sync to database."""
    print("=" * 60)
    print("GitHub App Installation Sync")
    print("=" * 60)

    # Step 1: Generate JWT
    print("\n📝 Generating GitHub App JWT...")
    try:
        app_jwt = generate_github_app_jwt()
        print("✅ JWT generated successfully")
    except Exception as e:
        print(f"❌ Failed to generate JWT: {e}")
        return

    # Step 2: Fetch installations from GitHub API
    print("\n🔍 Fetching installations from GitHub API...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/app/installations",
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=15.0,
            )

            if response.status_code != 200:
                print(f"❌ Failed to fetch installations: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return

            installations = response.json()
            print(f"✅ Found {len(installations)} installation(s)")

    except Exception as e:
        print(f"❌ Failed to fetch installations: {e}")
        return

    # Step 3: Get or installations from database
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # Get existing installations
            result = await conn.execute(text("SELECT installation_id, repo_full_name FROM github_installations"))
            existing = {row[0]: row[1] for row in result.fetchall()}
            print(f"\n📊 Existing installations in database: {len(existing)}")

            # Sync new installations
            synced_count = 0
            for inst in installations:
                inst_id = inst["id"]
                account = inst.get("account", {})
                github_login = account.get("login")
                repository_selection = inst.get("repository_selection", "unknown")

                print(f"\n🔄 Processing installation {inst_id} for {github_login}")

                if repository_selection == "all":
                    # For "all" repositories, we need to find user and create one record
                    result = await conn.execute(
                        text("SELECT id FROM users WHERE github_login = :login"),
                        {"login": github_login}
                    )
                    user_row = result.fetchone()

                    if not user_row:
                        print(f"  ⚠️  User '{github_login}' not found in database, skipping")
                        continue

                    user_id = user_row[0]

                    # Check if already exists
                    if inst_id in existing:
                        print(f"  ✅ Already registered: {existing[inst_id]}")
                        continue

                    # For demonstration, we'll need to get repos from API
                    # For now, create a placeholder - user should provide repo name
                    print(f"  ℹ️  Installation grants access to ALL repos")
                    print(f"  ⚠️  Please provide specific repo name to register, or use manual registration")

                else:
                    # Get repositories from API
                    repos_url = inst.get("repositories_url", "")
                    if not repos_url:
                        print(f"  ⚠️  No repositories URL found")
                        continue

                    # Get installation token to access repos
                    token_response = await httpx.AsyncClient().post(
                        f"https://api.github.com/app/installations/{inst_id}/access_tokens",
                        headers={
                            "Authorization": f"Bearer {app_jwt}",
                            "Accept": "application/vnd.github+json",
                        },
                    )

                    if token_response.status_code not in [200, 201]:
                        print(f"  ❌ Failed to get installation token")
                        continue

                    inst_token = token_response.json().get("token")

                    # Fetch repositories
                    async with httpx.AsyncClient() as client:
                        repos_response = await client.get(
                            repos_url,
                            headers={
                                "Authorization": f"token {inst_token}",
                                "Accept": "application/vnd.github+json",
                            },
                        )

                        if repos_response.status_code != 200:
                            print(f"  ❌ Failed to fetch repositories")
                            continue

                        repos = repos_response.json().get("repositories", [])
                        print(f"  📦 Found {len(repos)} repository(ies)")

                        for repo in repos:
                            repo_full_name = repo.get("full_name")
                            if not repo_full_name:
                                continue

                            # Find user
                            result = await conn.execute(
                                text("SELECT id FROM users WHERE github_login = :login"),
                                {"login": github_login}
                            )
                            user_row = result.fetchone()

                            if not user_row:
                                print(f"  ⚠️  User '{github_login}' not found, skipping {repo_full_name}")
                                continue

                            user_id = user_row[0]

                            # Check if already registered
                            check = await conn.execute(
                                text("SELECT id FROM github_installations WHERE installation_id = :inst_id AND repo_full_name = :repo"),
                                {"inst_id": inst_id, "repo": repo_full_name}
                            )
                            if check.fetchone():
                                print(f"  ✅ Already registered: {repo_full_name}")
                                continue

                            # Insert installation
                            await conn.execute(
                                text("""
                                    INSERT INTO github_installations (id, user_id, repo_full_name, installation_id, created_at)
                                    VALUES (gen_random_uuid(), :user_id, :repo, :inst_id, NOW())
                                """),
                                {"user_id": user_id, "repo": repo_full_name, "inst_id": inst_id}
                            )
                            print(f"  ✅ Registered: {repo_full_name}")
                            synced_count += 1

            print(f"\n{'=' * 60}")
            print(f"✅ Sync complete! Registered {synced_count} new installation(s)")
            print(f"{'=' * 60}")

    except Exception as e:
        print(f"❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(sync_installations())
