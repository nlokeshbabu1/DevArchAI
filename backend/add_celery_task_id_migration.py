"""
Migration script to add missing columns to database tables.

Run this script to update the database schema:
    python add_celery_task_id_migration.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.db.session import get_engine


async def add_column_if_not_exists(conn, table_name, column_name, column_type):
    """Add a column to a table if it doesn't exist."""
    try:
        # Check if column exists
        result = await conn.execute(text(f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = '{table_name}' AND column_name = '{column_name}'
            )
        """))
        exists = result.scalar()
        
        if exists:
            print(f"✓ {column_name} column already exists in {table_name} table")
            return True
        
        # Add column
        await conn.execute(text(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        ))
        await conn.commit()
        print(f"✓ Added {column_name} column to {table_name} table")
        return True
    except Exception as e:
        await conn.rollback()
        print(f"✗ Error adding {column_name} to {table_name}: {e}")
        raise


async def migrate():
    """Add missing columns to database tables."""
    
    print("Starting database migration...")
    
    engine = get_engine()
    
    async with engine.connect() as conn:
        # Add celery_task_id to scans table
        await add_column_if_not_exists(conn, "scans", "celery_task_id", "VARCHAR(255)")
        
        # Add subscription_plan to users table
        await add_column_if_not_exists(conn, "users", "subscription_plan", "VARCHAR(50) DEFAULT 'free'")
        
        # Add missing columns to findings table
        findings_columns = [
            ("risk", "TEXT"),
            ("impact", "TEXT"),
            ("fix_example", "TEXT"),
            ("ai_explanation", "TEXT"),
            ("impact_analysis", "TEXT"),
            ("confidence_score", "FLOAT DEFAULT 1.0"),
            ("is_resolved", "BOOLEAN DEFAULT FALSE"),
            ("resolved_at", "TIMESTAMP WITH TIME ZONE"),
        ]
        
        for column_name, column_type in findings_columns:
            await add_column_if_not_exists(conn, "findings", column_name, column_type)
        
        # Add linked_scan_id to anonymous_scans table
        await add_column_if_not_exists(conn, "anonymous_scans", "linked_scan_id", "VARCHAR(255)")
    
    print("\nMigration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
