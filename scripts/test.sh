#!/bin/bash
# Test execution script
# Runs pytest with coverage and generates reports

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Running Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Parse command line arguments
PYTEST_ARGS=""
VERBOSE=false
FAST=false
COVERAGE=true
MARKERS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--fast)
            FAST=true
            shift
            ;;
        --no-cov)
            COVERAGE=false
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -k)
            PYTEST_ARGS="$PYTEST_ARGS -k $2"
            shift 2
            ;;
        *)
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="uv run pytest"

# Add verbosity
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage options
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=google_contacts_cisco"
    PYTEST_CMD="$PYTEST_CMD --cov-report=term-missing"
    PYTEST_CMD="$PYTEST_CMD --cov-report=html"
    PYTEST_CMD="$PYTEST_CMD --cov-report=xml"
else
    PYTEST_CMD="$PYTEST_CMD --no-cov"
fi

# Add fast mode (skip slow tests)
if [ "$FAST" = true ]; then
    echo -e "${YELLOW}Fast mode: Skipping slow tests${NC}"
    PYTEST_CMD="$PYTEST_CMD -m 'not slow'"
fi

# Add custom markers
if [ -n "$MARKERS" ]; then
    echo -e "${YELLOW}Running tests with markers: $MARKERS${NC}"
    PYTEST_CMD="$PYTEST_CMD -m '$MARKERS'"
fi

# Add any additional arguments
if [ -n "$PYTEST_ARGS" ]; then
    PYTEST_CMD="$PYTEST_CMD $PYTEST_ARGS"
fi

# Display command
echo -e "${BLUE}Command:${NC} $PYTEST_CMD"
echo ""

# Run tests
if eval "$PYTEST_CMD"; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${BLUE}Coverage report generated:${NC}"
        echo -e "  • HTML: ${GREEN}htmlcov/index.html${NC}"
        echo -e "  • XML:  ${GREEN}coverage.xml${NC}"
        echo ""
        echo -e "${BLUE}View coverage report:${NC}"
        echo -e "  open htmlcov/index.html  ${YELLOW}(macOS)${NC}"
        echo -e "  xdg-open htmlcov/index.html  ${YELLOW}(Linux)${NC}"
    fi
    
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Tests failed${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
