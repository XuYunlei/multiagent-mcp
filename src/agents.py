"""
Multi-Agent System Implementation
Includes Router Agent, Customer Data Agent, and Support Agent
with A2A coordination capabilities and MCP integration
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
import logging
import requests
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import MCP HTTP client and A2A specs
try:
    from .mcp_http_client import MCPHTTPClient
    from .a2a_specs import (
        get_agent_card, CUSTOMER_DATA_AGENT_CARD, SUPPORT_AGENT_CARD, ROUTER_AGENT_CARD
    )
except ImportError:
    # Fallback for direct script execution
    from src.mcp_http_client import MCPHTTPClient
    from src.a2a_specs import (
        get_agent_card, CUSTOMER_DATA_AGENT_CARD, SUPPORT_AGENT_CARD, ROUTER_AGENT_CARD
    )

# A2A HTTP Configuration
A2A_USE_HTTP = os.getenv("A2A_USE_HTTP", "false").lower() == "true"
A2A_CUSTOMER_DATA_URL = os.getenv("A2A_CUSTOMER_DATA_URL", "http://localhost:8001")
A2A_SUPPORT_URL = os.getenv("A2A_SUPPORT_URL", "http://localhost:8002")

# MCP Server Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8003")

class AgentType(Enum):
    ROUTER = "router"
    CUSTOMER_DATA = "customer_data"
    SUPPORT = "support"

class MessageType(Enum):
    QUERY = "query"
    REQUEST = "request"
    RESPONSE = "response"
    ESCALATION = "escalation"
    COORDINATION = "coordination"

class AgentMessage:
    """Represents a message between agents"""
    def __init__(self, from_agent: AgentType, to_agent: AgentType, 
                 message_type: MessageType, content: Dict[str, Any],
                 query_id: str = None):
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.message_type = message_type
        self.content = content
        self.query_id = query_id or datetime.now().isoformat()
        self.timestamp = datetime.now()
    
    def to_dict(self):
        return {
            "from": self.from_agent.value,
            "to": self.to_agent.value,
            "type": self.message_type.value,
            "content": self.content,
            "query_id": self.query_id,
            "timestamp": self.timestamp.isoformat()
        }

class A2AHTTPClient:
    """HTTP client for Agent-to-Agent communication"""
    
    def __init__(self, agent_url: str):
        self.agent_url = agent_url
        self.logger = logging.getLogger(f"{__name__}.A2AHTTPClient")
    
    def send_message(self, message: AgentMessage) -> AgentMessage:
        """Send A2A message via HTTP"""
        try:
            response = requests.post(
                f"{self.agent_url}/process",
                json=message.to_dict(),
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Convert back to AgentMessage
            return AgentMessage(
                from_agent=AgentType(result["from"]),
                to_agent=AgentType(result["to"]),
                message_type=MessageType(result["type"]),
                content=result["content"],
                query_id=result.get("query_id")
            )
        except Exception as e:
            self.logger.error(f"HTTP A2A communication failed: {e}")
            raise

# Use MCP HTTP Client instead of direct database access
# MCPClient is now an alias for MCPHTTPClient for backward compatibility
MCPClient = MCPHTTPClient

class CustomerDataAgent:
    """Specialist agent for customer data operations via MCP"""
    
    def __init__(self, mcp_client: Optional[MCPHTTPClient] = None):
        self.agent_type = AgentType.CUSTOMER_DATA
        self.agent_card = CUSTOMER_DATA_AGENT_CARD
        self.mcp_client = mcp_client or MCPHTTPClient(MCP_SERVER_URL)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize MCP connection
        try:
            self.mcp_client.initialize()
            self.logger.info("MCP client initialized successfully")
        except Exception as e:
            self.logger.warning(f"MCP initialization failed: {e}")
    
    def get_agent_card(self) -> Dict[str, Any]:
        """Get A2A agent card"""
        return self.agent_card.to_dict()
    
    def process(self, message: AgentMessage) -> AgentMessage:
        """Process incoming message and return response"""
        self.logger.info(f"📥 Received message: {message.message_type.value} from {message.from_agent.value}")
        self.logger.info(f"   Content: {json.dumps(message.content, indent=2)}")
        
        content = message.content
        action = content.get("action")
        
        response_content = {}
        
        if action == "get_customer":
            customer_id = content.get("customer_id")
            customer = self.mcp_client.get_customer(customer_id)
            if customer:
                response_content = {
                    "success": True,
                    "customer": customer
                }
            else:
                response_content = {
                    "success": False,
                    "error": f"Customer {customer_id} not found"
                }
        
        elif action == "list_customers":
            status = content.get("status", "active")
            limit = content.get("limit", 100)
            customers = self.mcp_client.list_customers(status, limit)
            response_content = {
                "success": True,
                "customers": customers,
                "count": len(customers)
            }
        
        elif action == "update_customer":
            customer_id = content.get("customer_id")
            data = content.get("data", {})
            success = self.mcp_client.update_customer(customer_id, data)
            response_content = {
                "success": success,
                "customer_id": customer_id
            }
        
        elif action == "get_customer_history":
            customer_id = content.get("customer_id")
            history = self.mcp_client.get_customer_history(customer_id)
            response_content = {
                "success": True,
                "history": history,
                "count": len(history)
            }
        
        elif action == "get_premium_customers":
            # Get active customers (could filter by tier in real system)
            customers = self.mcp_client.list_customers("active", 1000)
            response_content = {
                "success": True,
                "customers": customers,
                "count": len(customers)
            }
        
        else:
            response_content = {
                "success": False,
                "error": f"Unknown action: {action}"
            }
        
        response = AgentMessage(
            from_agent=self.agent_type,
            to_agent=message.from_agent,
            message_type=MessageType.RESPONSE,
            content=response_content,
            query_id=message.query_id
        )
        
        self.logger.info(f"📤 Sending response to {message.from_agent.value}")
        return response

class SupportAgent:
    """Specialist agent for customer support operations"""
    
    def __init__(self, mcp_client: Optional[MCPHTTPClient] = None):
        self.agent_type = AgentType.SUPPORT
        self.agent_card = SUPPORT_AGENT_CARD
        self.mcp_client = mcp_client or MCPHTTPClient(MCP_SERVER_URL)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize MCP connection
        try:
            self.mcp_client.initialize()
            self.logger.info("MCP client initialized successfully")
        except Exception as e:
            self.logger.warning(f"MCP initialization failed: {e}")
    
    def get_agent_card(self) -> Dict[str, Any]:
        """Get A2A agent card"""
        return self.agent_card.to_dict()
    
    def process(self, message: AgentMessage) -> AgentMessage:
        """Process incoming message and return response"""
        self.logger.info(f"📥 Received message: {message.message_type.value} from {message.from_agent.value}")
        self.logger.info(f"   Content: {json.dumps(message.content, indent=2)}")
        
        content = message.content
        action = content.get("action")
        
        response_content = {}
        
        if action == "handle_support":
            query = content.get("query", "")
            customer_info = content.get("customer_info")
            
            # Generate support response based on query and customer info
            response_content = self._generate_support_response(query, customer_info)
        
        elif action == "create_ticket":
            customer_id = content.get("customer_id")
            issue = content.get("issue")
            priority = content.get("priority", "medium")
            ticket = self.mcp_client.create_ticket(customer_id, issue, priority)
            response_content = {
                "success": True,
                "ticket": ticket
            }
        
        elif action == "get_tickets_by_priority":
            priority = content.get("priority")
            customer_ids = content.get("customer_ids")
            tickets = self.mcp_client.get_tickets_by_priority(priority, customer_ids)
            response_content = {
                "success": True,
                "tickets": tickets,
                "count": len(tickets)
            }
        
        elif action == "check_can_handle":
            query = content.get("query", "")
            # Support agent can handle most queries except complex billing/refunds
            can_handle = "refund" not in query.lower() or "billing" not in query.lower()
            response_content = {
                "can_handle": can_handle,
                "reason": "I can handle this" if can_handle else "May need billing context"
            }
        
        elif action == "get_open_tickets_for_customers":
            customer_ids = content.get("customer_ids", [])
            all_tickets = []
            for customer_id in customer_ids:
                tickets = self.mcp_client.get_customer_history(customer_id)
                open_tickets = [t for t in tickets if t.get("status") == "open"]
                all_tickets.extend(open_tickets)
            response_content = {
                "success": True,
                "tickets": all_tickets,
                "count": len(all_tickets)
            }
        
        else:
            response_content = {
                "success": False,
                "error": f"Unknown action: {action}"
            }
        
        response = AgentMessage(
            from_agent=self.agent_type,
            to_agent=message.from_agent,
            message_type=MessageType.RESPONSE,
            content=response_content,
            query_id=message.query_id
        )
        
        self.logger.info(f"📤 Sending response to {message.from_agent.value}")
        return response
    
    def _generate_support_response(self, query: str, customer_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a support response based on query"""
        query_lower = query.lower()
        
        response_text = ""
        actions = []
        
        if "upgrade" in query_lower or "premium" in query_lower:
            response_text = "I can help you upgrade your account! Our premium tier includes priority support, advanced features, and exclusive benefits."
            actions.append("Account upgrade assistance provided")
        
        elif "cancel" in query_lower:
            response_text = "I understand you'd like to cancel your subscription. Before we proceed, let me address any concerns you might have. What's the main reason for cancellation?"
            actions.append("Cancellation inquiry handled")
        
        elif "help" in query_lower or "support" in query_lower:
            response_text = "I'm here to help! What specific issue are you experiencing? I can assist with account management, technical problems, billing questions, and more."
        
        elif "billing" in query_lower:
            response_text = "I can help with billing questions. Let me look into your account details to provide accurate information."
            actions.append("Billing inquiry routed")
        
        else:
            response_text = "I'm here to assist you. How can I help today?"
        
        customer_tier = ""
        if customer_info:
            customer_tier = "premium" if customer_info.get("id") == 12345 else "standard"
        
        return {
            "success": True,
            "response": response_text,
            "customer_tier": customer_tier,
            "actions": actions,
            "customer_info": customer_info
        }

