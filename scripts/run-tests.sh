#!/bin/bash
# DevArchAI Test Runner Script
# Usage: ./scripts/run-tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
RUN_BACKEND=true
RUN_FRONTEND=true
RUN_E2E=false
RUN_COVERAGE=true
RUN_PARALLEL=true
VERBOSITY="-v"

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only)
            RUN_FRONTEND=false
            shift
            ;;
        --frontend-only)
            RUN_BACKEND=false
            shift
            ;;
        --e2e)
            RUN_E2E=true
            shift
            ;;
        --no-coverage)
            RUN_COVERAGE=false
            shift
            ;;
        --no-parallel)
            RUN_PARALLEL=false
            shift
            ;;
        --quiet)
            VERBOSITY=""
            shift
            ;;
        --help)
            echo "DevArchAI Test Runner"
            echo ""
            echo "Usage: ./scripts/run-tests.sh [options]"
            echo ""
            echo "Options:"
            echo "  --backend-only    Run only backend tests"
            echo "  --frontend-only   Run only frontend tests"
            echo "  --e2e             Run E2E tests (Playwright)"
            echo "  --no-coverage     Skip coverage reporting"
            echo "  --no-parallel     Run tests sequentially"
            echo "  --quiet           Minimal output"
            echo "  --help            Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

print_header "🧪 DevArchAI Test Suite"

# Track test results
BACKEND_RESULT=0
FRONTEND_RESULT=0
E2E_RESULT=0

# Backend Tests
if [ "$RUN_BACKEND" = true ]; then
    print_header "Backend Tests"
    
    cd "$PROJECT_ROOT/backend"
    
    # Check if virtual environment exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    
    # Install test dependencies if needed
    if ! python -c "import pytest" 2>/dev/null; then
        print_info "Installing test dependencies..."
        pip install -q pytest pytest-asyncio pytest-cov pytest-mock pytest-xdist
    fi
    
    # Build pytest command
    PYTEST_CMD="pytest"
    
    if [ "$RUN_PARALLEL" = true ]; then
        PYTEST_CMD="$PYTEST_CMD -n auto"
    fi
    
    if [ "$RUN_COVERAGE" = true ]; then
        PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=term-missing --cov-report=html:htmlcov"
    fi
    
    PYTEST_CMD="$PYTEST_CMD $VERBOSITY tests/"
    
    # Run backend tests
    print_info "Running: $PYTEST_CMD"
    if eval $PYTEST_CMD; then
        print_success "Backend tests passed"
        BACKEND_RESULT=0
        
        if [ "$RUN_COVERAGE" = true ]; then
            print_info "Coverage report: backend/htmlcov/index.html"
        fi
    else
        print_error "Backend tests failed"
        BACKEND_RESULT=1
    fi
    
    cd "$PROJECT_ROOT"
fi

# Frontend Tests
if [ "$RUN_FRONTEND" = true ]; then
    print_header "Frontend Tests"
    
    cd "$PROJECT_ROOT/frontend"
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_info "Installing dependencies..."
        npm install --silent
    fi
    
    # Run unit tests
    print_info "Running unit tests..."
    if npm test -- --coverage --watchAll=false $VERBOSITY; then
        print_success "Frontend unit tests passed"
        FRONTEND_RESULT=0
        
        if [ "$RUN_COVERAGE" = true ]; then
            print_info "Coverage report: frontend/coverage/index.html"
        fi
    else
        print_error "Frontend unit tests failed"
        FRONTEND_RESULT=1
    fi
    
    cd "$PROJECT_ROOT"
fi

# E2E Tests (Playwright)
if [ "$RUN_E2E" = true ]; then
    print_header "E2E Tests (Playwright)"
    
    cd "$PROJECT_ROOT/frontend"
    
    # Check if Playwright is installed
    if ! npx playwright --version 2>/dev/null; then
        print_info "Installing Playwright..."
        npx playwright install
    fi
    
    # Run E2E tests
    print_info "Running E2E tests..."
    if npx playwright test $VERBOSITY; then
        print_success "E2E tests passed"
        E2E_RESULT=0
    else
        print_error "E2E tests failed"
        E2E_RESULT=1
    fi
    
    cd "$PROJECT_ROOT"
fi

# Summary
print_header "📊 Test Summary"

TOTAL_RESULT=0

if [ "$RUN_BACKEND" = true ]; then
    if [ $BACKEND_RESULT -eq 0 ]; then
        print_success "Backend: PASSED"
    else
        print_error "Backend: FAILED"
        TOTAL_RESULT=1
    fi
fi

if [ "$RUN_FRONTEND" = true ]; then
    if [ $FRONTEND_RESULT -eq 0 ]; then
        print_success "Frontend: PASSED"
    else
        print_error "Frontend: FAILED"
        TOTAL_RESULT=1
    fi
fi

if [ "$RUN_E2E" = true ]; then
    if [ $E2E_RESULT -eq 0 ]; then
        print_success "E2E: PASSED"
    else
        print_error "E2E: FAILED"
        TOTAL_RESULT=1
    fi
fi

print_header "Final Result"

if [ $TOTAL_RESULT -eq 0 ]; then
    print_success "✅ All tests passed!"
else
    print_error "❌ Some tests failed"
fi

exit $TOTAL_RESULT
