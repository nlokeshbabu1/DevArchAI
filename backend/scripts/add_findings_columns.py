#!/usr/bin/env python3
"""Add missing columns to findings table."""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/devarchai")

# Parse connection string
if DATABASE_URL.startswith("postgresql://"):
    # Remove prefix
    conn_str = DATABASE_URL.replace("postgresql://", "")
    # Parse
    user_pass, rest = conn_str.split("@")
    user, password = user_pass.split(":")
    host_port_db = rest.split("/")
    host_port = host_port_db[0].split(":")
    host = host_port[0]
    port = host_port[1] if len(host_port) > 1 else "5432"
    db = host_port_db[1] if len(host_port_db) > 1 else "devarchai"
else:
    # Default values
    host = "localhost"
    port = "5432"
    db = "devarchai"
    user = "lokesh"
    password = "lokesh"

print(f"Connecting to database: {host}:{port}/{db} as {user}")

try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=db,
        user=user,
        password=password
    )
except psycopg2.OperationalError as e:
    print(f"\n✗ Connection failed: {e}")
    print("\nTry these alternatives:")
    print("1. Set DATABASE_URL environment variable:")
    print("   export DATABASE_URL=postgresql://user:password@host:port/dbname")
    print("2. Or update the password in this script")
    print("3. Or run SQL manually:")
    print("   psql -U <user> -d devarchai")
    print("   ALTER TABLE findings ADD COLUMN summary TEXT;")
    print("   ALTER TABLE findings ADD COLUMN fix_code TEXT;")
    print("   ALTER TABLE findings ADD COLUMN full_example TEXT;")
    print("   ALTER TABLE findings ADD COLUMN best_practices TEXT;")
    print("   ALTER TABLE findings ADD COLUMN confidence DOUBLE PRECISION;")
    exit(1)

conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

cur = conn.cursor()

# Add columns
columns = [
    ("summary", "TEXT"),
    ("fix_code", "TEXT"),
    ("full_example", "TEXT"),
    ("best_practices", "TEXT"),
    ("confidence", "DOUBLE PRECISION"),
]

print("Adding missing columns to findings table...")
for col_name, col_type in columns:
    try:
        cur.execute(f"ALTER TABLE findings ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
        print(f"  ✓ Column '{col_name}' added (or already exists)")
    except Exception as e:
        print(f"  ✗ Error adding '{col_name}': {e}")

# Verify columns
print("\nVerifying columns...")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'findings' 
    AND column_name IN ('summary', 'fix_code', 'full_example', 'best_practices', 'confidence')
    ORDER BY column_name;
""")

existing = cur.fetchall()
print(f"Found {len(existing)} columns:")
for col in existing:
    print(f"  - {col[0]} ({col[1]})")

cur.close()
conn.close()

print("\n✓ Migration complete! Restart the backend server.")
