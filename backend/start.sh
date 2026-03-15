#!/bin/bash
# DevArchAI Backend Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting DevArchAI Backend...${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo -e "${YELLOW}Python Version: ${PYTHON_VERSION}${NC}"

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Not running in a virtual environment${NC}"
    echo -e "${YELLOW}Consider creating one:${NC}"
    echo -e "  python3 -m venv venv"
    echo -e "  source venv/bin/activate"
fi

# Install dependencies if needed
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    cp .env.example .env 2>/dev/null || echo "No .env.example found"
fi

# Clean pytest cache
echo -e "${YELLOW}Cleaning pytest cache...${NC}"
rm -rf .pytest_cache __pycache__ app/__pycache__ tests/__pycache__ 2>/dev/null || true

# Check Redis connection
echo -e "${YELLOW}Checking Redis connection...${NC}"
if ! command -v redis-cli &> /dev/null; then
    echo -e "${RED}Redis CLI not found. Install Redis or check connection.${NC}"
else
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}Redis connection OK${NC}"
    else
        echo -e "${RED}Redis not responding. Start Redis: docker run -d -p 6379:6379 redis:7${NC}"
    fi
fi

# Check PostgreSQL connection
echo -e "${YELLOW}Checking database connection...${NC}"
if command -v psql &> /dev/null; then
    if psql "$DATABASE_URL" -c "SELECT 1" &> /dev/null 2>&1; then
        echo -e "${GREEN}Database connection OK${NC}"
    else
        echo -e "${RED}Database not responding. Check DATABASE_URL in .env${NC}"
    fi
fi

# Initialize database
echo -e "${YELLOW}Initializing database...${NC}"
python3 init_db.py || echo -e "${YELLOW}Database init skipped (may already exist)${NC}"

# Start Celery worker in background
echo -e "${YELLOW}Starting Celery worker...${NC}"
celery -A app.workers.celery_config worker --loglevel=info --pool=solo &
CELERY_PID=$!
echo -e "${GREEN}Celery worker started (PID: ${CELERY_PID})${NC}"

# Wait a moment for Celery to start
sleep 2

# Start uvicorn
echo -e "${GREEN}Starting Uvicorn server on http://0.0.0.0:8000${NC}"
echo -e "${GREEN}API Docs: http://0.0.0.0:8000/docs${NC}"
echo -e "${GREEN}Health Check: http://0.0.0.0:8000/health${NC}"

# Trap to cleanup on exit
cleanup() {
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $CELERY_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start uvicorn with auto-reload for development
exec python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir app \
    --log-level info
