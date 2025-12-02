# src/mcp_http_client.py
"""
MCP HTTP Client for accessing MCP server tools
Replaces direct database access with proper MCP protocol calls
"""

import requests
import json
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class MCPHTTPClient:
    """HTTP client for MCP server communication"""
    
    def __init__(self, mcp_server_url: str = "http://localhost:8003"):
        self.mcp_server_url = mcp_server_url
        self.session_id: Optional[str] = None
        self.request_id = 0
    
    def _get_request_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    def _call_mcp(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make MCP protocol call"""
        if params is None:
            params = {}
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": method,
            "params": params
        }
        
        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        
        try:
            response = requests.post(
                f"{self.mcp_server_url}/mcp",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '')
            
            # POST /mcp now returns JSON directly (not SSE) for MCP Inspector compatibility
            if 'application/json' in content_type or 'text/json' in content_type:
                result = response.json()
            elif 'text/event-stream' in content_type:
                # Fallback: Parse SSE format if server still returns it
                text = response.text
                lines = text.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('data: '):
                        json_str = line[6:]  # Remove "data: " prefix
                        try:
                            result = json.loads(json_str)
                            break
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse SSE JSON: {e}, line: {line[:100]}")
                            continue
                else:
                    raise Exception(f"No valid data found in SSE response. Response: {text[:200]}")
            else:
                # Try to parse as JSON anyway
                try:
                    result = response.json()
                except:
                    raise Exception(f"Unexpected content type: {content_type}. Response: {response.text[:200]}")
            
            # Extract session ID from response headers
            if "Mcp-Session-Id" in response.headers:
                self.session_id = response.headers["Mcp-Session-Id"]
            
            if "error" in result:
                raise Exception(f"MCP Error: {result['error'].get('message', 'Unknown error')}")
            
            return result.get("result", {})
        
        except requests.exceptions.RequestException as e:
            logger.error(f"MCP HTTP request failed: {e}")
            raise
    
    def initialize(self) -> bool:
        """Initialize MCP session"""
        try:
            result = self._call_mcp("initialize", {})
            logger.info(f"MCP initialized: {result.get('serverInfo', {}).get('name')}")
            return True
        except Exception as e:
            logger.error(f"MCP initialization failed: {e}")
            return False
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        try:
            result = self._call_mcp("tools/list", {})
            return result.get("tools", [])
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool"""
        try:
            result = self._call_mcp("tools/call", {
                "name": name,
                "arguments": arguments
            })
            
            # Extract content from result
            content = result.get("content", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "{}")
                try:
                    return json.loads(text_content)
                except json.JSONDecodeError:
                    return {"raw": text_content}
            return {}
        
        except Exception as e:
            logger.error(f"Failed to call tool {name}: {e}")
            raise
    
    # Convenience methods matching the old MCPClient interface
    def get_customer(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get customer by ID"""
        try:
            result = self.call_tool("get_customer", {"customer_id": customer_id})
            if isinstance(result, dict) and "id" in result:
                return result
            elif isinstance(result, dict) and "error" in result:
                return None
            return result if result else None
        except Exception as e:
            logger.error(f"Failed to get customer {customer_id}: {e}")
            return None
    
    def list_customers(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List customers by status"""
        try:
            result = self.call_tool("list_customers", {"status": status, "limit": limit})
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "result" in result:
                return result["result"] if isinstance(result["result"], list) else []
            return []
        except Exception as e:
            logger.error(f"Failed to list customers: {e}")
            return []
    
    def update_customer(self, customer_id: int, data: Dict[str, Any]) -> bool:
        """Update customer data"""
        try:
            result = self.call_tool("update_customer", {
                "customer_id": customer_id,
                "data": data
            })
            return isinstance(result, dict) and "message" in result
        except Exception as e:
            logger.error(f"Failed to update customer {customer_id}: {e}")
            return False
    
    def create_ticket(self, customer_id: int, issue: str, priority: str) -> Optional[Dict[str, Any]]:
        """Create a new ticket"""
        try:
            result = self.call_tool("create_ticket", {
                "customer_id": customer_id,
                "issue": issue,
                "priority": priority
            })
            if isinstance(result, dict) and "ticket_id" in result:
                return result
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            return None
    
    def get_customer_history(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get customer ticket history"""
        try:
            result = self.call_tool("get_customer_history", {"customer_id": customer_id})
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "result" in result:
                return result["result"] if isinstance(result["result"], list) else []
            return []
        except Exception as e:
            logger.error(f"Failed to get customer history: {e}")
            return []
    
    def get_tickets_by_priority(self, priority: str, customer_ids: List[int] = None) -> List[Dict[str, Any]]:
        """Get tickets by priority, optionally filtered by customer IDs"""
        # This requires a custom query - for now, get all customer histories and filter
        all_tickets = []
        if customer_ids:
            for customer_id in customer_ids:
                tickets = self.get_customer_history(customer_id)
                all_tickets.extend(tickets)
        else:
            # Get all active customers and their tickets
            customers = self.list_customers("active", limit=1000)
            for customer in customers:
                tickets = self.get_customer_history(customer["id"])
                all_tickets.extend(tickets)
        
        return [t for t in all_tickets if t.get("priority") == priority]
    
    def get_customers_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all customers with a specific status"""
        return self.list_customers(status, limit=1000)

