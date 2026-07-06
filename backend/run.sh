#!/bin/bash
# Quick start script for development (without Celery)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Clean cache
rm -rf .pytest_cache __pycache__ app/__pycache__ 2>/dev/null || true

echo "Starting DevArchAI Backend (Development Mode)..."
echo "API: http://localhost:8000"
echo "Docs: http://localhost:8000/docs"

# Set environment
export ENVIRONMENT=development
export LOG_LEVEL=INFO
export LOG_FORMAT=console

# Run database migrations
echo "Running database migrations..."
python3 -c "from app.db.migrate import run_migrations; run_migrations()"
echo "Migrations complete"

# Start uvicorn
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info
