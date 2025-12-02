# Multi-Agent Customer Service System with A2A and MCP

## Overview

This project implements a multi-agent customer service system where specialized agents coordinate using Agent-to-Agent (A2A) communication and access customer data through the Model Context Protocol (MCP). The system demonstrates three key coordination scenarios: task allocation, negotiation/escalation, and multi-step coordination.

## System Architecture

The system consists of three specialized agents:

1. **Router Agent (Orchestrator)**
   - Receives and analyzes customer queries
   - Routes queries to appropriate specialist agents
   - Coordinates responses from multiple agents
   - Handles complex multi-step workflows

2. **Customer Data Agent (Specialist)**
   - Accesses customer database via MCP
   - Retrieves and updates customer information
   - Handles data validation and customer history
   - Manages customer-related queries

3. **Support Agent (Specialist)**
   - Handles general customer support queries
   - Creates and manages support tickets
   - Provides solutions and recommendations
   - Escalates complex issues when needed

## Features

- **HTTP Server with Streaming**: FastAPI-based HTTP server that accepts queries and streams responses
  - `/query` - Streaming endpoint for real-time response delivery
  - `/query/sync` - Synchronous endpoint for immediate responses
  - `/health` - Health check endpoint

- **A2A Protocol Implementation**: Agent-to-Agent communication via HTTP
  - Agents communicate using structured `AgentMessage` protocol
  - Supports both direct method calls and HTTP-based communication
  - Configurable via environment variables

- **MCP Integration**: Full HTTP-based MCP server implementation with 5 tools:
  - HTTP endpoint at `/mcp` supporting `tools/list` and `tools/call` methods
  - Testable via MCP Inspector and other MCP clients
  - All agents use MCP HTTP client (no direct database access)
  - Tools: `get_customer`, `list_customers`, `update_customer`, `create_ticket`, `get_customer_history`

- **A2A Specifications with LangGraph SDK**: Full A2A protocol implementation:
  - **LangGraph SDK Integration**: Agent coordination using LangGraph state graphs
  - **Agent Cards**: Each agent has an agent card with capabilities and tasks
  - **State Management**: LangGraph maintains state across agent interactions
  - **Message Passing**: LangChain messages for structured A2A communication
  - **Conditional Routing**: Dynamic agent selection based on query analysis
  - Agents expose `/agent-card` endpoints for discovery

- **A2A Coordination**: Three coordination patterns:
  - **Task Allocation**: Simple routing and delegation
  - **Negotiation/Escalation**: Multi-agent consultation and context gathering
  - **Multi-Step Coordination**: Complex workflows with multiple agent interactions

- **Database Schema**: SQLite database with:
  - Customers table (id, name, email, phone, status, timestamps)
  - Tickets table (id, customer_id, issue, status, priority, created_at)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup Steps

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**:
   ```bash
   python scripts/setup_database.py
   ```

   This will create a SQLite database (`customer_service.db`) in the project root with sample customer and ticket data.

## Usage

### Starting the MCP Server

**IMPORTANT**: The MCP server must be running before starting agents.

```bash
# Option 1: Using the helper script
./scripts/start_mcp_server.sh

# Option 2: Direct Python command
python -m src.mcp_http_server
```

The MCP server will start on `http://localhost:8003` with:
- MCP Endpoint: `http://localhost:8003/mcp` (JSON-RPC 2.0, MCP Inspector compatible)
- Tools List: `http://localhost:8003/tools/list`
- Tools Call: `http://localhost:8003/tools/call`
- Health Check: `http://localhost:8003/health`

### Agent Independence Architecture

This system implements **truly independent agents** with A2A interfaces. Each agent can run as a separate service, demonstrating proper A2A architecture.

#### Quick Start (All Independent Services)

The easiest way to start all services independently:

```bash
./scripts/start_all_services.sh
```

This script starts:
1. MCP Server (port 8003)
2. Customer Data Agent Service (port 8001)
3. Support Agent Service (port 8002)
4. Router Agent Service (port 8004)
5. Main HTTP Server (port 8000) with HTTP A2A enabled

#### Manual Setup (Independent Services)

For full control, start each service manually:

1. **Start MCP Server** (required first):
   ```bash
   python -m src.mcp_http_server
   ```

2. **Start Agent Services** (in separate terminals):
   ```bash
   # Terminal 2: Customer Data Agent
   python -m src.agent_services customer_data 8001
   
   # Terminal 3: Support Agent
   python -m src.agent_services support 8002
   
   # Terminal 4: Router Agent (optional)
   python -m src.agent_services router 8004
   ```

