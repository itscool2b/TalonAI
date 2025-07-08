import asyncio
from typing import Dict, Any

from state import AgentState
from planner import run_agentic_planner

# agent_loop.py

import asyncio
from typing import Dict, Any

from state import AgentState
from planner import run_agentic_planner


async def run_agent_system(state: AgentState) -> Dict[str, Any]:
    """
    Executes the agentic planner loop that can adapt its strategy based on results.
    The agentic planner can:
    - Dynamically decide what to do next based on intermediate results
    - Ask for more information when needed
    - Stop when satisfied with the outcome
    - Adapt its approach based on what it discovers
    """

    while True:
        state = await run_agentic_planner(state)
        if state.get("final_message"):
            break

    # Determine final output based on what the agentic planner accomplished
    # The agentic planner may have run multiple agents or adapted its strategy
    


    # Check if session ended normally
    if "end" in str(state.get("agent_trace", [])):
        # Determine what was accomplished based on the trace
        trace = state.get("agent_trace", [])
        
        # Priority order: buildplanner > modcoach > diagnostic > info
        if any("buildplanner" in a for a in trace):
            return {
                "type": "buildplanner",
                "build_plan": state.get("build_plan", []),
                "message": "Here's your personalized build plan for your car!",
                "agent_trace": trace,
                "reasoning": "Agentic planner determined a build plan was needed"
            }

        if any("modcoach" in a for a in trace):
            return {
                "type": "modcoach",
                "mod_recommendations": state.get("mod_recommendations", []),
                "message": "Here are my recommendations for your next mods!",
                "agent_trace": trace,
                "reasoning": "Agentic planner determined mod recommendations were needed"
            }

        if any("diagnostic" in a for a in trace):
            return {
                "type": "diagnostic",
                "symptom_summary": state.get("symptom_summary", ""),
                "followup_recommendations": state.get("followup_recommendations", []),
                "message": "Here's my diagnosis of your car's issue:",
                "agent_trace": trace,
                "reasoning": "Agentic planner determined diagnostic analysis was needed"
            }

        if any("info" in a for a in trace):
            return {
                "type": "info",
                "response": state.get("info_answer", "No answer available."),
                "message": "Here's what I found for you:",
                "agent_trace": trace,
                "reasoning": "Agentic planner determined informational response was needed"
            }

        # If no specific agents ran but session ended, it might be a simple query
        return {
            "type": "simple_response",
            "message": state.get("final_message", "Session complete."),
            "agent_trace": trace,
            "reasoning": "Agentic planner determined no specific agents were needed"
        }

    # If we reach here, something unexpected happened
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

        
        