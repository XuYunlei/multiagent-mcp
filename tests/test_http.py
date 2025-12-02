"""
Test script for HTTP server endpoints
Tests the streaming and synchronous query endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n" + "=" * 80)
    print("Testing Health Endpoint")
    print("=" * 80)
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_sync_query(query: str):
    """Test synchronous query endpoint"""
    print("\n" + "=" * 80)
    print(f"Testing Sync Query: {query}")
    print("=" * 80)
    try:
        response = requests.post(
            f"{BASE_URL}/query/sync",
            json={"query": query},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"\nQuery: {result.get('query')}")
        print(f"Scenario: {result.get('result', {}).get('scenario', 'N/A')}")
        print(f"Success: {result.get('result', {}).get('success', False)}")
        
        if result.get('result', {}).get('coordination_log'):
            print("\nA2A Coordination Log:")
            for i, log_entry in enumerate(result['result']['coordination_log'], 1):
                print(f"  {i}. {log_entry}")
        
        if result.get('result', {}).get('response'):
            print(f"\nResponse:\n{result['result']['response']}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_streaming_query(query: str):
    """Test streaming query endpoint"""
    print("\n" + "=" * 80)
    print(f"Testing Streaming Query: {query}")
    print("=" * 80)
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={"query": query},
            stream=True,
            timeout=30
        )
        print(f"Status: {response.status_code}")
        print("\nStreaming Response:")
        print("-" * 80)
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        data = json.loads(data_str)
                        if data.get('type') == 'coordination':
                            print(f"\nCoordination Log: {data.get('log', [])}")
                        elif data.get('type') == 'customer_info':
                            print(f"\nCustomer Info: {json.dumps(data.get('data', {}), indent=2)}")
                        elif data.get('type') == 'response':
                            print(f"\nResponse:\n{data.get('data', '')}")
                        elif data.get('status'):
                            print(f"\nStatus: {data.get('status')} - {data.get('message', '')}")
                            if data.get('status') == 'complete':
                                print(f"Success: {data.get('success')}")
                                print(f"Scenario: {data.get('scenario', 'N/A')}")
                    except json.JSONDecodeError:
                        print(f"Raw: {data_str}")
        
        print("-" * 80)
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
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
    print("\n" + "=" * 80)
    print("  HTTP SERVER TEST SUITE")
    print("=" * 80)
    
    # Check if server is running
    if not check_server_running():
        print("\n⚠️  WARNING: Server doesn't appear to be running or wrong server detected!")
        print("   Please start the server with: python server.py")
        print("   Or use: ./start_server.sh")
        print("\n   Waiting 5 seconds for you to start the server...")
        time.sleep(5)
        
        # Check again
        if not check_server_running():
            print("\n✗ Server still not responding. Please start the server and try again.")
            return
        else:
            print("✓ Server detected!")
    else:
        print("\n✓ Server is running and responding correctly")
    
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
    print("\n" + "=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)
    
    successful = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    
    print("\nTest Results:")
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {name}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