3. **Start Main Server** with HTTP A2A:
   ```bash
   export A2A_USE_HTTP=true
   export A2A_CUSTOMER_DATA_URL=http://localhost:8001
   export A2A_SUPPORT_URL=http://localhost:8002
   export A2A_ROUTER_URL=http://localhost:8004
   python -m src.server
   ```

#### Agent A2A Interfaces

Each independent agent exposes an A2A-compliant interface:

- **Customer Data Agent** (`http://localhost:8001`):
  - `/agent-card` - A2A agent card with capabilities and tasks
  - `/process` - A2A message processing endpoint
  - `/health` - Health check

- **Support Agent** (`http://localhost:8002`):
  - `/agent-card` - A2A agent card with capabilities and tasks
  - `/process` - A2A message processing endpoint
  - `/health` - Health check

- **Router Agent** (`http://localhost:8004`):
  - `/agent-card` - A2A agent card with capabilities and tasks
  - `/query` - Query processing endpoint
  - `/agents` - List all available agents
  - `/health` - Health check

#### Testing Agent Independence

Verify agents are running independently:

```bash
# Check Customer Data Agent
curl http://localhost:8001/agent-card

# Check Support Agent
curl http://localhost:8002/agent-card

# Check Router Agent
curl http://localhost:8004/agent-card

# List all agents from main server
curl http://localhost:8000/agents
```

### Running the HTTP Server (Single Process Mode)

For testing or development, you can run agents in a single process:

Start the main HTTP server with streaming support:

```bash
# Option 1: Using the helper script
./scripts/start_server.sh

# Option 2: Direct Python command
python -m src.server
```

The server will start on `http://localhost:8000` with:
- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`
- Query Endpoint: `http://localhost:8000/query` (streaming)
- Sync Query Endpoint: `http://localhost:8000/query/sync`
- Agents List: `http://localhost:8000/agents` (A2A agent cards)

### Testing HTTP Endpoints

Run the HTTP test suite:

```bash
python tests/test_http.py
```

This will test all HTTP endpoints including streaming responses.

### Running the End-to-End Demo

Run the comprehensive demonstration script (uses direct agent calls):

```bash
python tests/demo.py
```

This will execute all test scenarios:
- Scenario 1: Task Allocation
- Scenario 2: Negotiation/Escalation
- Scenario 3: Multi-Step Coordination
- Additional test cases (simple queries, complex queries, escalation, multi-intent)

### A2A Protocol Modes

The system supports two A2A communication modes:

1. **Direct Mode (Default)**: Agents communicate via direct method calls
   ```bash
   python demo.py
   ```

2. **HTTP Mode**: Agents communicate via HTTP endpoints
   ```bash
   # Set environment variable
   export A2A_USE_HTTP=true
   export A2A_CUSTOMER_DATA_URL=http://localhost:8001
   export A2A_SUPPORT_URL=http://localhost:8002
   
   # Start agent services (in separate terminals)
   python -m src.agent_services customer_data 8001
   python -m src.agent_services support 8002
   
   # Run demo with HTTP A2A
   python tests/demo.py
   ```

### Test Scenarios

The system successfully handles these query types:

1. **Simple Query**: "Get customer information for ID 5"
   - Single agent, straightforward MCP call

2. **Coordinated Query**: "I'm customer 12345 and need help upgrading my account"
   - Multiple agents coordinate: data fetch + support response

3. **Complex Query**: "Show me all active customers who have open tickets"
   - Requires coordination between data and support agents

4. **Escalation**: "I've been charged twice, please refund immediately!"
   - Router identifies urgency and routes appropriately

5. **Multi-Intent**: "Update my email to new@email.com and show my ticket history"
   - Parallel task execution and coordination

## Project Structure

