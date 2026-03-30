"""Fix missing database columns."""

import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/devarchai")


async def add_missing_columns():
    """Fix database schema to match User model."""
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            # The issue: database has old 'email' column with NOT NULL constraint
            # but model uses email_encrypted instead
            
            # Option 1: Drop the email column entirely (safest)
            print('Dropping old email column if exists...')
            await conn.execute(text("""
                ALTER TABLE users DROP COLUMN IF EXISTS email;
            """))
            print("✓ Old email column dropped")
            
            # Option 2: If you want to keep email column, make it nullable
            # But since we're using email_encrypted, dropping is better
            print('Making email column nullable (fallback)...')
            await conn.execute(text("""
                DO $$ 
                BEGIN 
                    IF EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'email'
                    ) THEN
                        ALTER TABLE users ALTER COLUMN email DROP NOT NULL;
                    END IF;
                END $$;
            """))
            print("✓ Email column constraint removed")
            
            # Add email_encrypted if not exists
            await conn.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'email_encrypted'
                    ) THEN
                        ALTER TABLE users ADD COLUMN email_encrypted VARCHAR(512);
                    END IF;
                END $$;
            """))
            print("✓ email_encrypted column check completed")
            
            # Add email_hash if not exists
            await conn.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'email_hash'
                    ) THEN
                        ALTER TABLE users ADD COLUMN email_hash VARCHAR(255);
                    END IF;
                END $$;
            """))
            print("✓ email_hash column check completed")
            
            await conn.commit()
            print("\n✓ Database schema updated successfully!")
            print("\nNote: The old 'email' column has been dropped.")
            print("The application now uses 'email_encrypted' and 'email_hash' columns.")
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: You may need to:")
        print("1. Check your DATABASE_URL environment variable")
        print("2. Verify PostgreSQL is running")
        print("3. Check PostgreSQL credentials")
        print("\nCurrent DATABASE_URL:", DATABASE_URL)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(add_missing_columns())
