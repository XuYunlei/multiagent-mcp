#!/bin/bash
# Start the HTTP server for Multi-Agent Customer Service System

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting HTTP Server..."
echo "Make sure the database is set up: python scripts/setup_database.py"
echo ""

# Kill any existing server on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start the server
cd "$PROJECT_ROOT"
python -m src.server