```
multiagent-mcp/
├── src/                         # Source code
│   ├── __init__.py
│   ├── agents.py                # Agent implementations and A2A coordination
│   ├── mcp_http_server.py       # MCP HTTP server implementation
│   ├── mcp_http_client.py       # MCP HTTP client for agents
│   ├── a2a_specs.py             # A2A agent cards and specifications
│   ├── langgraph_a2a.py         # LangGraph SDK integration for A2A
│   ├── agent_services.py        # Individual agent HTTP services (A2A protocol)
│   └── server.py                # HTTP server with streaming support
├── scripts/                     # Utility scripts
│   ├── setup_database.py        # Database initialization script
│   ├── start_server.sh          # Server startup helper
│   └── start_mcp_server.sh      # MCP server startup helper
├── tests/                       # Test files
│   ├── demo.py                  # End-to-end demonstration script
│   ├── test_http.py             # HTTP endpoint test suite
│   └── validate_pipeline.py     # Comprehensive pipeline validation
├── docs/                        # Documentation
│   ├── A2A_SPECIFICATIONS.md    # A2A protocol, agent cards, and LangGraph
│   └── CONCLUSION.md            # Learning outcomes and challenges
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── .gitignore                   # Git ignore rules
└── customer_service.db          # SQLite database (created after setup, gitignored)
```

## How It Works

### HTTP Server Architecture

The system provides a FastAPI-based HTTP server that:
1. Accepts customer queries via POST `/query` (streaming) or `/query/sync` (synchronous)
2. Routes queries through the Router Agent
3. Streams agent responses in real-time using Server-Sent Events (SSE)
4. Returns structured JSON responses with coordination logs

### A2A Communication Flow

1. **Router receives query** (via HTTP or direct call) and analyzes intent
2. **Router routes to appropriate agents** based on query complexity
3. **Agents communicate** via structured messages (AgentMessage) using:
   - Direct method calls (default mode)
   - HTTP endpoints (when `A2A_USE_HTTP=true`)
4. **Router coordinates responses** from multiple agents
5. **Final response** is synthesized and returned (streamed via HTTP or returned directly)

### A2A Protocol

The system implements a standard A2A protocol using `AgentMessage`:
- **Message Structure**: `from_agent`, `to_agent`, `message_type`, `content`, `query_id`, `timestamp`
- **Message Types**: `QUERY`, `REQUEST`, `RESPONSE`, `ESCALATION`, `COORDINATION`
- **Agent Types**: `ROUTER`, `CUSTOMER_DATA`, `SUPPORT`
- **Transport**: HTTP POST requests to `/process` endpoint (when using HTTP mode)

### Example: Task Allocation Scenario

```
Query: "I need help with my account, customer ID 12345"

1. Router Agent → Customer Data Agent: "Get customer info for ID 12345"
2. Customer Data Agent → Router: Returns customer data
3. Router Agent → Support Agent: "Handle support for customer 12345"
4. Support Agent → Router: Returns support response
5. Router → Final response to user
```

### Example: Multi-Step Coordination

```
Query: "What's the status of all high-priority tickets for premium customers?"

1. Router → Customer Data Agent: "Get all premium customers"
2. Customer Data Agent → Router: Returns customer list
3. Router → Support Agent: "Get high-priority tickets for these IDs"
4. Support Agent → Router: Returns ticket list
5. Router synthesizes report from both responses
```

## Logging

The system includes comprehensive logging that shows:
- Agent-to-agent message flows
- Query processing steps
- Coordination patterns
- Response generation

Logs are output to the console with timestamps and agent identifiers.

## Database Schema

### Customers Table
- `id` INTEGER PRIMARY KEY
- `name` TEXT NOT NULL
- `email` TEXT
- `phone` TEXT
- `status` TEXT ('active' or 'disabled')
- `created_at` TIMESTAMP
- `updated_at` TIMESTAMP

### Tickets Table
- `id` INTEGER PRIMARY KEY
- `customer_id` INTEGER (FK to customers.id)
- `issue` TEXT NOT NULL
- `status` TEXT ('open', 'in_progress', 'resolved')
- `priority` TEXT ('low', 'medium', 'high')
- `created_at` DATETIME

## MCP Tools Implementation

The MCP HTTP server provides five tools accessible via HTTP endpoints:

1. **get_customer**: Retrieves a single customer by ID
2. **list_customers**: Lists customers filtered by status with optional limit
3. **update_customer**: Updates customer information (name, email, phone, status)
4. **create_ticket**: Creates a new support ticket
5. **get_customer_history**: Retrieves all tickets for a customer

### Testing MCP Server with MCP Inspector

The MCP server is fully compatible with MCP Inspector and other MCP clients:

1. Start the MCP server: `python -m src.mcp_http_server`
2. Connect MCP Inspector to `http://localhost:8003/mcp`
3. Test `tools/list` and `tools/call` methods

