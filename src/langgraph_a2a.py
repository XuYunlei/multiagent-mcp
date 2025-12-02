# src/langgraph_a2a.py
"""
LangGraph SDK Integration for A2A (Agent-to-Agent) Communication
Implements agent coordination using LangGraph's state graph and message passing
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from datetime import datetime
import operator
import logging

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Fallback stubs for when LangGraph is not installed
    class StateGraph:
        pass
    class END:
        pass
    def add_messages(left, right):
        return left + right
    BaseMessage = object
    HumanMessage = object
    AIMessage = object
    SystemMessage = object

from .a2a_specs import get_agent_card, AgentCard
from .agents import AgentType, MessageType, AgentMessage, SupportAgent, RouterAgent, CustomerDataAgent
from .mcp_http_client import MCPHTTPClient

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State structure for LangGraph agent coordination"""
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    query_id: str
    current_agent: str
    agent_responses: Dict[str, Any]
    coordination_log: List[str]
    customer_info: Optional[Dict[str, Any]]
    final_response: Optional[str]
    needs_support_after_data: bool


class LangGraphA2ACoordinator:
    """A2A Coordinator using LangGraph SDK for agent orchestration"""
    
    def __init__(self, mcp_client: Optional[MCPHTTPClient] = None):
        if not LANGGRAPH_AVAILABLE:
            raise ImportError(
                "LangGraph SDK is required. Install with: pip install langgraph langchain-core"
            )
        self.mcp_client = mcp_client or MCPHTTPClient()
        # Initialize MCP connection
        try:
            self.mcp_client.initialize()
        except Exception as e:
            logger.warning(f"MCP initialization failed: {e}")
        # Create agent instances for proper response generation
        self.customer_data_agent = CustomerDataAgent(self.mcp_client)
        self.support_agent = SupportAgent(self.mcp_client)
        self.router_agent = RouterAgent(self.customer_data_agent, self.support_agent)
        self.graph = self._build_graph()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph state graph for agent coordination"""
        workflow = StateGraph(AgentState)
        
        # Add nodes for each agent
        workflow.add_node("router", self._router_node)
        workflow.add_node("customer_data", self._customer_data_node)
        workflow.add_node("support", self._support_node)
        workflow.add_node("synthesize", self._synthesize_node)
        
        # Define edges
        workflow.set_entry_point("router")
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "customer_data": "customer_data",
                "support": "support",
                "synthesize": "synthesize",
                "end": END
            }
        )
        # After customer_data, check if we need support too
        workflow.add_conditional_edges(
            "customer_data",
            self._after_customer_data_decision,
            {
                "support": "support",
                "synthesize": "synthesize"
            }
        )
        workflow.add_edge("support", "synthesize")
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    def _router_node(self, state: AgentState) -> AgentState:
        """Router agent node - analyzes query and routes to appropriate agents"""
        self.logger.info(f"🔵 ROUTER: Processing query: {state['query']}")
        
        query = state["query"]
        query_lower = query.lower()
        
        # Analyze intent
        needs_customer_data = any(word in query_lower for word in ["customer", "account", "id", "info", "information"])
        needs_support = any(word in query_lower for word in ["help", "support", "issue", "ticket", "upgrade", "cancel", "billing"])
        
        # Extract customer ID
        import re
        customer_id = None
        id_match = re.search(r'(?:id|customer)\s+(\d+)', query_lower)
        if not id_match:
            # Try to find standalone numbers
            id_match = re.search(r'\b(\d+)\b', query)
        if id_match:
            customer_id = int(id_match.group(1))
        
        state["coordination_log"].append(f"Router → Analyzing query intent")
        state["current_agent"] = "router"
        
        # Determine routing - if both customer data and support needed, get customer data first
        if needs_customer_data and customer_id:
            state["coordination_log"].append(f"Router → Routing to Customer Data Agent")
            state["messages"].append(SystemMessage(content=f"Get customer data for ID {customer_id}"))
            # Store that we also need support
            if needs_support:
                state["needs_support_after_data"] = True
        elif needs_support:
            state["coordination_log"].append(f"Router → Routing to Support Agent")
            state["messages"].append(SystemMessage(content=f"Handle support query: {query}"))
        elif needs_customer_data:
            # Customer data query without specific ID
            state["coordination_log"].append(f"Router → Routing to Customer Data Agent")
            state["messages"].append(SystemMessage(content=f"Handle customer data query: {query}"))
        else:
            state["coordination_log"].append(f"Router → Direct response")
        
        return state
    
    def _customer_data_node(self, state: AgentState) -> AgentState:
        """Customer Data Agent node - handles data operations via MCP"""
        self.logger.info("🟢 CUSTOMER DATA: Processing request")
        
        messages = state["messages"]
        last_message = messages[-1] if messages else None
        
        if last_message and isinstance(last_message, SystemMessage):
            content = last_message.content
            if "customer data" in content.lower() or "id" in content.lower():
                # Extract customer ID from message or original query
                import re
                id_match = re.search(r'id\s+(\d+)', content.lower())
                if not id_match:
                    # Try extracting from original query
                    query = state.get("query", "")
                    id_match = re.search(r'(?:id|customer)\s+(\d+)', query.lower())
                    if not id_match:
                        id_match = re.search(r'\b(\d+)\b', query)
                
                if id_match:
                    customer_id = int(id_match.group(1))
                    state["coordination_log"].append(f"Data Agent → Fetching customer {customer_id} via MCP")
                    # Call MCP HTTP client
                    try:
                        customer_info = self.mcp_client.get_customer(customer_id)
                        if customer_info:
                            state["customer_info"] = customer_info
                            state["agent_responses"]["customer_data"] = customer_info
                            state["coordination_log"].append(f"Data Agent → Customer data retrieved via MCP")
                        else:
                            state["coordination_log"].append(f"Data Agent → Customer {customer_id} not found")
                    except Exception as e:
                        self.logger.error(f"MCP call failed: {e}")
                        state["coordination_log"].append(f"Data Agent → MCP error: {e}")
        
        state["current_agent"] = "customer_data"
        state["messages"].append(AIMessage(content="Customer data retrieved via MCP"))
        
        return state
    
    def _support_node(self, state: AgentState) -> AgentState:
        """Support Agent node - handles support queries"""
        self.logger.info("🟡 SUPPORT: Processing request")
        
        query = state["query"]
        customer_info = state.get("customer_info")
        
        state["coordination_log"].append(f"Support Agent → Generating response")
        
        # Use actual SupportAgent to generate proper response
        support_response = self.support_agent._generate_support_response(query, customer_info)
        response_text = support_response.get("response", "I'm here to assist you. How can I help today?")
        
        state["agent_responses"]["support"] = {
            "response": response_text,
            "actions": support_response.get("actions", []),
            "customer_tier": support_response.get("customer_tier", "")
        }
        state["current_agent"] = "support"
        state["messages"].append(AIMessage(content=response_text))
        
        return state
    
    def _synthesize_node(self, state: AgentState) -> AgentState:
        """Synthesize responses from multiple agents"""
        self.logger.info("🔄 SYNTHESIZING: Combining agent responses")
        
        responses = state["agent_responses"]
        coordination_log = state["coordination_log"]
        query = state.get("query", "")
        
        # Combine responses intelligently
        final_parts = []
        
        # If we have customer data, format it nicely
        if "customer_data" in responses:
            customer = responses["customer_data"]
            if isinstance(customer, dict) and customer.get("id"):
                # Format customer information
                customer_info_lines = [
                    f"Customer Information:",
                    f"  ID: {customer.get('id')}",
                    f"  Name: {customer.get('name', 'N/A')}",
                    f"  Email: {customer.get('email', 'N/A')}",
                    f"  Phone: {customer.get('phone', 'N/A')}",
                    f"  Status: {customer.get('status', 'N/A')}"
                ]
                final_parts.append("\n".join(customer_info_lines))
        
        # Support response should be the main response
        if "support" in responses:
            support = responses["support"]
            support_response = support.get("response", "")
            if support_response:
                final_parts.append(support_response)
        
        # If no specific responses, generate a helpful default
        if not final_parts:
            if "customer_data" in responses:
                final_parts.append("Customer information retrieved successfully.")
            else:
                final_parts.append("I'm here to assist you. How can I help today?")
        
        state["final_response"] = "\n".join(final_parts) if final_parts else "Response generated"
        state["coordination_log"].append("Synthesize → Final response ready")
        
        return state
    
    def _route_decision(self, state: AgentState) -> str:
        """Decision function for initial routing"""
        messages = state["messages"]
        if not messages:
            return "end"
        
        last_message = messages[-1]
        
        # Initial routing based on message content
        if isinstance(last_message, SystemMessage):
            content = last_message.content.lower()
            if "customer data" in content or "id" in content:
                return "customer_data"
            elif "support" in content:
                return "support"
        
        return "synthesize"
    
    def _after_customer_data_decision(self, state: AgentState) -> str:
        """Decision function after customer data is retrieved"""
        # Check if we flagged that support is needed
        if state.get("needs_support_after_data", False):
            return "support"
        
        query = state.get("query", "").lower()
        
        # If query needs support (help, upgrade, cancel, etc.), route to support
        if any(word in query for word in ["help", "support", "upgrade", "upgrading", "cancel", "billing", "issue", "problem", "ticket"]):
            return "support"
        else:
            return "synthesize"
    
    def coordinate(self, query: str, query_id: Optional[str] = None) -> Dict[str, Any]:
        """Coordinate agents using LangGraph with RouterAgent for complex queries"""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph SDK is required")
        
        query_id = query_id or datetime.now().isoformat()
        
        # For complex queries, use RouterAgent's full logic
        # LangGraph provides the A2A framework, but RouterAgent handles the actual coordination
        query_lower = query.lower()
        is_complex_query = any(phrase in query_lower for phrase in [
            "all active customers", "open tickets", "high-priority tickets", "premium customers",
            "update", "ticket history", "all tickets"
        ])
        
        if is_complex_query:
            # Use RouterAgent for complex multi-step queries
            try:
                result = self.router_agent.process_query(query)
                return {
                    "query": query,
                    "query_id": query_id,
                    "response": result.get("response", "No response generated"),
                    "coordination_log": result.get("coordination_log", []),
                    "customer_info": result.get("customer_info"),
                    "success": result.get("success", True),
                    "scenario": "LangGraph A2A Coordination (via RouterAgent)"
                }
            except Exception as e:
                logger.error(f"RouterAgent error: {e}", exc_info=True)
                # Fallback to simple LangGraph flow
                initial_state: AgentState = {
                    "messages": [HumanMessage(content=query)],
                    "query": query,
                    "query_id": query_id,
                    "current_agent": "router",
                    "agent_responses": {},
                    "coordination_log": [],
                    "customer_info": None,
                    "final_response": None,
                    "needs_support_after_data": False
                }
                final_state = self.graph.invoke(initial_state)
                return {
                    "query": query,
                    "query_id": query_id,
                    "response": final_state.get("final_response", "Error processing query"),
                    "coordination_log": final_state.get("coordination_log", []),
                    "customer_info": final_state.get("customer_info"),
                    "success": True,
                    "scenario": "LangGraph A2A Coordination (fallback)"
                }
        
        # For simpler queries, use LangGraph state graph
        initial_state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "query_id": query_id,
            "current_agent": "router",
            "agent_responses": {},
            "coordination_log": [],
            "customer_info": None,
            "final_response": None,
            "needs_support_after_data": False
        }
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        return {
            "query": query,
            "query_id": query_id,
            "response": final_state.get("final_response", "No response generated"),
            "coordination_log": final_state.get("coordination_log", []),
            "customer_info": final_state.get("customer_info"),
            "success": True,
            "scenario": "LangGraph A2A Coordination"
        }


# Export coordinator if LangGraph is available
if LANGGRAPH_AVAILABLE:
    def create_a2a_coordinator(mcp_client: Optional[MCPHTTPClient] = None):
        """Factory function to create LangGraph A2A coordinator"""
        return LangGraphA2ACoordinator(mcp_client)
else:
    def create_a2a_coordinator(mcp_client: Optional[MCPHTTPClient] = None):
        """Fallback when LangGraph is not available"""
        logger.warning("LangGraph SDK not available. Install with: pip install langgraph langchain-core")
        return None

