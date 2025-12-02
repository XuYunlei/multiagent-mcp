#!/bin/bash
# Start the MCP HTTP Server

echo "Starting MCP HTTP Server on port 8003..."
cd "$(dirname "$0")/.."
python -m src.mcp_http_server

