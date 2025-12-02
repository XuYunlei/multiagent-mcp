# src/a2a_specs.py
"""
A2A (Agent-to-Agent) Specifications
Implements agent cards, tasks, and capabilities per A2A protocol
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
import json


class AgentCapability(Enum):
    """Agent capabilities"""
    DATA_RETRIEVAL = "data_retrieval"
    DATA_UPDATE = "data_update"
    TICKET_MANAGEMENT = "ticket_management"
    QUERY_ROUTING = "query_routing"
    SUPPORT_RESPONSE = "support_response"
    COORDINATION = "coordination"


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentCard:
    """A2A Agent Card - defines agent capabilities and identity"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: List[AgentCapability],
        tasks: List[Dict[str, Any]],
        endpoint: Optional[str] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.tasks = tasks
        self.endpoint = endpoint
        self.version = "1.0.0"
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent card to dictionary"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": [cap.value for cap in self.capabilities],
            "tasks": self.tasks,
            "endpoint": self.endpoint,
            "created_at": self.created_at
        }
    
    def can_handle_task(self, task_name: str) -> bool:
        """Check if agent can handle a specific task"""
        return any(task.get("name") == task_name for task in self.tasks)
    
    def get_task_schema(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific task"""
        for task in self.tasks:
            if task.get("name") == task_name:
                return task.get("input_schema")
        return None


class Task:
    """A2A Task definition"""
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema or {"type": "object"}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema
        }


# Router Agent Card
ROUTER_AGENT_CARD = AgentCard(
    agent_id="router_agent",
    name="Router Agent",
    description="Orchestrator agent that routes queries and coordinates other agents",
    capabilities=[
        AgentCapability.QUERY_ROUTING,
        AgentCapability.COORDINATION
    ],
    tasks=[
        Task(
            name="route_query",
            description="Analyze query intent and route to appropriate agents",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Customer query"},
                    "query_id": {"type": "string", "description": "Unique query identifier"}
                },
                "required": ["query"]
            }
        ).to_dict(),
        Task(
            name="coordinate_agents",
            description="Coordinate multiple agents to handle complex queries",
            input_schema={
                "type": "object",
                "properties": {
                    "agents": {"type": "array", "description": "List of agent IDs to coordinate"},
                    "tasks": {"type": "array", "description": "Tasks to distribute"},
                    "query_id": {"type": "string", "description": "Query identifier"}
                },
                "required": ["agents", "tasks"]
            }
        ).to_dict()
    ],
    endpoint="/router/process"
)

# Customer Data Agent Card
CUSTOMER_DATA_AGENT_CARD = AgentCard(
    agent_id="customer_data_agent",
    name="Customer Data Agent",
    description="Specialist agent for customer data operations via MCP",
    capabilities=[
        AgentCapability.DATA_RETRIEVAL,
        AgentCapability.DATA_UPDATE
    ],
    tasks=[
        Task(
            name="get_customer",
            description="Retrieve customer information by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer ID"}
                },
                "required": ["customer_id"]
            }
        ).to_dict(),
        Task(
            name="list_customers",
            description="List customers filtered by status",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["active", "disabled"]},
                    "limit": {"type": "integer", "default": 100}
                },
                "required": ["status"]
            }
        ).to_dict(),
        Task(
            name="update_customer",
            description="Update customer information",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "phone": {"type": "string"},
                            "status": {"type": "string", "enum": ["active", "disabled"]}
                        }
                    }
                },
                "required": ["customer_id", "data"]
            }
        ).to_dict(),
        Task(
            name="get_customer_history",
            description="Get customer ticket history",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer"}
                },
                "required": ["customer_id"]
            }
        ).to_dict()
    ],
    endpoint="/customer_data/process"
)

# Support Agent Card
SUPPORT_AGENT_CARD = AgentCard(
    agent_id="support_agent",
    name="Support Agent",
    description="Specialist agent for customer support operations",
    capabilities=[
        AgentCapability.TICKET_MANAGEMENT,
        AgentCapability.SUPPORT_RESPONSE
    ],
    tasks=[
        Task(
            name="handle_support",
            description="Handle customer support queries",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Support query"},
                    "customer_info": {"type": "object", "description": "Customer context"}
                },
                "required": ["query"]
            }
        ).to_dict(),
        Task(
            name="create_ticket",
            description="Create a new support ticket",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer"},
                    "issue": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]}
                },
                "required": ["customer_id", "issue", "priority"]
            }
        ).to_dict(),
        Task(
            name="get_tickets_by_priority",
            description="Get tickets filtered by priority",
            input_schema={
                "type": "object",
                "properties": {
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "customer_ids": {"type": "array", "items": {"type": "integer"}}
                },
                "required": ["priority"]
            }
        ).to_dict(),
        Task(
            name="check_can_handle",
            description="Check if agent can handle a query",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        ).to_dict()
    ],
    endpoint="/support/process"
)


# Registry of all agent cards
AGENT_REGISTRY: Dict[str, AgentCard] = {
    "router_agent": ROUTER_AGENT_CARD,
    "customer_data_agent": CUSTOMER_DATA_AGENT_CARD,
    "support_agent": SUPPORT_AGENT_CARD
}


def get_agent_card(agent_id: str) -> Optional[AgentCard]:
    """Get agent card by ID"""
    return AGENT_REGISTRY.get(agent_id)


def list_all_agents() -> List[Dict[str, Any]]:
    """List all registered agents with their cards"""
    return [card.to_dict() for card in AGENT_REGISTRY.values()]


def find_agent_for_task(task_name: str) -> Optional[str]:
    """Find an agent that can handle a specific task"""
    for agent_id, card in AGENT_REGISTRY.items():
        if card.can_handle_task(task_name):
            return agent_id
    return None

