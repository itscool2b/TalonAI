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
    try:
        debug_log("🚀 Starting agent system", {
            "query": state.get("query"),
            "user_id": state.get("user_id")
        })

        # Ensure state has required fields
        if not state.get("agent_trace"):
            state["agent_trace"] = []
        if not state.get("tool_trace"):
            state["tool_trace"] = []
        if not state.get("flags"):
            state["flags"] = {}

        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            debug_log(f"🔄 Running agentic planner (iteration {iteration})")
            
            try:
                state = await run_agentic_planner(state)
                debug_log("✅ Planner completed", {
                    "final_message": state.get("final_message"),
                    "agent_trace": state.get("agent_trace")
                })
                
                if state.get("final_message"):
                    debug_log("🏁 Breaking loop - final message received")
                    break
                    
            except Exception as e:
                debug_log(f"❌ Error in planner iteration {iteration}", str(e))
                state["final_message"] = "I encountered an error while processing your request."
                state["agent_trace"].append(f"Error in iteration {iteration}: {str(e)}")
                break

        if iteration >= max_iterations:
            debug_log("⚠️ Reached maximum iterations")
            state["final_message"] = "I've reached the maximum processing iterations. Please try rephrasing your question."
            state["agent_trace"].append("Reached maximum iterations limit")

        # Use the comprehensive response formatter
        debug_log("🎯 Formatting comprehensive response")
        formatted_response = format_agent_response(state)
        debug_log("✅ Response formatted successfully")
        
        return formatted_response
        
    except Exception as e:
        debug_log("❌ Critical error in agent system", str(e))
        # Return safe fallback response
        return {
            "type": "error",
            "query": state.get("query", ""),
            "user_id": state.get("user_id", ""),
            "session_id": state.get("session_id", ""),
            "timestamp": "2025-07-09T20:00:00.000000",
            "response": "I encountered a critical error while processing your request. Please try again.",
            "message": "I encountered a critical error while processing your request. Please try again.",
            "response_type": "error",
            "error": str(e),
            "agent_trace": state.get("agent_trace", []) + [f"Critical error: {str(e)}"],
            "tool_trace": state.get("tool_trace", [])
        }

        
        