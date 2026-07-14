#!/bin/bash
# DevArchAI — Standalone Migration Script
# Runs Alembic upgrade head with error handling.
# Usage: ./migrate.sh [DATABASE_URL]
set -euo pipefail

# Colors
INFO='\033[0;32m'
ERR='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${INFO}[MIGRATE]${NC} $*"; }
log_error() { echo -e "${ERR}[MIGRATE]${NC} $*" >&2; }

# Allow DATABASE_URL override as first argument
if [ -n "${1:-}" ]; then
    export DATABASE_URL="$1"
fi

if [ -z "${DATABASE_URL:-}" ]; then
    log_error "DATABASE_URL is not set. Pass it as an argument or export it."
    exit 1
fi

log_info "Running Alembic migrations..."
if python3 -c "
from app.db.migrate import run_migrations
run_migrations()
"; then
    log_info "Migrations applied successfully"
else
    log_error "Migration failed"
    exit 1
fi

log_info "Verifying migration state..."
python3 -c "
from app.db.migrate import current_revision, pending_migrations
rev = current_revision()
pending = pending_migrations()
print(f'Current revision: {rev}')
if pending:
    print(f'WARNING: {len(pending)} pending migration(s): {pending}')
    exit(1)
print('Schema is up to date')
"
log_info "Done"
