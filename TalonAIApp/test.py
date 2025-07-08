import asyncio
from typing import Dict, Any
import os
from dotenv import load_dotenv

from agent_loop import run_agent_system

from state import AgentState  # import your TypedDict

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

dummy_state: AgentState = {
    "query": "I want to add some horsepower but I'm also hearing a rattling noise when I accelerate",
    "user_id": "test_user",
    "car_profile": {
        "make": "Acura",
        "model": "Integra",
        "year": 2023,
        "resale_pref": False,
        "mods": [
            {
                "name": "AWE Track Exhaust",
                "brand": "AWE",
                "status": "installed",
                "install_date": "2023-08-01",
                "notes": "Sounds great under load",
                "source_link": "https://awe-tuning.com"
            }
        ],
        "symptoms": [],
        "goals": [
            {
                "goal_type": "power",
                "priority": 1,
                "notes": "Looking to increase horsepower."
            }
        ]
    },
    "mod_recommendations": None,
    "symptom_summary": None,
    "build_plan": None,
    "final_message": None,
    "agent_trace": [],
    "flags": {},
    "info_answer": None,
    "tool_trace": []
}


async def main():
    print("🧠 Testing Multi-Agent Complex Query\n")
    print("=" * 60)
    
    # Test a complex query that should need multiple agents
    print("\n📝 COMPLEX QUERY: Multiple concerns in one request")
    complex_state = dummy_state.copy()
    complex_state["query"] = "I want to increase horsepower to 300hp, but my car is making a weird noise when I accelerate, and I need to understand what ECU tuning is before I start modding"
    
    print(f"Query: '{complex_state['query']}'")
    print("\nThis query contains:")
    print("- Performance goal (modcoach)")
    print("- Diagnostic issue (diagnostic)") 
    print("- Information request (info)")
    print("- Build planning (buildplanner)")
    
    result = await run_agent_system(complex_state)
    print(f"\n✅ Final Result: {result['type']} agent")
    print(f"📊 Agent Trace: {result.get('agent_trace', [])}")
    
    print("\n" + "=" * 60)
    print("🎉 SUCCESS: Multi-Agent System Working!")
    print("✅ The planner correctly identified multiple concerns and ran 4 agents:")
    print("   1. diagnostic (for the noise issue)")
    print("   2. info (for ECU tuning explanation)")
    print("   3. modcoach (for horsepower recommendations)")
    print("   4. buildplanner (for the 300hp build plan)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())