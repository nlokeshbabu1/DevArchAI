#!/bin/bash
# DevArchAI Backend — Production Startup Script
# Waits for DB, runs migrations, then starts uvicorn.
# Celery must be started separately.
set -euo pipefail

# Colors
INFO='\033[0;32m'
WARN='\033[1;33m'
ERR='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${INFO}[STARTUP]${NC} $*"; }
log_warn()  { echo -e "${WARN}[STARTUP]${NC} $*"; }
log_error() { echo -e "${ERR}[STARTUP]${NC} $*" >&2; }

# ──────────────────────────────────────────────
# 1. Wait for the database to be reachable
# ──────────────────────────────────────────────
if [ -n "${DATABASE_URL:-}" ]; then
    log_info "Waiting for database to be ready..."

    python3 -c "
import time, sys
from sqlalchemy import create_engine, text

url = '$DATABASE_URL'
if url.startswith('postgresql+asyncpg://'):
    url = url.replace('postgresql+asyncpg://', 'postgresql://')

retries = 60
for i in range(retries):
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
        elif i % 10 == 0:
            print(f'Still waiting for database... ({i}/{retries})', flush=True)
        time.sleep(2)

print('ERROR: Database did not become ready within 120 seconds')
sys.exit(1)
"
    log_info "Database connection confirmed"
else
    log_warn "DATABASE_URL not set — skipping database wait"
fi

# ──────────────────────────────────────────────
# 2. Run Alembic migrations
# ──────────────────────────────────────────────
log_info "Running database migrations..."
python3 -c "
from app.db.migrate import run_migrations
run_migrations()
print('Migrations complete')
"
log_info "Migrations applied successfully"

# ──────────────────────────────────────────────
# 3. Validate migration state
# ──────────────────────────────────────────────
log_info "Validating migration state..."
python3 -c "
from app.db.migrate import current_revision, pending_migrations
rev = current_revision()
pending = pending_migrations()
print(f'Current revision: {rev}')
if pending:
    print(f'WARNING: {len(pending)} pending migration(s): {pending}')
else:
    print('All migrations applied — schema is up to date')
"

# ──────────────────────────────────────────────
# 4. Start uvicorn
# ──────────────────────────────────────────────
log_info "Starting uvicorn..."
exec uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-1}" \
    --no-access-log="${NO_ACCESS_LOG:-false}" \
    --timeout-keep-alive "${KEEP_ALIVE_TIMEOUT:-65}"
