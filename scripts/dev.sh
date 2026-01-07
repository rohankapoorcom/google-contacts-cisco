#!/bin/bash
# Development script to run both backend and frontend
# Usage: ./scripts/dev.sh

set -e

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting development servers...${NC}"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${BLUE}Shutting down servers...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start FastAPI backend
echo -e "${GREEN}Starting FastAPI backend on http://localhost:8000...${NC}"
uv run uvicorn google_contacts_cisco.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start Vite frontend dev server
echo -e "${GREEN}Starting Vite frontend on http://localhost:5173...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!

cd "$PROJECT_ROOT"

echo -e "\n${GREEN}Development servers started!${NC}"
echo -e "  Backend:  http://localhost:8000"
echo -e "  Frontend: http://localhost:5173"
echo -e "  API Docs: http://localhost:8000/docs"
echo -e "\nPress Ctrl+C to stop both servers.\n"

# Wait for both processes
wait

