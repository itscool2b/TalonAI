#!/usr/bin/env python3
"""
Test script to demonstrate the difference between workflow-based and agentic AI approaches.
"""

import asyncio
import json
from .state import AgentState
from .agent_loop import run_agent_system

async def test_agentic_vs_workflow():
    """
    Compare how the system handles different types of queries
    """
    
    test_cases = [
        {
            "name": "Simple Info Query",
            "query": "What is a turbocharger?",
            "expected_behavior": "Should use info agent directly"
        },
        {
            "name": "Incomplete Car Profile",
            "query": "I want to upgrade my car for more horsepower",
            "car_profile": {"year": "2020"},  # Missing model, engine, etc.
            "expected_behavior": "Should ask user for more information"
        },
        {
            "name": "Complex Multi-Issue Query",
            "query": "My car is making a weird noise and I want to know about turbo upgrades",
            "car_profile": {"year": "2018", "model": "Civic", "engine": "1.5T"},
            "expected_behavior": "Should diagnose first, then provide mod recommendations"
        },
        {
            "name": "Diagnostic Reveals Serious Problem",
            "query": "I want to add a turbo but my engine is misfiring",
            "car_profile": {"year": "2019", "model": "WRX", "engine": "2.0T"},
            "expected_behavior": "Should focus on diagnostic first, may not recommend mods if problem is serious"
        }
    ]
    
    print("🧪 TESTING AGENTIC VS WORKFLOW APPROACHES")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        print(f"Expected: {test_case['expected_behavior']}")
        print("-" * 40)
        
        # Initialize state
        state = AgentState(
            query=test_case["query"],
            car_profile=test_case.get("car_profile", {})
        )
        
        # Run the agentic system
        result = await run_agent_system(state)
        
        print(f"Result Type: {result['type']}")
        print(f"Message: {result['message']}")
        print(f"Agent Trace: {result['agent_trace']}")
        
        if result.get('reasoning'):
            print(f"Reasoning: {result['reasoning']}")
        
        print()

async def demonstrate_agentic_adaptation():
    """
    Show how the agentic planner can adapt based on intermediate results
    """
    
    print("\n🎯 DEMONSTRATING AGENTIC ADAPTATION")
    print("=" * 60)
    
    # Test case where diagnostic reveals a serious problem
    state = AgentState(
        query="I want to add a turbo but my engine is misfiring",
        car_profile={"year": "2019", "model": "WRX", "engine": "2.0T"}
    )
    
    print("Initial Query: I want to add a turbo but my engine is misfiring")
    print("Car Profile: 2019 WRX with 2.0T engine")
    print("\nExpected Agentic Behavior:")
    print("1. Diagnostic agent identifies misfiring as serious issue")
    print("2. Agentic planner adapts - focuses on fixing the problem first")
    print("3. May not recommend turbo mods until engine is healthy")
    print("\n" + "-" * 40)
    
    result = await run_agent_system(state)
    
    print(f"Actual Result: {result['type']}")
    print(f"Message: {result['message']}")
    print(f"Agent Trace: {result['agent_trace']}")
    
    if result.get('reasoning'):
        print(f"Reasoning: {result['reasoning']}")

if __name__ == "__main__":
    asyncio.run(test_agentic_vs_workflow())
    asyncio.run(demonstrate_agentic_adaptation()) 