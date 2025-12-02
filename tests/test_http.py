"""
Test script for HTTP server endpoints
Tests the streaming and synchronous query endpoints
"""

import requests
import json
import time
import logging

# Suppress verbose logging for cleaner output
logging.getLogger().setLevel(logging.ERROR)
logging.getLogger('src').setLevel(logging.ERROR)
logging.getLogger('src.agents').setLevel(logging.ERROR)
logging.getLogger('src.mcp_http_client').setLevel(logging.ERROR)

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n" + "─" * 80)
    print("🔍 Testing Health Endpoint")
    print("─" * 80)
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"   Service: {data.get('service', 'N/A')}")
            print(f"   A2A Framework: {data.get('a2a_framework', 'N/A')}")
            print(f"   MCP Transport: {data.get('mcp_transport', 'N/A')}")
            return True
        else:
            print(f"❌ Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_sync_query(query: str):
    """Test synchronous query endpoint"""
    print("\n" + "─" * 80)
    print(f"🔍 Testing Sync Query")
    print("─" * 80)
    print(f"📝 Query: {query[:70]}{'...' if len(query) > 70 else ''}")
    try:
        response = requests.post(
            f"{BASE_URL}/query/sync",
            json={"query": query},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json().get('result', {})
            scenario = result.get('scenario', 'N/A')
            success = result.get('success', False)
            
            print(f"✅ Status: {response.status_code}")
            print(f"🎯 Scenario: {scenario}")
            print(f"{'✅' if success else '❌'} Success: {success}")
            
            if result.get('coordination_log'):
                print(f"\n🔄 A2A Coordination Steps ({len(result['coordination_log'])} steps):")
                for i, log_entry in enumerate(result['coordination_log'], 1):
                    print(f"   {i}. {log_entry}")
            
            if result.get('response'):
                response_text = result['response']
                print(f"\n💬 Response:")
                if '\n' in response_text:
                    for line in response_text.split('\n'):
                        print(f"   {line}")
                else:
                    print(f"   {response_text}")
            
            return True
        else:
            print(f"❌ Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_streaming_query(query: str):
    """Test streaming query endpoint"""
    print("\n" + "─" * 80)
    print(f"🔍 Testing Streaming Query")
    print("─" * 80)
    print(f"📝 Query: {query[:70]}{'...' if len(query) > 70 else ''}")
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={"query": query},
            stream=True,
            timeout=30
        )
        if response.status_code == 200:
            print(f"✅ Status: {response.status_code}")
            print(f"\n📡 Streaming Response:")
            print("─" * 80)
            
            final_status = None
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            if data.get('type') == 'coordination':
                                log = data.get('log', [])
                                if log:
                                    print(f"🔄 Coordination: {log[-1] if isinstance(log, list) else log}")
                            elif data.get('type') == 'customer_info':
                                customer = data.get('data', {})
                                if customer:
                                    print(f"👤 Customer: {customer.get('name', 'N/A')} (ID: {customer.get('id', 'N/A')})")
                            elif data.get('type') == 'response':
                                response_text = data.get('data', '')
                                if response_text:
                                    print(f"💬 Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
                            elif data.get('status'):
                                status = data.get('status')
                                if status == 'complete':
                                    final_status = data
                                    print(f"✅ {status.capitalize()}: Success={data.get('success')}, Scenario={data.get('scenario', 'N/A')}")
                                elif status == 'processing':
                                    print(f"⏳ Processing: {data.get('message', '')}")
                        except json.JSONDecodeError:
                            pass
            
            print("─" * 80)
            return True
        else:
            print(f"❌ Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_server_running():
    """Check if the correct server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if "Multi-Agent Customer Service System" in str(data.get("service", "")):
                return True
        return False
    except:
        return False

def main():
    """Run all tests"""
    print("\n" + "═" * 80)
    print("  HTTP SERVER TEST SUITE")
    print("═" * 80)
    
    # Check if server is running
    if not check_server_running():
        print("\n⚠️  WARNING: Server doesn't appear to be running or wrong server detected!")
        print("   Please start the server with: python -m src.server")
        print("   Or use: ./scripts/start_server.sh")
        print("\n   Waiting 5 seconds for you to start the server...")
        time.sleep(5)
        
        # Check again
        if not check_server_running():
            print("\n❌ Server still not responding. Please start the server and try again.")
            return
        else:
            print("✅ Server detected!")
    else:
        print("\n✅ Server is running and responding correctly")
    
    results = []
    
    # Test health
    results.append(("Health Check", test_health()))
    
    # Test scenarios
    test_queries = [
        "Get customer information for ID 5",
        "I need help with my account, customer ID 12345",
        "I want to cancel my subscription but I'm having billing issues",
        "What's the status of all high-priority tickets for premium customers?",
    ]
    
    for query in test_queries:
        results.append((f"Sync: {query[:50]}...", test_sync_query(query)))
        time.sleep(1)  # Small delay between requests
    
    # Test streaming
    results.append(("Streaming: Simple query", test_streaming_query("Get customer information for ID 5")))
    
    # Summary
    print("\n" + "═" * 80)
    print("  TEST SUMMARY")
    print("═" * 80)
    
    successful = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n📈 Test Statistics:")
    print(f"   • Total Tests: {total}")
    print(f"   • Successful: {successful} ✅")
    print(f"   • Failed: {total - successful}")
    
    print(f"\n📋 Test Results:")
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"   {status} {name}")
    
    print("\n" + "═" * 80 + "\n")

if __name__ == "__main__":
    main()

