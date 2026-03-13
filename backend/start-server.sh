#!/bin/bash
# Reliable startup script that works from any directory

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to that directory
cd "$SCRIPT_DIR"

# Set PYTHONPATH to include backend directory
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Clean any pytest cache that might interfere
rm -rf .pytest_cache 2>/dev/null || true

# Show info
echo "==================================="
echo "DevArchAI Backend Starting..."
echo "==================================="
echo "Directory: $(pwd)"
echo "Python: $(python3 --version)"
echo "Uvicorn: $(which uvicorn)"
echo "==================================="

# Run uvicorn with explicit module path
exec python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-exclude "*.pyc" \
    --reload-exclude "__pycache__/*" \
    --log-level info
