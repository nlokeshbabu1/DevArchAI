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
# 4. Start the application
# ──────────────────────────────────────────────
echo -e "${INFO}[4/4] Starting application...${NC}"

exec "$@"
