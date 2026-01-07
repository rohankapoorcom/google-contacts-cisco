#!/bin/bash
# Production build script
# Usage: ./scripts/build.sh

set -e

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Building frontend for production...${NC}"

# Navigate to frontend directory
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${GREEN}Installing dependencies...${NC}"
    npm install
fi

# Type check
echo -e "${GREEN}Running type check...${NC}"
npm run type-check

# Build for production
echo -e "${GREEN}Building production bundle...${NC}"
npm run build

cd "$PROJECT_ROOT"

echo -e "\n${GREEN}Frontend built successfully!${NC}"
echo -e "  Output: google_contacts_cisco/static/dist/"
echo -e "\nTo run the production server:"
echo -e "  uv run uvicorn google_contacts_cisco.main:app --host 0.0.0.0 --port 8000"

