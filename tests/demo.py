"""
End-to-End Demonstration of Multi-Agent Customer Service System
Tests all three A2A coordination scenarios

This demo can run in two modes:
1. Direct mode (default): Agents communicate via direct method calls
2. HTTP mode: Set A2A_USE_HTTP=true to use HTTP-based A2A communication
"""

import sys
import json
import os
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.setup_database import setup_database
from src.agents import RouterAgent, CustomerDataAgent, SupportAgent

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def print_result(result):
    """Print a formatted result"""
    print("\n" + "-" * 80)
    print("RESULT:")
    print("-" * 80)
    print(f"Query: {result.get('query', 'N/A')}")
    print(f"Scenario: {result.get('scenario', 'N/A')}")
    print(f"Success: {result.get('success', False)}")
    
    if result.get('coordination_log'):
        print("\nA2A Coordination Log:")
        for i, log_entry in enumerate(result['coordination_log'], 1):
            print(f"  {i}. {log_entry}")
    
    if result.get('response'):
        print(f"\nFinal Response:")
        print(f"  {result['response']}")
    
    if result.get('customer_info'):
        print(f"\nCustomer Info Retrieved:")
        customer = result['customer_info']
        print(f"  ID: {customer.get('id')}")
        print(f"  Name: {customer.get('name')}")
        print(f"  Email: {customer.get('email')}")
        print(f"  Status: {customer.get('status')}")
    
    if result.get('statistics'):
        stats = result['statistics']
        print(f"\nStatistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    if result.get('negotiation'):
        neg = result['negotiation']
        print(f"\nNegotiation Details:")
        print(f"  Support can handle: {neg.get('support_can_handle')}")
        print(f"  Context provided: {neg.get('context_provided')}")
    
    print("\n" + "-" * 80 + "\n")

def test_scenario_1_task_allocation():
    """Test Scenario 1: Task Allocation"""
    print_section("TEST SCENARIO 1: Task Allocation")
    print("Query: 'I need help with my account, customer ID 12345'")
    
    # Initialize agents (they will create their own MCP clients)
    customer_data_agent = CustomerDataAgent()
    support_agent = SupportAgent()
    router = RouterAgent(customer_data_agent, support_agent)
    
    # Process query
    query = "I need help with my account, customer ID 12345"
    result = router.process_query(query)
    
    print_result(result)
    return result

def test_scenario_2_negotiation():
    """Test Scenario 2: Negotiation/Escalation"""
    print_section("TEST SCENARIO 2: Negotiation/Escalation")
    print("Query: 'I want to cancel my subscription but I'm having billing issues'")
    
    # Initialize agents (they will create their own MCP clients)
    customer_data_agent = CustomerDataAgent()
    support_agent = SupportAgent()
    router = RouterAgent(customer_data_agent, support_agent)
    
    # Process query
    query = "I want to cancel my subscription but I'm having billing issues"
    result = router.process_query(query)
    
    print_result(result)
    return result

def test_scenario_3_multi_step():
    """Test Scenario 3: Multi-Step Coordination"""
    print_section("TEST SCENARIO 3: Multi-Step Coordination")
    print("Query: 'What's the status of all high-priority tickets for premium customers?'")
    
    # Initialize agents (they will create their own MCP clients)
    customer_data_agent = CustomerDataAgent()
    support_agent = SupportAgent()
    router = RouterAgent(customer_data_agent, support_agent)
    
    # Process query
    query = "What's the status of all high-priority tickets for premium customers?"
    result = router.process_query(query)
    
    print_result(result)
    return result

def test_simple_query():
    """Test: Simple Query - Get customer information"""
    print_section("TEST: Simple Query")
    print("Query: 'Get customer information for ID 5'")
    
    mcp_client = MCPClient()
    customer_data_agent = CustomerDataAgent(mcp_client)
    support_agent = SupportAgent(mcp_client)
    router = RouterAgent(customer_data_agent, support_agent)
    
    query = "Get customer information for ID 5"
    result = router.process_query(query)
    
    print_result(result)
    return result

def test_coordinated_query():
    """Test: Coordinated Query"""
    print_section("TEST: Coordinated Query")
    print("Query: 'I'm customer 12345 and need help upgrading my account'")
    
    mcp_client = MCPClient()
    customer_data_agent = CustomerDataAgent(mcp_client)
    support_agent = SupportAgent(mcp_client)
    router = RouterAgent(customer_data_agent, support_agent)
    
    query = "I'm customer 12345 and need help upgrading my account"
    result = router.process_query(query)
    
    print_result(result)
    return result

def test_complex_query():
    """Test: Complex Query"""
    print_section("TEST: Complex Query")
    print("Query: 'Show me all active customers who have open tickets'")
    
    mcp_client = MCPClient()
    customer_data_agent = CustomerDataAgent(mcp_client)
    support_agent = SupportAgent(mcp_client)
    router = RouterAgent(customer_data_agent, support_agent)
    
    query = "Show me all active customers who have open tickets"
    result = router.process_query(query)
    
    print_result(result)
    return result

def test_escalation():
    """Test: Escalation"""
    print_section("TEST: Escalation")
    print("Query: 'I've been charged twice, please refund immediately!'")
    
    mcp_client = MCPClient()
    customer_data_agent = CustomerDataAgent(mcp_client)
    support_agent = SupportAgent(mcp_client)
    router = RouterAgent(customer_data_agent, support_agent)
    
    query = "I've been charged twice, please refund immediately!"
    result = router.process_query(query)
    
    print_result(result)
    return result

def test_multi_intent():
    """Test: Multi-Intent"""
    print_section("TEST: Multi-Intent")
    print("Query: 'Update my email to new@email.com and show my ticket history'")
    
    mcp_client = MCPClient()
    customer_data_agent = CustomerDataAgent(mcp_client)
    support_agent = SupportAgent(mcp_client)
    router = RouterAgent(customer_data_agent, support_agent)
    
    # For this query, we need a customer ID
    query = "I'm customer 1, update my email to new@email.com and show my ticket history"
    result = router.process_query(query)
    
    print_result(result)
    return result

def main():
    """Run all test scenarios"""
    print("\n" + "=" * 80)
    print("  MULTI-AGENT CUSTOMER SERVICE SYSTEM - END-TO-END DEMONSTRATION")
    print("=" * 80)
    
    # Setup database
    print("\nSetting up database...")
    try:
        setup_database()
        print("✓ Database setup complete!")
    except Exception as e:
        print(f"✗ Error setting up database: {e}")
        return
    
    results = []
    
    # Run all test scenarios
    try:
        # Required scenarios
        results.append(("Scenario 1: Task Allocation", test_scenario_1_task_allocation()))
        results.append(("Scenario 2: Negotiation", test_scenario_2_negotiation()))
        results.append(("Scenario 3: Multi-Step", test_scenario_3_multi_step()))
        
        # Additional test scenarios
        results.append(("Simple Query", test_simple_query()))
        results.append(("Coordinated Query", test_coordinated_query()))
        results.append(("Complex Query", test_complex_query()))
        results.append(("Escalation", test_escalation()))
        results.append(("Multi-Intent", test_multi_intent()))
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Summary
    print_section("TEST SUMMARY")
    
    successful = sum(1 for _, r in results if r.get('success', False))
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    
    print("\nTest Results:")
    for name, result in results:
        status = "✓" if result.get('success', False) else "✗"
        print(f"  {status} {name}")
    
    print("\n" + "=" * 80)
    print("  DEMONSTRATION COMPLETE")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()

