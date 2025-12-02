# src/server.py
"""
HTTP Server for Multi-Agent Customer Service System
Provides streaming HTTP endpoints for customer queries
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from typing import Optional
import uvicorn

try:
    from .agents import RouterAgent, CustomerDataAgent, SupportAgent
    from .a2a_specs import list_all_agents
    # Try to import LangGraph A2A coordinator
    try:
        from .langgraph_a2a import create_a2a_coordinator
        langgraph_coordinator = create_a2a_coordinator()
        LANGGRAPH_AVAILABLE = langgraph_coordinator is not None
    except (ImportError, Exception) as e:
        LANGGRAPH_AVAILABLE = False
        langgraph_coordinator = None
        import logging
        logging.warning(f"LangGraph SDK not available: {e}. Install with: pip install langgraph langchain-core")
except ImportError:
    from src.agents import RouterAgent, CustomerDataAgent, SupportAgent
    from src.a2a_specs import list_all_agents
    LANGGRAPH_AVAILABLE = False
    langgraph_coordinator = None

app = FastAPI(title="Multi-Agent Customer Service System")

# Enable CORS for testing
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


def stream_agent_response(query: str):
    """Generator function to stream agent responses"""
    try:
        # Yield initial status
        yield f"data: {json.dumps({'status': 'processing', 'message': 'Analyzing query...'})}\n\n"
        
        # Process query through router
        result = router_agent.process_query(query)
        
        # Stream coordination log entries
        if result.get('coordination_log'):
            yield f"data: {json.dumps({'type': 'coordination', 'log': result['coordination_log']})}\n\n"
        
        # Stream intermediate results
        if result.get('customer_info'):
            yield f"data: {json.dumps({'type': 'customer_info', 'data': result['customer_info']})}\n\n"
        
        # Stream final response
        yield f"data: {json.dumps({'type': 'response', 'data': result.get('response', '')})}\n\n"
        
        # Stream completion
        yield f"data: {json.dumps({'status': 'complete', 'success': result.get('success', False), 'scenario': result.get('scenario', '')})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Multi-Agent Customer Service System",
        "version": "1.0",
        "endpoints": {
            "/query": "POST - Submit customer query (streaming)",
            "/query/sync": "POST - Submit customer query (synchronous)",
            "/health": "GET - Health check"
        }
    }


@app.post("/query")
async def query_stream(query: dict):
    """Streaming endpoint for customer queries"""
    if "query" not in query:
        raise HTTPException(status_code=400, detail="Missing 'query' field")
    
    customer_query = query["query"]
    
    return StreamingResponse(
        stream_agent_response(customer_query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/query/sync")
async def query_sync(query: dict):
    """Synchronous endpoint for customer queries"""
    if "query" not in query:
        raise HTTPException(status_code=400, detail="Missing 'query' field")
    
    customer_query = query["query"]
    
    # Use LangGraph A2A coordinator if available, otherwise fallback to direct agent calls
    if LANGGRAPH_AVAILABLE and langgraph_coordinator:
        result = langgraph_coordinator.coordinate(customer_query)
    else:
        result = router_agent.process_query(customer_query)
    
    return {
        "query": customer_query,
        "result": result,
        "a2a_framework": "LangGraph SDK" if LANGGRAPH_AVAILABLE else "Custom A2A"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agents": {
            "router": "active",
            "customer_data": "active",
            "support": "active"
        },
        "a2a_framework": "LangGraph SDK" if LANGGRAPH_AVAILABLE else "Custom A2A",
        "mcp_transport": "Streamable HTTP (SSE)"
    }


@app.get("/agents")
async def list_agents():
    """List all available agents with their A2A cards"""
    return {"agents": list_all_agents()}


if __name__ == "__main__":
    import os
    import sys
    
    # Add project root to path for database access
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    print("Starting HTTP Server on http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)

