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
    BaseMessage = object
    HumanMessage = object
    AIMessage = object
    SystemMessage = object

from .a2a_specs import get_agent_card, AgentCard
from .agents import AgentType, MessageType, AgentMessage
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
        workflow.add_edge("customer_data", "synthesize")
        workflow.add_edge("support", "synthesize")
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    def _router_node(self, state: AgentState) -> AgentState:
        """Router agent node - analyzes query and routes to appropriate agents"""
        self.logger.info(f"🔵 ROUTER: Processing query: {state['query']}")
        
        query = state["query"]
        query_lower = query.lower()
        
        # Analyze intent
        needs_customer_data = any(word in query_lower for word in ["customer", "account", "id", "info"])
        needs_support = any(word in query_lower for word in ["help", "support", "issue", "ticket"])
        
        # Extract customer ID
        import re
        customer_id = None
        id_match = re.search(r'(?:id|customer)\s+(\d+)', query_lower)
        if id_match:
            customer_id = int(id_match.group(1))
        
        state["coordination_log"].append(f"Router → Analyzing query intent")
        state["current_agent"] = "router"
        
        # Determine routing
        if needs_customer_data and customer_id:
            state["coordination_log"].append(f"Router → Routing to Customer Data Agent")
            state["messages"].append(SystemMessage(content=f"Get customer data for ID {customer_id}"))
        elif needs_support:
            state["coordination_log"].append(f"Router → Routing to Support Agent")
            state["messages"].append(SystemMessage(content=f"Handle support query: {query}"))
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
                # Extract customer ID
                import re
                id_match = re.search(r'id\s+(\d+)', content.lower())
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
        
        # Generate support response
        response = f"I can help you with: {query}"
        if customer_info:
            response += f" (Customer: {customer_info.get('name', 'N/A')})"
        
        state["agent_responses"]["support"] = {"response": response}
        state["current_agent"] = "support"
        state["messages"].append(AIMessage(content=response))
        
        return state
    
    def _synthesize_node(self, state: AgentState) -> AgentState:
        """Synthesize responses from multiple agents"""
        self.logger.info("🔄 SYNTHESIZING: Combining agent responses")
        
        responses = state["agent_responses"]
        coordination_log = state["coordination_log"]
        
        # Combine responses
        final_parts = []
        if "customer_data" in responses:
            customer = responses["customer_data"]
            final_parts.append(f"Customer Information: {customer.get('name', 'N/A')}")
        
        if "support" in responses:
            support = responses["support"]
            final_parts.append(support.get("response", ""))
        
        state["final_response"] = "\n".join(final_parts) if final_parts else "Response generated"
        state["coordination_log"].append("Synthesize → Final response ready")
        
        return state
    
    def _route_decision(self, state: AgentState) -> str:
        """Decision function for routing"""
        messages = state["messages"]
        if not messages:
            return "end"
        
        last_message = messages[-1]
        if isinstance(last_message, SystemMessage):
            content = last_message.content.lower()
            if "customer data" in content or "id" in content:
                return "customer_data"
            elif "support" in content:
                return "support"
        
        return "synthesize"
    
    def coordinate(self, query: str, query_id: Optional[str] = None) -> Dict[str, Any]:
        """Coordinate agents using LangGraph"""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph SDK is required")
        
        query_id = query_id or datetime.now().isoformat()
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "query_id": query_id,
            "current_agent": "router",
            "agent_responses": {},
            "coordination_log": [],
            "customer_info": None,
            "final_response": None
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

