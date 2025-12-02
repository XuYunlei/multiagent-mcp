#!/bin/bash
# Start all services independently for A2A compliance
# This demonstrates true agent independence with A2A interfaces

echo "=========================================="
echo "Starting Multi-Agent System Services"
echo "=========================================="
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down all services..."
    kill $MCP_PID $CUSTOMER_DATA_PID $SUPPORT_PID $ROUTER_PID $MAIN_PID 2>/dev/null
    exit
}

# Trap Ctrl+C
trap cleanup INT TERM

# Start MCP Server (required first)
echo "1. Starting MCP Server on port 8003..."
python -m src.mcp_http_server > /tmp/mcp_server.log 2>&1 &
MCP_PID=$!
sleep 2
if ps -p $MCP_PID > /dev/null; then
    echo "   ✅ MCP Server started (PID: $MCP_PID)"
else
    echo "   ❌ Failed to start MCP Server"
    exit 1
fi

# Start Customer Data Agent Service
echo "2. Starting Customer Data Agent Service on port 8001..."
python -m src.agent_services customer_data 8001 > /tmp/customer_data_agent.log 2>&1 &
CUSTOMER_DATA_PID=$!
sleep 1
if ps -p $CUSTOMER_DATA_PID > /dev/null; then
    echo "   ✅ Customer Data Agent started (PID: $CUSTOMER_DATA_PID)"
else
    echo "   ❌ Failed to start Customer Data Agent"
    cleanup
    exit 1
fi

# Start Support Agent Service
echo "3. Starting Support Agent Service on port 8002..."
python -m src.agent_services support 8002 > /tmp/support_agent.log 2>&1 &
SUPPORT_PID=$!
sleep 1
if ps -p $SUPPORT_PID > /dev/null; then
    echo "   ✅ Support Agent started (PID: $SUPPORT_PID)"
else
    echo "   ❌ Failed to start Support Agent"
    cleanup
    exit 1
fi

# Start Router Agent Service (optional, for full independence)
echo "4. Starting Router Agent Service on port 8004..."
python -m src.agent_services router 8004 > /tmp/router_agent.log 2>&1 &
ROUTER_PID=$!
sleep 1
if ps -p $ROUTER_PID > /dev/null; then
    echo "   ✅ Router Agent started (PID: $ROUTER_PID)"
else
    echo "   ❌ Failed to start Router Agent"
    cleanup
    exit 1
fi

# Start Main HTTP Server with HTTP A2A enabled
echo "5. Starting Main HTTP Server on port 8000..."
export A2A_USE_HTTP=true
export A2A_CUSTOMER_DATA_URL=http://localhost:8001
export A2A_SUPPORT_URL=http://localhost:8002
export A2A_ROUTER_URL=http://localhost:8004
python -m src.server > /tmp/main_server.log 2>&1 &
MAIN_PID=$!
sleep 2
if ps -p $MAIN_PID > /dev/null; then
    echo "   ✅ Main Server started (PID: $MAIN_PID)"
else
    echo "   ❌ Failed to start Main Server"
    cleanup
    exit 1
fi

echo ""
echo "=========================================="
echo "All Services Started Successfully!"
echo "=========================================="
echo ""
echo "Service Endpoints:"
echo "  • MCP Server:        http://localhost:8003"
echo "  • Customer Data:    http://localhost:8001"
echo "  • Support Agent:    http://localhost:8002"
echo "  • Router Agent:     http://localhost:8004"
echo "  • Main Server:      http://localhost:8000"
echo ""
echo "Agent Cards (A2A Interface):"
echo "  • Customer Data:    http://localhost:8001/agent-card"
echo "  • Support Agent:    http://localhost:8002/agent-card"
echo "  • Router Agent:     http://localhost:8004/agent-card"
echo "  • All Agents:       http://localhost:8000/agents"
echo ""
echo "MCP Inspector:"
echo "  Connect to: http://localhost:8003/mcp"
echo ""
echo "Logs:"
echo "  • MCP Server:        /tmp/mcp_server.log"
echo "  • Customer Data:    /tmp/customer_data_agent.log"
echo "  • Support Agent:    /tmp/support_agent.log"
echo "  • Router Agent:     /tmp/router_agent.log"
echo "  • Main Server:      /tmp/main_server.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait

