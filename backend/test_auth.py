#!/usr/bin/env python3
"""Create test user and verify auth flow."""

import asyncio
import sys
sys.path.insert(0, '/home/lokesh/AI-Engine/DevArchAI/backend')

from sqlalchemy import select
from app.db.session import get_session_factory
from app.models.user import User
from app.core.security import create_access_token, verify_password, get_password_hash

async def main():
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Check existing users
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        print("=== Existing Users ===")
        for user in users:
            print(f"  - {user.username} (ID: {user.id})")
        
        # Create test user if not exists
        test_email = "test@example.com"
        result = await session.execute(select(User).where(User.email_hash == 'a1b2c3d4'))
        test_user = result.scalar_one_or_none()
        
        if not test_user:
            print("\n=== Creating Test User ===")
            from app.core.security import get_password_hash
            import hashlib
            
            # Create user manually
            email_hash = hashlib.sha256(test_email.encode()).hexdigest()
            
            new_user = User(
                username="testuser",
                email_hash=email_hash,
                hashed_password=get_password_hash("test123"),
                is_active=True,
                is_verified=True,
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            print(f"Created user: {new_user.username} (ID: {new_user.id})")
            test_user = new_user
        else:
            print("\n=== Test User Exists ===")
            print(f"User: {test_user.username} (ID: {test_user.id})")
        
        # Generate token
        print("\n=== Generate Access Token ===")
        token_data = {"sub": str(test_user.id), "username": test_user.username}
        token = create_access_token(data=token_data)
        print(f"Email: {test_email}")
        print(f"Password: test123")
        print(f"\nACCESS_TOKEN={token}")
        
        # Verify token works
        print("\n=== Test Token ===")
        import requests
        response = requests.get(
            "http://localhost:8000/api/v1/dashboard/summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Dashboard API Response: {response.status_code}")
        print(f"Data: {response.json()}")

if __name__ == "__main__":
    asyncio.run(main())
