#!/usr/bin/env python3
"""
Link anonymous scans to the logged-in user.

This script finds scans created without user_id and links them to the specified user.
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

async def link_anonymous_scans(user_email: str):
    """Link anonymous scans to user."""
    
    # Database URL from .env
    DATABASE_URL = "postgresql+asyncpg://lokesh:2001@localhost:5432/devarchai"
    
    engine = create_async_engine(DATABASE_URL)
    
    async with AsyncSession(engine) as db:
        # Find user by username (email is encrypted)
        from app.models.user import User
        from app.models.scan import Scan
        
        # Extract username from email
        username = user_email.split('@')[0]
        
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User with username '{username}' not found!")
            print("   Available users in database:")
            result = await db.execute(select(User))
            for u in result.scalars().all():
                print(f"     - {u.username} (ID: {u.id})")
            return
        
        print(f"✓ Found user: {user.username} (ID: {user.id})")
        
        # Find anonymous scans (user_id IS NULL)
        result = await db.execute(
            select(Scan).where(Scan.user_id.is_(None))
        )
        anonymous_scans = result.scalars().all()
        
        if not anonymous_scans:
            print("✓ No anonymous scans found - all scans are already linked!")
            return
        
        print(f"⚠ Found {len(anonymous_scans)} anonymous scans to link")
        
        # Link them to user
        for scan in anonymous_scans:
            print(f"  Linking scan {scan.id} → {scan.repository_url}")
            scan.user_id = user.id
        
        await db.commit()
        
        print(f"\n✅ Successfully linked {len(anonymous_scans)} scans to {user.username}")
        print("\n🎉 Refresh your dashboard now - it should show real data!")


if __name__ == "__main__":
    import sys
    
    # Default to the email from your token
    default_email = "admin2@example.com"
    
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = default_email
    
    print(f"Linking anonymous scans to: {email}\n")
    asyncio.run(link_anonymous_scans(email))
