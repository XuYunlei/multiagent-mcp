"""
Agent Services - HTTP endpoints for individual agents
Implements A2A (Agent-to-Agent) communication protocol
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from typing import Optional

try:
    from .agents import (
        RouterAgent, CustomerDataAgent, SupportAgent, MCPHTTPClient,
        AgentMessage, AgentType, MessageType
    )
    from .a2a_specs import list_all_agents
except ImportError:
    from src.agents import (
        RouterAgent, CustomerDataAgent, SupportAgent, MCPHTTPClient,
        AgentMessage, AgentType, MessageType
    )
    from src.a2a_specs import list_all_agents

# Create separate FastAPI apps for each agent service
customer_data_app = FastAPI(title="Customer Data Agent Service")
support_app = FastAPI(title="Support Agent Service")
router_app = FastAPI(title="Router Agent Service")

# Enable CORS
for app in [customer_data_app, support_app, router_app]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Initialize agents (they will create their own MCP clients)
customer_data_agent = CustomerDataAgent()
support_agent = SupportAgent()
router_agent = RouterAgent(customer_data_agent, support_agent)


# Customer Data Agent Endpoints
@customer_data_app.post("/process")
async def customer_data_process(message: dict):
    """Process A2A message for Customer Data Agent"""
    try:
        # Convert dict to AgentMessage
        agent_msg = AgentMessage(
            from_agent=AgentType(message["from_agent"]),
            to_agent=AgentType(message["to_agent"]),
            message_type=MessageType(message["message_type"]),
            content=message["content"],
            query_id=message.get("query_id")
        )
        
        response = customer_data_agent.process(agent_msg)
        return response.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@customer_data_app.get("/health")
async def customer_data_health():
    return {"status": "healthy", "agent": "customer_data"}


@customer_data_app.get("/agent-card")
async def customer_data_agent_card():
    """Get A2A agent card"""
    return customer_data_agent.get_agent_card()


# Support Agent Endpoints
@support_app.post("/process")
async def support_process(message: dict):
    """Process A2A message for Support Agent"""
    try:
        agent_msg = AgentMessage(
            from_agent=AgentType(message["from_agent"]),
            to_agent=AgentType(message["to_agent"]),
            message_type=MessageType(message["message_type"]),
            content=message["content"],
            query_id=message.get("query_id")
        )
        
        response = support_agent.process(agent_msg)
        return response.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@support_app.get("/health")
async def support_health():
    return {"status": "healthy", "agent": "support"}


@support_app.get("/agent-card")
async def support_agent_card():
    """Get A2A agent card"""
    return support_agent.get_agent_card()


# Router Agent Endpoints
@router_app.post("/query")
async def router_query(query: dict):
    """Process query through Router Agent"""
    if "query" not in query:
        raise HTTPException(status_code=400, detail="Missing 'query' field")
    
    result = router_agent.process_query(query["query"])
    return result


@router_app.get("/health")
async def router_health():
    return {"status": "healthy", "agent": "router"}


@router_app.get("/agent-card")
async def router_agent_card():
    """Get A2A agent card"""
    return router_agent.get_agent_card()


@router_app.get("/agents")
async def list_agents():
    """List all available agents with their A2A cards"""
    return {"agents": list_all_agents()}


# Run individual agent services
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python agent_services.py [customer_data|support|router] [port]")
        sys.exit(1)
    
    agent_type = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    
    if agent_type == "customer_data":
        print(f"Starting Customer Data Agent on port {port}")
        uvicorn.run(customer_data_app, host="0.0.0.0", port=port)
    elif agent_type == "support":
        print(f"Starting Support Agent on port {port}")
        uvicorn.run(support_app, host="0.0.0.0", port=port)
    elif agent_type == "router":
        print(f"Starting Router Agent on port {port}")
        uvicorn.run(router_app, host="0.0.0.0", port=port)
    else:
        print(f"Unknown agent type: {agent_type}")