**MCP Protocol Endpoints**:
- `POST /mcp` - Client-to-server messages (returns JSON-RPC 2.0, MCP Inspector compatible)
  - Supports: `initialize`, `tools/list`, `tools/call`
  - Returns JSON responses (not SSE) for standard MCP client compatibility
- `GET /mcp` - Server-to-client streaming (SSE) for long-lived connections
- `GET /tools/list` - Direct tools list (for testing)
- `POST /tools/call` - Direct tool call (for testing)

**MCP Inspector Compatibility**:
- ✅ POST `/mcp` returns JSON responses (standard MCP protocol)
- ✅ JSON-RPC 2.0 format for all responses
- ✅ CORS enabled for web-based clients
- ✅ Session management via `Mcp-Session-Id` header

## A2A Specifications

Each agent implements the A2A protocol with:

- **Agent Cards**: Define capabilities, tasks, and schemas
- **Task Definitions**: Input/output schemas for each task
- **Agent Discovery**: `/agent-card` endpoints for each agent
- **A2A Protocol**: Structured message format for agent communication

### Accessing Agent Cards

```bash
# List all agents
curl http://localhost:8000/agents

# Get specific agent card
curl http://localhost:8001/agent-card  # Customer Data Agent
curl http://localhost:8002/agent-card  # Support Agent
```

See [A2A_SPECIFICATIONS.md](docs/A2A_SPECIFICATIONS.md) for detailed documentation.

## API Examples

### Streaming Query (Server-Sent Events)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Get customer information for ID 5"}' \
  --no-buffer
```

### Synchronous Query

```bash
curl -X POST http://localhost:8000/query/sync \
  -H "Content-Type: application/json" \
  -d '{"query": "I need help with my account, customer ID 12345"}'
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Documentation

Additional documentation is available in the `docs/` directory:
- **[A2A_SPECIFICATIONS.md](docs/A2A_SPECIFICATIONS.md)** - A2A protocol, agent cards, and LangGraph integration
- **[CONCLUSION.md](docs/CONCLUSION.md)** - Learning outcomes and challenges

## Troubleshooting

### HTTP Server Issues

- **Port already in use**: Change port in `src/server.py` or stop other services
- **Connection refused**: Ensure server is running: `python -m src.server` or `./scripts/start_server.sh`
- **Streaming not working**: Check that client supports Server-Sent Events

### Database Issues

If you encounter database errors:
- Delete `customer_service.db` and run `python scripts/setup_database.py` again
- Ensure SQLite is available in your Python environment

### Import Errors

If you see import errors:
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.8+)

### Agent Coordination Issues

- Check the console logs for detailed A2A message flows
- Verify the database contains sample data
- Review the coordination_log in the output
- For HTTP A2A mode, ensure agent services are running on correct ports

## Assignment Compliance

✅ **MCP Server**: HTTP-based MCP server with `/mcp` endpoint  
✅ **MCP Protocol**: POST `/mcp` returns JSON-RPC 2.0 (MCP Inspector compatible)  
✅ **MCP Tools**: `tools/list` and `tools/call` methods implemented  
✅ **MCP Testability**: Fully compatible with MCP Inspector and other MCP clients  
✅ **A2A Protocol with LangGraph SDK**: Agent coordination using LangGraph state graphs  
✅ **A2A Interface**: Each agent has independent A2A interface with `/agent-card` endpoint  
✅ **A2A Specifications**: Full A2A protocol implementation (agent cards, tasks, LangGraph integration)  
✅ **Agent Independence**: Agents can run as independent services (demonstrated via `start_all_services.sh`)  
✅ **LangGraph Integration**: State graphs, message passing, conditional routing  
✅ **HTTP Server**: FastAPI server with streaming support  
✅ **Three Coordination Scenarios**: Task Allocation, Negotiation, Multi-Step  
✅ **Test Scenarios**: All 5 required test scenarios implemented and passing  
✅ **No Direct DB Access**: All agents use MCP HTTP client (proper MCP protocol)  
✅ **End-to-End Demo**: Complete demonstration script  

## Future Enhancements

Potential improvements:
- WebSocket support for bidirectional communication
- More sophisticated intent analysis using NLP
- Agent state persistence
- Multi-threaded agent execution for parallel processing
- Web interface for query submission
- Advanced error handling and retry logic
- Authentication and authorization for agent services

## License

This project is created for educational purposes as part of Assignment 5 - Multiagentic systems and MCP.

## Author

Created as part of the Multi-Agent Systems course assignment.

