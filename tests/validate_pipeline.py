#!/usr/bin/env python3
"""
Pipeline Validation Script
Tests MCP server, A2A agent cards, and end-to-end functionality
"""

import requests
import json
import sys
import time
from typing import Dict, Any, List

# Configuration
MCP_SERVER_URL = "http://localhost:8003"
MAIN_SERVER_URL = "http://localhost:8000"
CUSTOMER_DATA_URL = "http://localhost:8001"
SUPPORT_URL = "http://localhost:8002"

def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_section(text: str):
    """Print a formatted section"""
    print(f"\n--- {text} ---")

def check_service(url: str, name: str) -> bool:
    """Check if a service is running"""
    try:
        response = requests.get(f"{url}/health", timeout=2)
        if response.status_code == 200:
            print(f"✅ {name} is running at {url}")
            return True
        else:
            print(f"❌ {name} returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name} is not running at {url}")
        return False
    except Exception as e:
        print(f"❌ Error checking {name}: {e}")
        return False

def test_mcp_tools_list() -> bool:
    """Test MCP tools/list endpoint"""
    print_section("Testing MCP tools/list")
    try:
        response = requests.get(f"{MCP_SERVER_URL}/tools/list", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        tools = data.get("tools", [])
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.get('name')}: {tool.get('description', '')[:60]}...")
        
        # Validate required tools
        required_tools = ["get_customer", "list_customers", "update_customer", 
                         "create_ticket", "get_customer_history"]
        found_tools = [t.get("name") for t in tools]
        missing = [t for t in required_tools if t not in found_tools]
        
        if missing:
            print(f"❌ Missing required tools: {missing}")
            return False
        else:
            print("✅ All required tools present")
            return True
    except Exception as e:
        print(f"❌ Error testing tools/list: {e}")
        return False

def test_mcp_tools_call() -> bool:
    """Test MCP tools/call endpoint"""
    print_section("Testing MCP tools/call")
    try:
        # Test get_customer
        payload = {
            "name": "get_customer",
            "arguments": {"customer_id": 1}
        }
        response = requests.post(f"{MCP_SERVER_URL}/tools/call", json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            result = data.get("result", {})
            if "id" in result:
                print(f"✅ get_customer works: Retrieved customer {result.get('id')} - {result.get('name')}")
                return True
            else:
                print(f"❌ get_customer returned unexpected result: {data}")
                return False
        else:
            print(f"❌ get_customer failed: {data.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Error testing tools/call: {e}")
        return False

def test_mcp_protocol() -> bool:
    """Test MCP protocol endpoint (/mcp)"""
    print_section("Testing MCP Protocol Endpoint")
    try:
        # Test initialize
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        response = requests.post(f"{MCP_SERVER_URL}/mcp", json=payload, timeout=5)
        response.raise_for_status()
        
        # POST /mcp now returns JSON directly (not SSE)
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type or 'text/json' in content_type:
            data = response.json()
        else:
            # Fallback: try parsing as JSON anyway
            try:
                data = response.json()
            except:
                print(f"❌ Unexpected content type: {content_type}")
                return False
        
        if "result" in data:
            print("✅ MCP initialize works")
            session_id = response.headers.get("Mcp-Session-Id")
            if session_id:
                print(f"   Session ID: {session_id[:20]}...")
        else:
            print(f"❌ MCP initialize failed: {data}")
            return False
        
        # Test tools/list via protocol
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        response = requests.post(f"{MCP_SERVER_URL}/mcp", json=payload, timeout=5)
        response.raise_for_status()
        
        # POST /mcp returns JSON directly
        data = response.json()
        
        if "result" in data and "tools" in data["result"]:
            print(f"✅ MCP tools/list works: {len(data['result']['tools'])} tools")
        else:
            print(f"❌ MCP tools/list failed: {data}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error testing MCP protocol: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_cards() -> bool:
    """Test A2A agent cards"""
    print_section("Testing A2A Agent Cards")
    try:
        response = requests.get(f"{MAIN_SERVER_URL}/agents", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        agents = data.get("agents", [])
        print(f"✅ Found {len(agents)} agents:")
        
        required_agents = ["router_agent", "customer_data_agent", "support_agent"]
        found_agent_ids = [a.get("agent_id") for a in agents]
        
        for agent in agents:
            agent_id = agent.get("agent_id")
            name = agent.get("name")
            capabilities = agent.get("capabilities", [])
            tasks = agent.get("tasks", [])
            print(f"   - {name} ({agent_id})")
            print(f"     Capabilities: {', '.join(capabilities)}")
            print(f"     Tasks: {len(tasks)} tasks defined")
        
        missing = [a for a in required_agents if a not in found_agent_ids]
        if missing:
            print(f"❌ Missing required agents: {missing}")
            return False
        else:
            print("✅ All required agents present with agent cards")
            return True
    except Exception as e:
        print(f"❌ Error testing agent cards: {e}")
        return False

def test_end_to_end_query() -> bool:
    """Test end-to-end query processing"""
    print_section("Testing End-to-End Query")
    try:
        # Test a simple query
        payload = {"query": "Get customer information for ID 1"}
        response = requests.post(f"{MAIN_SERVER_URL}/query/sync", json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        result = data.get("result", {})
        if result.get("success"):
            print("✅ End-to-end query successful")
            print(f"   Scenario: {result.get('scenario', 'N/A')}")
            print(f"   Response: {result.get('response', '')[:100]}...")
            if result.get("coordination_log"):
                print(f"   Coordination steps: {len(result['coordination_log'])}")
            return True
        else:
            print(f"❌ End-to-end query failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error testing end-to-end query: {e}")
        return False

def main():
    """Run all validation tests"""
    print_header("Pipeline Validation")
    print("\nThis script validates:")
    print("  1. MCP Server is running and accessible")
    print("  2. MCP tools/list endpoint works")
    print("  3. MCP tools/call endpoint works")
    print("  4. MCP protocol endpoint (/mcp) works")
    print("  5. A2A agent cards are accessible")
    print("  6. End-to-end query processing works")
    
    results = []
    
    # Check services
    print_header("Service Health Checks")
    results.append(("MCP Server", check_service(MCP_SERVER_URL, "MCP Server")))
    results.append(("Main Server", check_service(MAIN_SERVER_URL, "Main Server")))
    
    if not all([r[1] for r in results]):
        print("\n❌ Some services are not running. Please start them first:")
        print("   - MCP Server: python -m src.mcp_http_server")
        print("   - Main Server: python -m src.server")
        return 1
    
    # Test MCP
    print_header("MCP Server Tests")
    results.append(("MCP tools/list", test_mcp_tools_list()))
    results.append(("MCP tools/call", test_mcp_tools_call()))
    results.append(("MCP Protocol", test_mcp_protocol()))
    
    # Test A2A
    print_header("A2A Agent Cards Tests")
    results.append(("Agent Cards", test_agent_cards()))
    
    # Test End-to-End
    print_header("End-to-End Tests")
    results.append(("End-to-End Query", test_end_to_end_query()))
    
    # Summary
    print_header("Validation Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTests Passed: {passed}/{total}")
    print("\nDetailed Results:")
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    if passed == total:
        print("\n🎉 All tests passed! Pipeline is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

