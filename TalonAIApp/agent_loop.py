import asyncio
from typing import Dict, Any

from .state import AgentState
from .planner import run_agentic_planner
from .response_formatter import format_agent_response

# Debug logging function
def debug_log(message, data=None):
    print(f"🔍 AGENT_LOOP: {message}")
    if data:
        print(f"📊 DATA: {data}")


async def run_agent_system(state: AgentState) -> Dict[str, Any]:
    """
    Executes the agentic planner loop that can adapt its strategy based on results.
    The agentic planner can:
    - Dynamically decide what to do next based on intermediate results
    - Ask for more information when needed
    - Stop when satisfied with the outcome
    - Adapt its approach based on what it discovers
    """
    debug_log("🚀 Starting agent system", {
        "query": state.get("query"),
        "user_id": state.get("user_id")
    })

    while True:
        debug_log("🔄 Running agentic planner")
        state = await run_agentic_planner(state)
        debug_log("✅ Planner completed", {
            "final_message": state.get("final_message"),
            "agent_trace": state.get("agent_trace")
        })
        if state.get("final_message"):
            debug_log("🏁 Breaking loop - final message received")
            break

    # Use the comprehensive response formatter
    debug_log("🎯 Formatting comprehensive response")
    formatted_response = format_agent_response(state)
    debug_log("✅ Response formatted successfully", formatted_response)
    
    return formatted_response

        
        