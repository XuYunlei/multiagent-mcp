# A2A (Agent-to-Agent) Specifications

## Overview

This system implements A2A (Agent-to-Agent) communication protocol with proper agent cards, tasks, and capabilities. Each agent exposes an A2A-compliant interface that can be discovered and used by other agents.

## Agent Cards

Each agent has an **Agent Card** that defines:
- **Agent ID**: Unique identifier
- **Name**: Human-readable name
- **Description**: What the agent does
- **Capabilities**: List of capabilities (e.g., data_retrieval, ticket_management)
- **Tasks**: Available tasks with input/output schemas
- **Endpoint**: HTTP endpoint for A2A communication

## Available Agents

### 1. Router Agent
- **ID**: `router_agent`
- **Capabilities**: `query_routing`, `coordination`
- **Tasks**:
  - `route_query` - Analyze and route queries
  - `coordinate_agents` - Coordinate multiple agents
- **Endpoint**: `/router/process`

### 2. Customer Data Agent
- **ID**: `customer_data_agent`
- **Capabilities**: `data_retrieval`, `data_update`
- **Tasks**:
  - `get_customer` - Retrieve customer by ID
  - `list_customers` - List customers by status
  - `update_customer` - Update customer information
  - `get_customer_history` - Get customer ticket history
- **Endpoint**: `/customer_data/process`

### 3. Support Agent
- **ID**: `support_agent`
- **Capabilities**: `ticket_management`, `support_response`
- **Tasks**:
  - `handle_support` - Handle support queries
  - `create_ticket` - Create support tickets
  - `get_tickets_by_priority` - Get tickets by priority
  - `check_can_handle` - Check if agent can handle a query
- **Endpoint**: `/support/process`

## Accessing Agent Cards

### Via HTTP Endpoints

Each agent service exposes an `/agent-card` endpoint:

```bash
# Router Agent Card
curl http://localhost:8000/agents

# Customer Data Agent Card
curl http://localhost:8001/agent-card

# Support Agent Card
curl http://localhost:8002/agent-card
```

### Programmatically

```python
from src.a2a_specs import get_agent_card, list_all_agents

# Get specific agent card
card = get_agent_card("customer_data_agent")
print(card.to_dict())

# List all agents
all_agents = list_all_agents()
```

## Task Execution

Tasks are executed via A2A messages:

```python
from src.agents import AgentMessage, AgentType, MessageType

message = AgentMessage(
    from_agent=AgentType.ROUTER,
    to_agent=AgentType.CUSTOMER_DATA,
    message_type=MessageType.REQUEST,
    content={
        "action": "get_customer",
        "customer_id": 1
    }
)

response = customer_data_agent.process(message)
```

## Agent Discovery

Agents can discover other agents and their capabilities:

```python
from src.a2a_specs import find_agent_for_task

# Find agent that can handle a task
agent_id = find_agent_for_task("get_customer")
# Returns: "customer_data_agent"
```

## A2A Protocol Structure

### Message Format

```json
{
  "from": "router_agent",
  "to": "customer_data_agent",
  "type": "request",
  "content": {
    "action": "get_customer",
    "customer_id": 1
  },
  "query_id": "unique-query-id",
  "timestamp": "2024-01-01T00:00:00"
}
```

### Message Types

- `query` - Initial query
- `request` - Request for action
- `response` - Response to request
- `escalation` - Escalation to another agent
- `coordination` - Multi-agent coordination

## Integration with MCP

Agents use MCP (Model Context Protocol) for data access:
- Agents don't access the database directly
- All data operations go through the MCP server
- MCP provides tools that agents can call

## Compliance

This implementation provides:
- ✅ Agent cards with capabilities and tasks
- ✅ Task schemas (input/output)
- ✅ Agent discovery mechanisms
- ✅ A2A message protocol
- ✅ HTTP endpoints for agent communication
- ✅ Independent agent services

## LangGraph SDK Integration

This system integrates **LangGraph SDK** for A2A coordination:

- **State Graphs**: Agent workflows defined as state machines
- **Message Passing**: LangChain messages for structured communication
- **Conditional Routing**: Dynamic agent selection based on query analysis
- **MCP Integration**: LangGraph nodes use MCP HTTP client for data access

### Usage

The system automatically uses LangGraph if installed:

```bash
pip install langgraph langchain-core
```

Check if LangGraph is active:
```bash
curl http://localhost:8000/health
# Response includes: "a2a_framework": "LangGraph SDK"
```

### Implementation

See `src/langgraph_a2a.py` for the full LangGraph implementation with:
- AgentState: Typed state structure
- State Graph: Router, Customer Data, Support, and Synthesize nodes
- Conditional edges for dynamic routing

