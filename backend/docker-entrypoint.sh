#!/bin/bash
# DevArchAI Backend Docker Entrypoint
# Orchestrates: wait-for-db → migrate → validate → start
set -e

# Colors
INFO='\033[0;32m'
WARN='\033[1;33m'
ERR='\033[0;31m'
NC='\033[0m'

echo -e "${INFO}========================================${NC}"
echo -e "${INFO} DevArchAI Backend Starting${NC}"
echo -e "${INFO}========================================${NC}"

# ──────────────────────────────────────────────
# 1. Wait for the database to be reachable
# ──────────────────────────────────────────────
if [ -n "$DATABASE_URL" ]; then
    echo -e "${INFO}[1/4] Waiting for database...${NC}"

    # Use Python to poll the database (avoids needing pg_isready / netcat)
    python3 -c "
import time, sys
from sqlalchemy import create_engine, text

url = '$DATABASE_URL'
if url.startswith('postgresql+asyncpg://'):
    url = url.replace('postgresql+asyncpg://', 'postgresql://')

for i in range(60):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        engine.dispose()
        print('Database is ready')
        sys.exit(0)
    except Exception as e:
        if i == 0:
            print(f'Waiting for database... ({e})', flush=True)
        time.sleep(1)
print('Database did not become ready within 60 seconds')
sys.exit(1)
"
else
    echo -e "${WARN}[1/4] DATABASE_URL not set, skipping database wait${NC}"
fi

# ──────────────────────────────────────────────
# 2. Run Alembic migrations
# ──────────────────────────────────────────────
echo -e "${INFO}[2/4] Running database migrations...${NC}"
python3 -c "
from app.db.migrate import run_migrations
run_migrations()
print('Migrations complete')
"
echo -e "${INFO}[2/4] Migrations applied successfully${NC}"

# ──────────────────────────────────────────────
# 3. Validate migration state
# ──────────────────────────────────────────────
echo -e "${INFO}[3/4] Validating migration state...${NC}"
python3 -c "
from app.db.migrate import current_revision, pending_migrations
rev = current_revision()
pending = pending_migrations()
print(f'Current revision: {rev}')
if pending:
    print(f'WARNING: {len(pending)} migration(s) pending: {pending}')
else:
    print('All migrations applied')
"
echo -e "${INFO}[3/4] Validation complete${NC}"

# ──────────────────────────────────────────────
# 3a. Verify schema drift against the models
# ──────────────────────────────────────────────
echo -e "${INFO}[3a/4] Verifying schema against models...${NC}"
python3 -c "
import sys
from app.config import settings
from app.db.migrate import _sync_url, current_revision
from app.db.verify import verify_schema

url = _sync_url()
try:
    report = verify_schema(url, database_revision=current_revision())
except Exception as exc:
    print(f'WARNING: schema verification failed to run ({exc})')
    sys.exit(0)

for issue in report.warnings:
    print(f'[WARN ] schema: {issue.kind}: {getattr(issue, \"table\", \"\")} {getattr(issue, \"column\", \"\") or \"\"}'.rstrip())

if not report.ok:
    print(f'ERROR: schema drift detected against models ({len(report.issues)} issue(s))')
    print(report.format_banner())
    sys.exit(1)

print(f'Schema verified OK ({report.tables_checked} tables, {report.columns_checked} columns)')
"
echo -e "${INFO}[3a/4] Schema verification complete${NC}"

# Migrations already ran in this entrypoint — skip the duplicate pass inside
# FastAPI lifespan (saves ~5-10s on cold start; schema was validated above).
export DB_MIGRATE_ON_STARTUP=false

# ──────────────────────────────────────────────
# 3b. Optional: quick Redis reachability check (non-blocking)
# ──────────────────────────────────────────────
if [ -n "${REDIS_URL:-}" ]; then
    echo -e "${INFO}[3b/4] Checking Redis...${NC}"
    python3 -c "
import os, sys
url = os.environ.get('REDIS_URL', '')
if not url:
    sys.exit(0)
try:
    import redis
    client = redis.from_url(
        url,
        socket_connect_timeout=float(os.environ.get('REDIS_CONNECT_TIMEOUT_SECONDS', '3')),
        socket_timeout=float(os.environ.get('REDIS_SOCKET_TIMEOUT_SECONDS', '3')),
    )
    client.ping()
    print('Redis is ready')
except Exception as exc:
    print(f'Redis not reachable ({exc}) — app will start without cache', flush=True)
" || true
fi

# ──────────────────────────────────────────────
# 4. Start the application
# ──────────────────────────────────────────────
echo -e "${INFO}[4/4] Starting application on port ${PORT:-8000}...${NC}"

exec "$@"
