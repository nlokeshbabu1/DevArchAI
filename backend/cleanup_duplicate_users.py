"""Clean up duplicate users from failed OAuth attempts."""

import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/devarchai")


async def cleanup_duplicate_users():
    """Remove duplicate users created from failed OAuth attempts."""
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            # Find users with empty or null email_encrypted (failed OAuth attempts)
            print('Finding duplicate/failed users...')
            result = await conn.execute(text("""
                SELECT id, username, email_hash, github_id, created_at 
                FROM users 
                WHERE email_encrypted IS NULL 
                   OR email_encrypted = ''
                ORDER BY created_at DESC;
            """))
            failed_users = result.fetchall()
            
            if failed_users:
                print(f"\nFound {len(failed_users)} failed/duplicate user(s):")
                for user in failed_users:
                    print(f"  - ID: {user[0]}, Username: {user[1]}, GitHub ID: {user[3]}")
                
                # Delete failed users
                print('\nDeleting failed users...')
                await conn.execute(text("""
                    DELETE FROM users 
                    WHERE email_encrypted IS NULL 
                       OR email_encrypted = '';
                """))
                print("✓ Failed users deleted")
            
            # Also find duplicate usernames (keep the oldest one)
            print('\nChecking for duplicate usernames...')
            result = await conn.execute(text("""
                SELECT username, COUNT(*) as count
                FROM users
                GROUP BY username
                HAVING COUNT(*) > 1;
            """))
            duplicates = result.fetchall()
            
            if duplicates:
                print(f"\nFound {len(duplicates)} duplicate username(s):")
                for dup in duplicates:
                    print(f"  - Username: {dup[0]}, Count: {dup[1]}")
                    
                    # Delete duplicates, keeping the oldest (lowest id)
                    await conn.execute(text(f"""
                        DELETE FROM users 
                        WHERE username = '{dup[0]}' 
                        AND id != (
                            SELECT MIN(id) 
                            FROM users 
                            WHERE username = '{dup[0]}'
                        );
                    """))
                    print(f"  ✓ Deleted duplicates for username: {dup[0]}")
            else:
                print("✓ No duplicate usernames found")
            
            await conn.commit()
            print("\n✓ Database cleanup completed successfully!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_duplicate_users())
