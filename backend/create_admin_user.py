"""Create initial admin user for testing."""

import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/devarchai")

# Admin credentials
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@1234"
ADMIN_USERNAME = "admin"
ADMIN_FULL_NAME = "Admin User"


def hash_password(password: str) -> str:
    """Hash password using bcrypt (simplified for testing)."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def hash_email(email: str) -> str:
    """Create SHA256 hash of email for lookups."""
    import hashlib
    return hashlib.sha256(email.lower().encode()).hexdigest()


def encrypt_email(email: str) -> tuple[str, str]:
    """Encrypt email and create hash (simplified for testing)."""
    import base64
    # Simple base64 encoding (in production, use proper encryption)
    email_encrypted = base64.b64encode(email.encode()).decode()
    email_hash = hash_email(email)
    return email_encrypted, email_hash


async def create_admin_user():
    """Create admin user in database."""
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            # Check if admin user already exists
            result = await conn.execute(text("""
                SELECT id, username, email_hash FROM users 
                WHERE username = :username OR email_hash = :email_hash
            """), {"username": ADMIN_USERNAME, "email_hash": hash_email(ADMIN_EMAIL)})
            
            existing_user = result.fetchone()
            
            if existing_user:
                print(f"⚠️  Admin user already exists!")
                print(f"   ID: {existing_user[0]}")
                print(f"   Username: {existing_user[1]}")
                print(f"   Email Hash: {existing_user[2]}")
                print(f"\n   You can login with:")
                print(f"   Email: {ADMIN_EMAIL}")
                print(f"   Password: {ADMIN_PASSWORD}")
            else:
                # Create admin user
                email_encrypted, email_hash = encrypt_email(ADMIN_EMAIL)
                hashed_password = hash_password(ADMIN_PASSWORD)
                
                await conn.execute(text("""
                    INSERT INTO users (
                        email_encrypted, email_hash, username, hashed_password, 
                        full_name, is_active, is_verified, role, subscription_plan
                    ) VALUES (
                        :email_encrypted, :email_hash, :username, :hashed_password,
                        :full_name, TRUE, TRUE, 'ADMIN', 'free'
                    )
                """), {
                    "email_encrypted": email_encrypted,
                    "email_hash": email_hash,
                    "username": ADMIN_USERNAME,
                    "hashed_password": hashed_password,
                    "full_name": ADMIN_FULL_NAME
                })
                
                await conn.commit()
                
                print("✓ Admin user created successfully!")
                print(f"\n   Login credentials:")
                print(f"   Email: {ADMIN_EMAIL}")
                print(f"   Password: {ADMIN_PASSWORD}")
                print(f"   Username: {ADMIN_USERNAME}")
                print(f"   Role: ADMIN")
            
            # Also create a regular test user
            TEST_EMAIL = "test@example.com"
            TEST_PASSWORD = "Test@1234"
            TEST_USERNAME = "testuser"
            
            result = await conn.execute(text("""
                SELECT id, username FROM users 
                WHERE username = :username
            """), {"username": TEST_USERNAME})
            
            existing_test = result.fetchone()
            
            if not existing_test:
                email_encrypted, email_hash = encrypt_email(TEST_EMAIL)
                hashed_password = hash_password(TEST_PASSWORD)
                
                await conn.execute(text("""
                    INSERT INTO users (
                        email_encrypted, email_hash, username, hashed_password, 
                        full_name, is_active, is_verified, role, subscription_plan
                    ) VALUES (
                        :email_encrypted, :email_hash, :username, :hashed_password,
                        :full_name, TRUE, TRUE, 'USER', 'free'
                    )
                """), {
                    "email_encrypted": email_encrypted,
                    "email_hash": email_hash,
                    "username": TEST_USERNAME,
                    "hashed_password": hashed_password,
                    "full_name": "Test User"
                })
                
                await conn.commit()
                
                print("\n✓ Test user created successfully!")
                print(f"\n   Login credentials:")
                print(f"   Email: {TEST_EMAIL}")
                print(f"   Password: {TEST_PASSWORD}")
                print(f"   Username: {TEST_USERNAME}")
                print(f"   Role: USER (Free plan)")
            else:
                print(f"\n⚠️  Test user already exists: {TEST_USERNAME}")
            
            print("\n" + "="*60)
            print("You can now login with any of the above credentials!")
            print("="*60)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin_user())
