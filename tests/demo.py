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
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Suppress verbose logging for cleaner output
logging.getLogger().setLevel(logging.ERROR)
logging.getLogger('src').setLevel(logging.ERROR)
logging.getLogger('src.agents').setLevel(logging.ERROR)
logging.getLogger('src.mcp_http_client').setLevel(logging.ERROR)

from scripts.setup_database import setup_database
from src.agents import RouterAgent, CustomerDataAgent, SupportAgent, MCPClient

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "═" * 80)
    print(f"  {title}")
    print("═" * 80)

def print_result(result):
    """Print a formatted result"""
    print("\n" + "─" * 80)
    print("RESULT")
    print("─" * 80)
    
    # Query
    query = result.get('query', 'N/A')
    print(f"\n📝 Query: {query}")
    
    # Scenario
    scenario = result.get('scenario', 'N/A')
    print(f"🎯 Scenario: {scenario}")
    
    # Success status
    success = result.get('success', False)
    status_icon = "✅" if success else "❌"
    print(f"{status_icon} Success: {success}")
    
    # A2A Coordination Log
    if result.get('coordination_log'):
        print(f"\n🔄 A2A Coordination Steps ({len(result['coordination_log'])} steps):")
        for i, log_entry in enumerate(result['coordination_log'], 1):
            print(f"   {i}. {log_entry}")
    
    # Final Response
    if result.get('response'):
        print(f"\n💬 Final Response:")
        response = result['response']
        # Format multi-line responses nicely
        if '\n' in response:
            for line in response.split('\n'):
                print(f"   {line}")
        else:
            print(f"   {response}")
    
    # Customer Info
    if result.get('customer_info'):
        customer = result['customer_info']
        print(f"\n👤 Customer Information:")
        print(f"   • ID: {customer.get('id')}")
        print(f"   • Name: {customer.get('name')}")
        print(f"   • Email: {customer.get('email')}")
        print(f"   • Status: {customer.get('status')}")
    
    # Statistics
    if result.get('statistics'):
        stats = result['statistics']
        print(f"\n📊 Statistics:")
        for key, value in stats.items():
            print(f"   • {key.replace('_', ' ').title()}: {value}")
    
    # Negotiation Details
    if result.get('negotiation'):
        neg = result['negotiation']
        print(f"\n🤝 Negotiation Details:")
        print(f"   • Support can handle: {neg.get('support_can_handle')}")
        print(f"   • Context provided: {neg.get('context_provided')}")
    
    print("\n" + "─" * 80 + "\n")

def test_scenario_1_task_allocation():
    """Test Scenario 1: Task Allocation"""
    print_section("SCENARIO 1: Task Allocation")
    print("Query: 'I need help with my account, customer ID 12345'\n")
    
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
    print_section("SCENARIO 2: Negotiation/Escalation")
    print("Query: 'I want to cancel my subscription but I'm having billing issues'\n")
    
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
    print_section("SCENARIO 3: Multi-Step Coordination")
    print("Query: 'What's the status of all high-priority tickets for premium customers?'\n")
    
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
    print_section("ADDITIONAL TEST: Simple Query")
    print("Query: 'Get customer information for ID 5'\n")
    
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
    print_section("ADDITIONAL TEST: Coordinated Query")
    print("Query: 'I'm customer 12345 and need help upgrading my account'\n")
    
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
    print_section("ADDITIONAL TEST: Complex Query")
    print("Query: 'Show me all active customers who have open tickets'\n")
    
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
    print_section("ADDITIONAL TEST: Escalation")
    print("Query: 'I've been charged twice, please refund immediately!'\n")
    
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
    print_section("ADDITIONAL TEST: Multi-Intent")
    print("Query: 'Update my email to new@email.com and show my ticket history'\n")
    
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
    print("\n" + "═" * 80)
    print("  MULTI-AGENT CUSTOMER SERVICE SYSTEM - END-TO-END DEMONSTRATION")
    print("═" * 80)
    
    # Setup database
    print("\n🔧 Setting up database...")
    try:
        setup_database()
        print("✅ Database setup complete!\n")
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
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
    
    print(f"\n📈 Test Statistics:")
    print(f"   • Total Tests: {total}")
    print(f"   • Successful: {successful} ✅")
    print(f"   • Failed: {total - successful}")
    
    print(f"\n📋 Test Results:")
    for name, result in results:
        status = "✅" if result.get('success', False) else "❌"
        print(f"   {status} {name}")
    
    print("\n" + "═" * 80)
    print("  🎉 DEMONSTRATION COMPLETE")
    print("═" * 80 + "\n")

if __name__ == "__main__":
    main()

