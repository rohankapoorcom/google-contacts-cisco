#!/bin/bash
# Generate comprehensive coverage reports
# This script generates HTML, XML, and JSON coverage reports

set -e  # Exit on error

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Generating Coverage Reports${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Run tests with coverage
echo -e "${BLUE}Running tests with coverage...${NC}"
uv run pytest \
    --cov=google_contacts_cisco \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=xml \
    --cov-report=json \
    -v

echo ""
echo -e "${GREEN}Coverage reports generated:${NC}"
echo ""

# Check if reports exist and display info
if [ -f "coverage.xml" ]; then
    echo -e "  ✓ ${GREEN}coverage.xml${NC} - XML format for CI/CD"
    echo -e "    Size: $(du -h coverage.xml | cut -f1)"
fi

if [ -f "coverage.json" ]; then
    echo -e "  ✓ ${GREEN}coverage.json${NC} - JSON format for tools"
    echo -e "    Size: $(du -h coverage.json | cut -f1)"
fi

if [ -d "htmlcov" ]; then
    echo -e "  ✓ ${GREEN}htmlcov/${NC} - Interactive HTML report"
    FILE_COUNT=$(find htmlcov -type f | wc -l | tr -d ' ')
    echo -e "    Files: $FILE_COUNT"
    echo -e "    Index: ${GREEN}htmlcov/index.html${NC}"
fi

echo ""
echo -e "${BLUE}View HTML coverage report:${NC}"
echo -e "  ${YELLOW}open htmlcov/index.html${NC}  (macOS)"
echo -e "  ${YELLOW}xdg-open htmlcov/index.html${NC}  (Linux)"
echo -e "  ${YELLOW}python -m http.server --directory htmlcov${NC}  (any OS)"

echo ""
echo -e "${BLUE}Coverage Summary:${NC}"
uv run coverage report --precision=2

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Coverage reports ready${NC}"
echo -e "${GREEN}========================================${NC}"
