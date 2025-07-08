#!/usr/bin/env python3
"""
Simple demonstration of workflow vs agentic AI approaches
"""

def demonstrate_workflow_approach():
    """
    Shows how a workflow-based system would handle queries
    """
    print("🔄 WORKFLOW-BASED APPROACH")
    print("=" * 50)
    
    scenarios = [
        {
            "query": "I want to add a turbo but my engine is misfiring",
            "workflow_logic": "1. Check if query mentions mods → YES\n2. Check if query mentions problems → YES\n3. Run diagnostic first, then modcoach\n4. Always follow this order regardless of diagnostic results"
        },
        {
            "query": "What is a turbocharger?",
            "workflow_logic": "1. Check if query is informational → YES\n2. Run info agent\n3. End session"
        },
        {
            "query": "I want to upgrade my car", 
            "car_profile": {"year": "2020"},
            "workflow_logic": "1. Check if query mentions mods → YES\n2. Run modcoach agent\n3. Ignore incomplete car profile\n4. End session"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['query']}")
        print(f"Workflow Logic:\n{scenario['workflow_logic']}")
        print(f"Result: Fixed, predictable behavior")
        print()

def demonstrate_agentic_approach():
    """
    Shows how an agentic system would handle the same queries
    """
    print("\n🧠 AGENTIC APPROACH")
    print("=" * 50)
    
    scenarios = [
        {
            "query": "I want to add a turbo but my engine is misfiring",
            "agentic_logic": "1. Evaluate: User wants mods BUT reports serious problem\n2. Decision: Misfiring is critical - must diagnose first\n3. Run diagnostic\n4. Adapt: If diagnostic reveals serious engine damage → focus on repairs, not mods\n5. May ask: 'Have you fixed the misfiring issue first?'"
        },
        {
            "query": "What is a turbocharger?",
            "agentic_logic": "1. Evaluate: Simple informational query\n2. Decision: Direct info response needed\n3. Run info agent\n4. End: Query satisfied"
        },
        {
            "query": "I want to upgrade my car",
            "car_profile": {"year": "2020"},
            "agentic_logic": "1. Evaluate: User wants mods but profile incomplete\n2. Decision: Need more info for accurate recommendations\n3. Action: Ask user for missing details\n4. Question: 'What model and engine does your 2020 car have?'"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['query']}")
        print(f"Agentic Logic:\n{scenario['agentic_logic']}")
        print(f"Result: Adaptive, context-aware behavior")
        print()

def show_key_differences():
    """
    Highlights the key differences between the approaches
    """
    print("\n🔍 KEY DIFFERENCES")
    print("=" * 50)
    
    differences = [
        {
            "aspect": "Decision Making",
            "workflow": "Fixed rules and patterns",
            "agentic": "Dynamic evaluation of context"
        },
        {
            "aspect": "Adaptation",
            "workflow": "Follows predetermined sequence",
            "agentic": "Adapts strategy based on results"
        },
        {
            "aspect": "Information Gathering",
            "workflow": "Uses what's available",
            "agentic": "Can request additional information"
        },
        {
            "aspect": "Problem Solving",
            "workflow": "Linear, step-by-step",
            "agentic": "Iterative, can backtrack and reconsider"
        },
        {
            "aspect": "User Interaction",
            "workflow": "Assumes complete information",
            "agentic": "Can ask clarifying questions"
        }
    ]
    
    for diff in differences:
        print(f"\n{diff['aspect']}:")
        print(f"  Workflow: {diff['workflow']}")
        print(f"  Agentic:  {diff['agentic']}")

def main():
    demonstrate_workflow_approach()
    demonstrate_agentic_approach()
    show_key_differences()
    
    print("\n" + "=" * 50)
    print("💡 CONCLUSION")
    print("=" * 50)
    print("""
The key difference is that agentic AI can:
• Think about what it doesn't know
• Adapt its strategy based on what it discovers
• Ask for more information when needed
• Change its approach if initial attempts don't work
• Make context-aware decisions rather than following fixed rules

This makes it more like a real intelligent agent rather than just a workflow engine.
    """)

if __name__ == "__main__":
    main() 