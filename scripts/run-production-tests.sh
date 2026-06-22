#!/bin/bash
# Production Test Runner for DevArchAI
# 
# Runs all test suites:
# - Backend unit tests
# - Backend integration tests
# - Backend AI validation tests
# - Frontend component tests
# - Frontend E2E tests
#
# Usage:
#   ./scripts/run-production-tests.sh
#   ./scripts/run-production-tests.sh --backend-only
#   ./scripts/run-production-tests.sh --frontend-only

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   DevArchAI Production Test Suite                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run tests and track results
run_tests() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${YELLOW}▶ Running: ${test_name}${NC}"
    echo -e "${BLUE}  Command: ${test_command}${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}  ✅ ${test_name} PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}  ❌ ${test_name} FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
}

# Parse arguments
BACKEND_ONLY=false
FRONTEND_ONLY=false

for arg in "$@"; do
    case $arg in
        --backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        --frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --backend-only    Run only backend tests"
            echo "  --frontend-only   Run only frontend tests"
            echo "  --help            Show this help message"
            exit 0
            ;;
    esac
done

# Backend Tests
if [ "$FRONTEND_ONLY" = false ]; then
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Backend Tests                                       ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""

    cd "$PROJECT_ROOT/backend"

    # Unit Tests
    echo -e "${YELLOW}─── Unit Tests ───${NC}"
    run_tests "Rule Engine Tests" \
        "python -m pytest tests/unit/test_rule_engine.py -v --tb=short"
    
    run_tests "Scoring Engine Tests" \
        "python -m pytest tests/unit/test_scoring_engine.py -v --tb=short"
    
    run_tests "Technology Detector Tests" \
        "python -m pytest tests/unit/test_technology_detector.py -v --tb=short"
    
    run_tests "Findings Enricher Tests" \
        "python -m pytest tests/unit/test_findings_enricher.py -v --tb=short"
    
    run_tests "Findings Deduplicator Tests" \
        "python -m pytest tests/unit/test_findings_deduplicator.py -v --tb=short"
    
    run_tests "Production Services Tests (NEW)" \
        "python -m pytest tests/unit/test_production_services.py -v --tb=short"
    
    echo ""

    # Integration Tests
    echo -e "${YELLOW}─── Integration Tests ───${NC}"
    run_tests "Scan API Tests" \
        "python -m pytest tests/integration/test_scan_api.py -v --tb=short"
    
    run_tests "DevSecOps Scanner Tests" \
        "python -m pytest tests/integration/test_devsecops_scanner.py -v --tb=short"
    
    run_tests "API Production Tests (NEW)" \
        "python -m pytest tests/integration/test_api_production.py -v --tb=short"
    
    run_tests "Repo Scan Tests (NEW)" \
        "python -m pytest tests/integration/test_repo_scan.py -v --tb=short -k 'not real'"
    
    echo ""

    # AI Tests
    echo -e "${YELLOW}─── AI Validation Tests ───${NC}"
    run_tests "AI Generation Tests" \
        "python -m pytest tests/ai/test_ai_generation_complete.py -v --tb=short"
    
    run_tests "AI Fix Generator Tests" \
        "python -m pytest tests/ai/test_ai_fix_generator.py -v --tb=short"
    
    echo ""
fi

# Frontend Tests
if [ "$BACKEND_ONLY" = false ]; then
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Frontend Tests                                      ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""

    cd "$PROJECT_ROOT/frontend"

    # Component Tests
    echo -e "${YELLOW}─── Component Tests ───${NC}"
    run_tests "Component Tests" \
        "npm test -- --passWithNoTests --watchAll=false"
    
    run_tests "Scan Components Tests (NEW)" \
        "npm test -- src/components/__tests__/scan-components.test.tsx --passWithNoTests --watchAll=false"
    
    echo ""

    # E2E Tests (only if Playwright is installed)
    echo -e "${YELLOW}─── E2E Tests ───${NC}"
    if command -v npx &> /dev/null && [ -f "playwright.config.ts" ]; then
        run_tests "E2E Scan Flow Tests" \
            "npx playwright test tests/e2e/scan-flow.spec.ts --reporter=line"
        
        run_tests "E2E Production Tests (NEW)" \
            "npx playwright test tests/e2e/scan-flow-production.spec.ts --reporter=line"
    else
        echo -e "${YELLOW}  ⚠️  Playwright not installed, skipping E2E tests${NC}"
        echo -e "${YELLOW}     Install with: npx playwright install${NC}"
        echo ""
    fi
    
    echo ""
fi

# Summary
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Test Summary                                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Total Test Suites:  ${TOTAL_TESTS}"
echo -e "${GREEN}Passed:             ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed:             ${FAILED_TESTS}${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}Production readiness: READY FOR DEPLOYMENT${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${YELLOW}Review failures above and fix before deployment${NC}"
    exit 1
fi
