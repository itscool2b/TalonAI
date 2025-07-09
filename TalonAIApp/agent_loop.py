import asyncio
from typing import Dict, Any

from .state import AgentState
from .planner import run_agentic_planner

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

    # Determine final output based on what the agentic planner accomplished
    # The agentic planner may have run multiple agents or adapted its strategy
    


    # Check if session ended normally
    if "end" in str(state.get("agent_trace", [])):
        # Determine what was accomplished based on the trace
        trace = state.get("agent_trace", [])
        debug_log("🎯 Session ended normally", trace)
        
        # Priority order: buildplanner > modcoach > diagnostic > info
        if any("buildplanner" in a for a in trace):
            debug_log("📋 Returning buildplanner response")
            build_plan = state.get("build_plan", [])
            if build_plan and len(build_plan) > 0:
                message = "Here's your personalized build plan for your car!"
            else:
                message = "I'd be happy to help you create a build plan! Tell me about your car and what you want to achieve."
            return {
                "type": "buildplanner",
                "build_plan": build_plan,
                "message": message,
                "agent_trace": trace
            }

        if any("modcoach" in a for a in trace):
            debug_log("🚗 Returning modcoach response")
            mod_recommendations = state.get("mod_recommendations", [])
            if mod_recommendations and len(mod_recommendations) > 0:
                message = "Here are my recommendations for your next mods!"
            else:
                message = "I'd love to help you choose your next modifications! What kind of performance are you looking for?"
            return {
                "type": "modcoach",
                "mod_recommendations": mod_recommendations,
                "message": message,
                "agent_trace": trace
            }

        if any("diagnostic" in a for a in trace):
            debug_log("🔧 Returning diagnostic response")
            symptom_summary = state.get("symptom_summary", "")
            if symptom_summary and symptom_summary.strip():
                message = "Here's my diagnosis of your car's issue:"
            else:
                message = "I'd be happy to help diagnose any car issues. Could you describe what symptoms you're experiencing?"
            return {
                "type": "diagnostic",
                "symptom_summary": symptom_summary,
                "followup_recommendations": state.get("followup_recommendations", []),
                "message": message,
                "agent_trace": trace
            }

        if any("info" in a for a in trace):
            debug_log("📚 Returning info response")
            info_answer = state.get("info_answer", "")
            # Info agent should provide complete responses directly
            return {
                "type": "info",
                "response": info_answer,
                "message": info_answer,  # Use the info answer as the message
                "agent_trace": trace
            }

        # If no specific agents ran but session ended, it might be a simple query
        debug_log("💬 Returning simple response")
        return {
            "type": "simple_response",
            "message": state.get("final_message", "Session complete."),
            "agent_trace": trace
        }

    # If we reach here, something unexpected happened
    debug_log("❌ Unexpected situation - returning unknown response", {
        "final_message": state.get("final_message"),
        "agent_trace": state.get("agent_trace", [])
    })
    return {
        "type": "unknown",
        "message": "The agentic planner encountered an unexpected situation.",
        "agent_trace": state.get("agent_trace", []),
        "debug_info": {
            "final_message": state.get("final_message"),
            "flags": state.get("flags", {}),
            "tool_trace": state.get("tool_trace", [])
        }
    }

        
        