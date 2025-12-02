# src/mcp_http_server.py
"""
MCP HTTP Server for Customer Service System
Implements HTTP/SSE transport with tools/list and tools/call endpoints
Compatible with MCP Inspector and other MCP clients
"""

import asyncio
import json
import sqlite3
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
import os

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Database path relative to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "customer_service.db")

app = FastAPI(title="MCP Customer Service Server")

# Enable CORS for MCP Inspector
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session management
sessions: Dict[str, Dict[str, Any]] = {}


def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)


def get_tools_list() -> List[Dict[str, Any]]:
    """Get list of available MCP tools"""
    return [
        {
            "name": "get_customer",
            "description": "Retrieve customer information by customer ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "The customer ID to retrieve"
                    }
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "list_customers",
            "description": "List customers filtered by status with optional limit",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "disabled"],
                        "description": "Filter by customer status"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of customers to return"
                    }
                },
                "required": ["status"]
            }
        },
        {
            "name": "update_customer",
            "description": "Update customer information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "The customer ID to update"
                    },
                    "data": {
                        "type": "object",
                        "description": "Customer data fields to update (name, email, phone, status)",
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
        },
        {
            "name": "create_ticket",
            "description": "Create a new support ticket",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "The customer ID for this ticket"
                    },
                    "issue": {
                        "type": "string",
                        "description": "Description of the issue"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Ticket priority level"
                    }
                },
                "required": ["customer_id", "issue", "priority"]
            }
        },
        {
            "name": "get_customer_history",
            "description": "Get all tickets for a customer",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "The customer ID to get history for"
                    }
                },
                "required": ["customer_id"]
            }
        }
    ]


async def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool calls"""
    try:
        if name == "get_customer":
            customer_id = arguments["customer_id"]
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                result = {
                    "id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "phone": row[3],
                    "status": row[4],
                    "created_at": row[5],
                    "updated_at": row[6]
                }
                return {"success": True, "result": result}
            else:
                return {"success": False, "error": f"Customer {customer_id} not found"}
        
        elif name == "list_customers":
            status = arguments["status"]
            limit = arguments.get("limit", 100)
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE status = ? LIMIT ?", (status, limit))
            rows = cursor.fetchall()
            conn.close()
            
            customers = []
            for row in rows:
                customers.append({
                    "id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "phone": row[3],
                    "status": row[4],
                    "created_at": row[5],
                    "updated_at": row[6]
                })
            return {"success": True, "result": customers}
        
        elif name == "update_customer":
            customer_id = arguments["customer_id"]
            data = arguments["data"]
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Build update query dynamically
            updates = []
            values = []
            for key, value in data.items():
                if key in ["name", "email", "phone", "status"]:
                    updates.append(f"{key} = ?")
                    values.append(value)
            
            if not updates:
                conn.close()
                return {"success": False, "error": "No valid fields to update"}
            
            values.append(datetime.now())  # updated_at
            values.append(customer_id)
            updates.append("updated_at = ?")
            
            query = f"UPDATE customers SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            
            return {"success": True, "result": {"message": f"Customer {customer_id} updated"}}
        
        elif name == "create_ticket":
            customer_id = arguments["customer_id"]
            issue = arguments["issue"]
            priority = arguments["priority"]
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tickets (customer_id, issue, status, priority, created_at) VALUES (?, ?, ?, ?, ?)",
                (customer_id, issue, "open", priority, datetime.now())
            )
            ticket_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            result = {
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "issue": issue,
                "status": "open",
                "priority": priority
            }
            return {"success": True, "result": result}
        
        elif name == "get_customer_history":
            customer_id = arguments["customer_id"]
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
            rows = cursor.fetchall()
            conn.close()
            
            tickets = []
            for row in rows:
                tickets.append({
                    "id": row[0],
                    "customer_id": row[1],
                    "issue": row[2],
                    "status": row[3],
                    "priority": row[4],
                    "created_at": row[5]
                })
            return {"success": True, "result": tickets}
        
        else:
            return {"success": False, "error": f"Unknown tool: {name}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/mcp")
async def mcp_stream_endpoint(
    mcp_session_id: Optional[str] = Header(None, alias="Mcp-Session-Id")
):
    """
    GET /mcp - Streamable HTTP transport for server-to-client messages (SSE)
    Establishes a long-lived connection for streaming responses
    """
    # Create or retrieve session
    if not mcp_session_id:
        mcp_session_id = str(uuid.uuid4())
    
    if mcp_session_id not in sessions:
        sessions[mcp_session_id] = {
            "id": mcp_session_id,
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
    
    async def event_generator():
        """Generate SSE events from session messages"""
        session = sessions[mcp_session_id]
        while True:
            # Check for new messages in session
            if session["messages"]:
                message = session["messages"].pop(0)
                yield f"data: {json.dumps(message)}\n\n"
            else:
                # Keep connection alive
                yield f": keepalive\n\n"
                await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Mcp-Session-Id": mcp_session_id,
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    mcp_session_id: Optional[str] = Header(None, alias="Mcp-Session-Id")
):
    """
    POST /mcp - HTTP transport for client-to-server messages
    Returns JSON-RPC 2.0 responses (not SSE) for MCP Inspector compatibility
    SSE streaming is available via GET /mcp
    """
    # Create or retrieve session
    if not mcp_session_id:
        mcp_session_id = str(uuid.uuid4())
    
    if mcp_session_id not in sessions:
        sessions[mcp_session_id] = {
            "id": mcp_session_id,
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
    
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")
        
        response_data = None
        
        if method == "tools/list":
            tools = get_tools_list()
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": tools
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            result = await call_tool(tool_name, arguments)
            
            if result["success"]:
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result["result"], indent=2, default=str)
                            }
                        ]
                    }
                }
            else:
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": result.get("error", "Internal error")
                    }
                }
        
        elif method == "initialize":
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "customer-service-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        
        else:
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
        
        # Store in session for GET /mcp streaming (optional)
        if response_data:
            sessions[mcp_session_id]["messages"].append(response_data)
        
        # Return JSON response directly (not SSE) for MCP Inspector compatibility
        return JSONResponse(
            content=response_data if response_data else {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Unknown error"
                }
            },
            headers={"Mcp-Session-Id": mcp_session_id}
        )
    
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": body.get("id", None) if 'body' in locals() else None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }
        if mcp_session_id in sessions:
            sessions[mcp_session_id]["messages"].append(error_response)
        
        return JSONResponse(
            content=error_response,
            headers={"Mcp-Session-Id": mcp_session_id},
            status_code=500
        )


@app.get("/tools/list")
async def tools_list_endpoint():
    """Direct endpoint for listing tools (for testing)"""
    return JSONResponse(content={"tools": get_tools_list()})


@app.post("/tools/call")
async def tools_call_endpoint(request: Request):
    """Direct endpoint for calling tools (for testing)"""
    try:
        body = await request.json()
        tool_name = body.get("name")
        arguments = body.get("arguments", {})
        
        result = await call_tool(tool_name, arguments)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-server"}


if __name__ == "__main__":
    print("Starting MCP HTTP Server on http://localhost:8003")
    print("MCP HTTP Transport (MCP Inspector Compatible):")
    print("  POST /mcp - Client-to-server messages (returns JSON)")
    print("  GET /mcp  - Server-to-client streaming (SSE)")
    print("Direct Endpoints:")
    print("  GET /tools/list - List available tools")
    print("  POST /tools/call - Call a tool directly")
    print("  GET /health - Health check")
    uvicorn.run(app, host="0.0.0.0", port=8003)