class RouterAgent:
    """Orchestrator agent that routes queries and coordinates other agents"""
    
    def __init__(self, customer_data_agent: CustomerDataAgent = None, 
                 support_agent: SupportAgent = None,
                 use_http_a2a: bool = False):
        self.agent_type = AgentType.ROUTER
        self.agent_card = ROUTER_AGENT_CARD
        self.customer_data_agent = customer_data_agent
        self.support_agent = support_agent
        self.use_http_a2a = use_http_a2a or A2A_USE_HTTP
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.max_iterations = 10
        self.current_iteration = 0
        
        # Initialize agents if not provided
        if not self.customer_data_agent:
            self.customer_data_agent = CustomerDataAgent()
        if not self.support_agent:
            self.support_agent = SupportAgent()
        
        # Initialize HTTP clients if using HTTP A2A
        if self.use_http_a2a:
            self.customer_data_client = A2AHTTPClient(A2A_CUSTOMER_DATA_URL)
            self.support_client = A2AHTTPClient(A2A_SUPPORT_URL)
            self.logger.info("Using HTTP-based A2A communication")
        else:
            self.customer_data_client = None
            self.support_client = None
    
    def get_agent_card(self) -> Dict[str, Any]:
        """Get A2A agent card"""
        return self.agent_card.to_dict()
    
    def _send_to_agent(self, agent_type: AgentType, message: AgentMessage) -> AgentMessage:
        """Send message to agent (HTTP or direct)"""
        if self.use_http_a2a:
            if agent_type == AgentType.CUSTOMER_DATA:
                return self.customer_data_client.send_message(message)
            elif agent_type == AgentType.SUPPORT:
                return self.support_client.send_message(message)
        else:
            # Direct method call
            if agent_type == AgentType.CUSTOMER_DATA and self.customer_data_agent:
                return self.customer_data_agent.process(message)
            elif agent_type == AgentType.SUPPORT and self.support_agent:
                return self.support_agent.process(message)
        
        raise ValueError(f"Cannot send message to {agent_type.value}: agent not available")
    
    def process_query(self, query: str, query_id: str = None) -> Dict[str, Any]:
        """Main entry point for processing customer queries"""
        self.logger.info("=" * 80)
        self.logger.info(f"🔵 ROUTER: Processing new query: {query}")
        self.logger.info("=" * 80)
        
        self.current_iteration = 0
        query_id = query_id or datetime.now().isoformat()
        
        # Analyze query intent
        intent = self._analyze_intent(query)
        self.logger.info(f"🔵 ROUTER: Detected intent: {intent}")
        
        # Route based on intent and coordinate agents
        result = self._route_and_coordinate(query, intent, query_id)
        
        return result
    
    def _analyze_intent(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine intent and required agents"""
        query_lower = query.lower()
        
        intent = {
            "needs_customer_data": False,
            "needs_support": False,
            "is_complex": False,
            "customer_id": None,
            "intents": []
        }
        
        # Extract customer ID if present (look for "ID X" or "customer X" or just numbers)
        import re
        # Try to find "ID 123" or "customer 123" pattern first
        id_match = re.search(r'(?:id|customer)\s+(\d+)', query_lower)
        if not id_match:
            # Then try to find any standalone number (prefer longer IDs but accept single digits)
            id_match = re.search(r'\b(\d+)\b', query)
        if id_match:
            intent["customer_id"] = int(id_match.group(1))
            intent["needs_customer_data"] = True
        
        # Detect specific intents
        if any(word in query_lower for word in ["customer", "account", "info", "information", "id"]):
            intent["needs_customer_data"] = True
            intent["intents"].append("get_customer_info")
        
        if any(word in query_lower for word in ["help", "support", "issue", "problem", "ticket"]):
            intent["needs_support"] = True
            intent["intents"].append("support")
        
        if any(word in query_lower for word in ["cancel", "billing", "refund", "charge"]):
            intent["needs_support"] = True
            intent["is_complex"] = True
            intent["intents"].append("billing_issue")
        
        if any(word in query_lower for word in ["status", "tickets", "history", "premium", "open tickets"]):
            intent["needs_customer_data"] = True
            intent["needs_support"] = True
            intent["intents"].append("ticket_query")
        
        if any(word in query_lower for word in ["update", "change", "modify"]):
            intent["needs_customer_data"] = True
            intent["intents"].append("update")
        
        if any(word in query_lower for word in ["show", "list", "all", "every"]):
            intent["is_complex"] = True
        
        if len(intent["intents"]) > 1:
            intent["is_complex"] = True
        
        return intent
    
    def _route_and_coordinate(self, query: str, intent: Dict[str, Any], query_id: str) -> Dict[str, Any]:
        """Route query and coordinate between agents"""
        self.current_iteration += 1
        
        if self.current_iteration > self.max_iterations:
            return {"error": "Maximum iterations reached", "query_id": query_id}
        
        customer_info = None
        coordination_log = []
        
        # Scenario 1: Task Allocation - Simple routing
        if not intent["is_complex"]:
            return self._handle_task_allocation(query, intent, query_id, coordination_log)
        
        # Check for complex multi-query scenarios
        query_lower = query.lower()
        if "all active customers" in query_lower and "open tickets" in query_lower:
            return self._handle_complex_ticket_query(query, intent, query_id, coordination_log)
        
        if "update" in query_lower and "ticket history" in query_lower:
            return self._handle_multi_intent_update(query, intent, query_id, coordination_log)
        
        # Scenario 2: Negotiation/Escalation
        if "billing" in " ".join(intent["intents"]) or "cancel" in query.lower():
            return self._handle_negotiation(query, intent, query_id, coordination_log)
        
        # Scenario 3: Multi-Step Coordination
        if intent["is_complex"] and len(intent["intents"]) > 1:
            return self._handle_multi_step(query, intent, query_id, coordination_log)
        
        # Fallback to task allocation
        return self._handle_task_allocation(query, intent, query_id, coordination_log)
    
    def _handle_task_allocation(self, query: str, intent: Dict[str, Any], 
                                query_id: str, coordination_log: List) -> Dict[str, Any]:
        """Handle simple task allocation scenario"""
        self.logger.info("🔵 ROUTER: Scenario 1 - Task Allocation")
        
        customer_info = None
        
        # If this is just a customer info query without support needs, handle it directly
        if intent.get("customer_id") and not intent.get("needs_support") and "get_customer_info" in intent.get("intents", []):
            self.logger.info(f"🔵 ROUTER → 🟢 DATA: Requesting customer info for ID {intent['customer_id']}")
            msg = AgentMessage(
                from_agent=AgentType.ROUTER,
                to_agent=AgentType.CUSTOMER_DATA,
                message_type=MessageType.REQUEST,
                content={"action": "get_customer", "customer_id": intent["customer_id"]},
                query_id=query_id
            )
            response = self._send_to_agent(AgentType.CUSTOMER_DATA, msg)
            coordination_log.append(f"Router → Data Agent: Get customer {intent['customer_id']}")
            
            if response.content.get("success"):
                customer_info = response.content.get("customer")
                coordination_log.append(f"Data Agent → Router: Customer data retrieved")
                
                # Format customer info response
                if customer_info:
                    response_text = f"Customer Information:\n"
                    response_text += f"  ID: {customer_info.get('id')}\n"
                    response_text += f"  Name: {customer_info.get('name')}\n"
                    response_text += f"  Email: {customer_info.get('email')}\n"
                    response_text += f"  Phone: {customer_info.get('phone')}\n"
                    response_text += f"  Status: {customer_info.get('status')}"
                else:
                    response_text = f"Customer {intent['customer_id']} not found."
                
                return {
                    "query": query,
                    "query_id": query_id,
                    "scenario": "Task Allocation",
                    "response": response_text,
                    "customer_info": customer_info,
                    "coordination_log": coordination_log,
                    "success": True
                }
            else:
                return {
                    "query": query,
                    "query_id": query_id,
                    "scenario": "Task Allocation",
                    "response": f"Error: Could not retrieve customer information for ID {intent['customer_id']}",
                    "coordination_log": coordination_log,
                    "success": False
                }
        
        # Get customer data if needed
        if intent.get("customer_id"):
            self.logger.info(f"🔵 ROUTER → 🟢 DATA: Requesting customer info for ID {intent['customer_id']}")
            msg = AgentMessage(
                from_agent=AgentType.ROUTER,
                to_agent=AgentType.CUSTOMER_DATA,
                message_type=MessageType.REQUEST,
                content={"action": "get_customer", "customer_id": intent["customer_id"]},
                query_id=query_id
            )
            response = self._send_to_agent(AgentType.CUSTOMER_DATA, msg)
            coordination_log.append(f"Router → Data Agent: Get customer {intent['customer_id']}")
            
            if response.content.get("success"):
                customer_info = response.content.get("customer")
                coordination_log.append(f"Data Agent → Router: Customer data retrieved")
        
        # Route to support agent if support is needed
        if intent.get("needs_support") or not customer_info:
            self.logger.info("🔵 ROUTER → 🟡 SUPPORT: Routing to support agent")
            msg = AgentMessage(
                from_agent=AgentType.ROUTER,
                to_agent=AgentType.SUPPORT,
                message_type=MessageType.REQUEST,
                content={
                    "action": "handle_support",
                    "query": query,
                    "customer_info": customer_info
                },
                query_id=query_id
            )
            response = self._send_to_agent(AgentType.SUPPORT, msg)
            coordination_log.append(f"Router → Support Agent: Handle support query")
            coordination_log.append(f"Support Agent → Router: Response generated")
            
            return {
                "query": query,
                "query_id": query_id,
                "scenario": "Task Allocation",
                "response": response.content.get("response", "Unable to generate response"),
                "customer_info": customer_info,
                "coordination_log": coordination_log,
                "success": True
            }
        else:
            # Just return customer info
            response_text = f"Customer Information:\n"
            response_text += f"  ID: {customer_info.get('id')}\n"
            response_text += f"  Name: {customer_info.get('name')}\n"
            response_text += f"  Email: {customer_info.get('email')}\n"
            response_text += f"  Phone: {customer_info.get('phone')}\n"
            response_text += f"  Status: {customer_info.get('status')}"
            
            return {
                "query": query,
                "query_id": query_id,
                "scenario": "Task Allocation",
                "response": response_text,
                "customer_info": customer_info,
                "coordination_log": coordination_log,
                "success": True
            }
    
    def _handle_negotiation(self, query: str, intent: Dict[str, Any],
                           query_id: str, coordination_log: List) -> Dict[str, Any]:
        """Handle negotiation/escalation scenario"""
        self.logger.info("🔵 ROUTER: Scenario 2 - Negotiation/Escalation")
        
        # Check if support can handle
        self.logger.info("🔵 ROUTER → 🟡 SUPPORT: Checking if support can handle this query")
        msg = AgentMessage(
            from_agent=AgentType.ROUTER,
            to_agent=AgentType.SUPPORT,
            message_type=MessageType.REQUEST,
            content={"action": "check_can_handle", "query": query},
            query_id=query_id
        )
        response = self._send_to_agent(AgentType.SUPPORT, msg)
        coordination_log.append(f"Router → Support: Can you handle this?")
        
        can_handle = response.content.get("can_handle", False)
        coordination_log.append(f"Support → Router: {response.content.get('reason', '')}")
        
        # Get customer context if needed
        customer_info = None
        if intent.get("customer_id"):
            self.logger.info("🔵 ROUTER → 🟢 DATA: Getting customer context for negotiation")
            msg = AgentMessage(
                from_agent=AgentType.ROUTER,
                to_agent=AgentType.CUSTOMER_DATA,
                message_type=MessageType.REQUEST,
                content={"action": "get_customer", "customer_id": intent["customer_id"]},
                query_id=query_id
            )
            response = self._send_to_agent(AgentType.CUSTOMER_DATA, msg)
            coordination_log.append(f"Router → Data Agent: Get customer context")
            
            if response.content.get("success"):
                customer_info = response.content.get("customer")
                coordination_log.append(f"Data Agent → Router: Context provided")
        
        # Generate coordinated response
        self.logger.info("🔵 ROUTER → 🟡 SUPPORT: Generating coordinated response")
        msg = AgentMessage(
            from_agent=AgentType.ROUTER,
            to_agent=AgentType.SUPPORT,
            message_type=MessageType.REQUEST,
            content={
                "action": "handle_support",
                "query": query,
                "customer_info": customer_info
            },
            query_id=query_id
        )
        response = self._send_to_agent(AgentType.SUPPORT, msg)
        coordination_log.append(f"Router → Support: Generate response with context")
        coordination_log.append(f"Support → Router: Coordinated response ready")
        
        return {
            "query": query,
            "query_id": query_id,
            "scenario": "Negotiation/Escalation",
            "response": response.content.get("response", "Unable to generate response"),
            "customer_info": customer_info,
            "negotiation": {
                "support_can_handle": can_handle,
                "context_provided": customer_info is not None
            },
            "coordination_log": coordination_log,
            "success": True
        }
    
    def _handle_multi_step(self, query: str, intent: Dict[str, Any],
                          query_id: str, coordination_log: List) -> Dict[str, Any]:
        """Handle multi-step coordination scenario"""
        self.logger.info("🔵 ROUTER: Scenario 3 - Multi-Step Coordination")
        
        # Step 1: Get premium/active customers
        self.logger.info("🔵 ROUTER → 🟢 DATA: Getting premium customers")
        msg = AgentMessage(
            from_agent=AgentType.ROUTER,
            to_agent=AgentType.CUSTOMER_DATA,
            message_type=MessageType.REQUEST,
            content={"action": "get_premium_customers"},
            query_id=query_id
        )
        response = self._send_to_agent(AgentType.CUSTOMER_DATA, msg)
        coordination_log.append(f"Router → Data Agent: Get premium customers")
        
        customers = response.content.get("customers", [])
        customer_ids = [c["id"] for c in customers]
        coordination_log.append(f"Data Agent → Router: Found {len(customers)} customers")
        
        # Step 2: Get high-priority tickets for these customers
        self.logger.info("🔵 ROUTER → 🟡 SUPPORT: Getting high-priority tickets")
        msg = AgentMessage(
            from_agent=AgentType.ROUTER,
            to_agent=AgentType.SUPPORT,
            message_type=MessageType.REQUEST,
            content={
                "action": "get_tickets_by_priority",
                "priority": "high",
                "customer_ids": customer_ids
            },
            query_id=query_id
        )
        response = self._send_to_agent(AgentType.SUPPORT, msg)
        coordination_log.append(f"Router → Support: Get high-priority tickets")
        
        tickets = response.content.get("tickets", [])
        coordination_log.append(f"Support → Router: Found {len(tickets)} high-priority tickets")
        
        # Step 3: Format report
        report = self._format_ticket_report(customers, tickets)
        
        return {
            "query": query,
            "query_id": query_id,
            "scenario": "Multi-Step Coordination",
            "response": report,
            "statistics": {
                "customers_found": len(customers),
                "tickets_found": len(tickets)
            },
            "coordination_log": coordination_log,
            "success": True
        }
    
    def _handle_complex_ticket_query(self, query: str, intent: Dict[str, Any],
                                     query_id: str, coordination_log: List) -> Dict[str, Any]:
        """Handle complex query: Show all active customers who have open tickets"""
        self.logger.info("🔵 ROUTER: Handling complex ticket query")
        
        # Step 1: Get all active customers
        self.logger.info("🔵 ROUTER → 🟢 DATA: Getting all active customers")
        msg = AgentMessage(
            from_agent=AgentType.ROUTER,
            to_agent=AgentType.CUSTOMER_DATA,
            message_type=MessageType.REQUEST,
            content={"action": "list_customers", "status": "active", "limit": 1000},
            query_id=query_id
        )
        response = self._send_to_agent(AgentType.CUSTOMER_DATA, msg)
        coordination_log.append(f"Router → Data Agent: Get all active customers")
        
        customers = response.content.get("customers", [])
        customer_ids = [c["id"] for c in customers]
        coordination_log.append(f"Data Agent → Router: Found {len(customers)} active customers")
        
        # Step 2: Get open tickets for these customers
        self.logger.info("🔵 ROUTER → 🟡 SUPPORT: Getting open tickets for active customers")
        msg = AgentMessage(
            from_agent=AgentType.ROUTER,
            to_agent=AgentType.SUPPORT,
            message_type=MessageType.REQUEST,
            content={
                "action": "get_open_tickets_for_customers",
                "customer_ids": customer_ids
            },
            query_id=query_id
        )
        response = self._send_to_agent(AgentType.SUPPORT, msg)
        coordination_log.append(f"Router → Support: Get open tickets")
        
        open_tickets = response.content.get("tickets", [])
        coordination_log.append(f"Support → Router: Found {len(open_tickets)} open tickets")
        
        # Step 3: Match tickets to customers
        customers_with_tickets = {}
        for ticket in open_tickets:
            cust_id = ticket["customer_id"]
            if cust_id not in customers_with_tickets:
                customer = next((c for c in customers if c["id"] == cust_id), None)
                if customer:
                    customers_with_tickets[cust_id] = {
                        "customer": customer,
                        "tickets": []
                    }
                else:
                    continue
            customers_with_tickets[cust_id]["tickets"].append(ticket)
        
        # Format response
        report_lines = [f"Found {len(customers_with_tickets)} active customer(s) with open tickets:\n"]
        for cust_id, data in customers_with_tickets.items():
            customer = data["customer"]
            tickets = data["tickets"]
            report_lines.append(f"- {customer['name']} (ID: {cust_id}, Email: {customer.get('email', 'N/A')})")
            report_lines.append(f"  Open Tickets: {len(tickets)}")
            for ticket in tickets:
                report_lines.append(f"    • Ticket #{ticket['id']}: {ticket['issue']} (Priority: {ticket['priority']})")
            report_lines.append("")
        
        return {
            "query": query,
            "query_id": query_id,
            "scenario": "Complex Query Coordination",
            "response": "\n".join(report_lines),
            "statistics": {
                "active_customers": len(customers),
                "customers_with_open_tickets": len(customers_with_tickets),
                "total_open_tickets": len(open_tickets)
            },
            "coordination_log": coordination_log,
            "success": True
        }
    
    def _handle_multi_intent_update(self, query: str, intent: Dict[str, Any],
                                    query_id: str, coordination_log: List) -> Dict[str, Any]:
        """Handle multi-intent query: Update customer info and show ticket history"""
        self.logger.info("🔵 ROUTER: Handling multi-intent query (update + history)")
        
        customer_info = None
        
        # Get customer ID from query
        customer_id = intent.get("customer_id")
        if not customer_id:
            return {"error": "Customer ID required for updates", "query_id": query_id}
        
        # Extract update information from query
        update_data = {}
        query_lower = query.lower()
        import re
        
        # Extract email if mentioned
        email_match = re.search(r'(\S+@\S+\.\S+)', query)
        if email_match:
            update_data["email"] = email_match.group(1)
        
        actions = []
        
        # Step 1: Update customer if update requested
        if update_data:
            self.logger.info(f"🔵 ROUTER → 🟢 DATA: Updating customer {customer_id}")
            msg = AgentMessage(
                from_agent=AgentType.ROUTER,
                to_agent=AgentType.CUSTOMER_DATA,
                message_type=MessageType.REQUEST,
                content={"action": "update_customer", "customer_id": customer_id, "data": update_data},
                query_id=query_id
            )
            response = self._send_to_agent(AgentType.CUSTOMER_DATA, msg)
            coordination_log.append(f"Router → Data Agent: Update customer {customer_id}")
            
            if response.content.get("success"):
                actions.append(f"Updated customer {customer_id}: {update_data}")
                coordination_log.append(f"Data Agent → Router: Update successful")
        
        # Step 2: Get customer info
        self.logger.info(f"🔵 ROUTER → 🟢 DATA: Getting updated customer info")
        msg = AgentMessage(
            from_agent=AgentType.ROUTER,
            to_agent=AgentType.CUSTOMER_DATA,
            message_type=MessageType.REQUEST,
            content={"action": "get_customer", "customer_id": customer_id},
            query_id=query_id
        )
        response = self._send_to_agent(AgentType.CUSTOMER_DATA, msg)
        coordination_log.append(f"Router → Data Agent: Get customer info")
        
        if response.content.get("success"):
            customer_info = response.content.get("customer")
            coordination_log.append(f"Data Agent → Router: Customer data retrieved")
        
        # Step 3: Get ticket history
        self.logger.info(f"🔵 ROUTER → 🟢 DATA: Getting ticket history")
        msg = AgentMessage(
            from_agent=AgentType.ROUTER,
            to_agent=AgentType.CUSTOMER_DATA,
            message_type=MessageType.REQUEST,
            content={"action": "get_customer_history", "customer_id": customer_id},
            query_id=query_id
        )
        response = self._send_to_agent(AgentType.CUSTOMER_DATA, msg)
        coordination_log.append(f"Router → Data Agent: Get ticket history")
        
        history = response.content.get("history", [])
        coordination_log.append(f"Data Agent → Router: Found {len(history)} tickets")
        
        # Format response
        response_lines = []
        if actions:
            response_lines.append("Updates completed:")
            for action in actions:
                response_lines.append(f"  ✓ {action}")
            response_lines.append("")
        
        if customer_info:
            response_lines.append(f"Customer Information:")
            response_lines.append(f"  Name: {customer_info.get('name')}")
            response_lines.append(f"  Email: {customer_info.get('email')}")
            response_lines.append(f"  Status: {customer_info.get('status')}")
            response_lines.append("")
        
        response_lines.append(f"Ticket History ({len(history)} tickets):")
        if history:
            for ticket in history:
                response_lines.append(f"  • Ticket #{ticket['id']}: {ticket['issue']}")
                response_lines.append(f"    Status: {ticket['status']}, Priority: {ticket['priority']}")
                response_lines.append(f"    Created: {ticket.get('created_at', 'N/A')}")
        else:
            response_lines.append("  No tickets found.")
        
        return {
            "query": query,
            "query_id": query_id,
            "scenario": "Multi-Intent Query",
            "response": "\n".join(response_lines),
            "customer_info": customer_info,
            "ticket_history": history,
            "actions": actions,
            "coordination_log": coordination_log,
            "success": True
        }
    
    def _format_ticket_report(self, customers: List[Dict], tickets: List[Dict]) -> str:
        """Format a report of tickets for customers"""
        if not tickets:
            return "No high-priority tickets found for premium customers."
        
        report_lines = [f"Found {len(tickets)} high-priority ticket(s) for premium customers:\n"]
        
        for ticket in tickets:
            customer_id = ticket.get("customer_id")
            customer = next((c for c in customers if c["id"] == customer_id), None)
            customer_name = customer.get("name", f"Customer {customer_id}") if customer else f"Customer {customer_id}"
            
            report_lines.append(f"- Ticket #{ticket['id']}: {ticket['issue']}")
            report_lines.append(f"  Customer: {customer_name} (ID: {customer_id})")
            report_lines.append(f"  Status: {ticket['status']}, Priority: {ticket['priority']}")
            report_lines.append("")
        
        return "\n".join(report_lines)

