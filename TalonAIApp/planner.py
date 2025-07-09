from typing import Dict, Any
import json
from .claude import call_claude
from .state import AgentState
from .tools import tool_registry, execute_tool
from .memory import get_recent_memory, format_memory_for_prompt

async def run_agentic_planner(state: AgentState) -> AgentState:
    """
    Dynamic LLM-based planner that decides what to do and calls tools as needed
    """
    
    # Get recent memory for context
    try:
        memories = await get_recent_memory(state.get("user_id", ""), limit=3)
        memory_context = format_memory_for_prompt(memories)
    except Exception as e:
        print(f"⚠️ Memory retrieval failed: {e}")
        memory_context = "No previous conversations found."
    
    # Get available tools
    available_tools = tool_registry.list_tools()
    
    # Create dynamic prompt with current state
    prompt = f"""
You are an intelligent automotive assistant planner. You analyze user queries and decide what actions to take.

CURRENT STATE:
- User Query: "{state.get('query', '')}"
- User ID: {state.get('user_id', '')}
- Session ID: {state.get('session_id', '')}
- Car Profile: {json.dumps(state.get('car_profile', {}), indent=2)}
- Previous Actions: {json.dumps(state.get('agent_trace', []), indent=2)}

MEMORY CONTEXT:
{memory_context}

AVAILABLE TOOLS:
{json.dumps(available_tools, indent=2)}

CURRENT RESULTS:
- Mod Recommendations: {json.dumps(state.get('mod_recommendations'), indent=2) if state.get('mod_recommendations') else 'None'}
- Diagnostic Results: {json.dumps(state.get('symptom_summary'), indent=2) if state.get('symptom_summary') else 'None'}
- Build Plan: {json.dumps(state.get('build_plan'), indent=2) if state.get('build_plan') else 'None'}
- Info Answer: {json.dumps(state.get('info_answer'), indent=2) if state.get('info_answer') else 'None'}

INSTRUCTIONS:
1. Analyze the user's query and current state
2. Decide what action to take next
3. You can either:
   - Call a tool to get more information or perform an action
   - Provide a direct response if you have enough information
   - End the conversation if the user's needs are met

RESPONSE FORMAT:
Return a JSON object with ONE of these structures:

To call a tool:
{{
    "action": "use_tool",
    "tool_name": "tool_name",
    "tool_parameters": {{
        "param1": "value1",
        "param2": "value2"
    }},
    "reasoning": "Why you're calling this tool"
}}

To provide a direct response:
{{
    "action": "respond",
    "response_type": "info|modcoach|diagnostic|buildplanner",
    "response": "Your response to the user",
    "reasoning": "Why you're providing this response"
}}

To end the conversation:
{{
    "action": "end",
    "final_response": "Final response to user",
    "reasoning": "Why you're ending the conversation"
}}

DECISION LOGIC:
- If user mentions car details you don't have, use "update_car_profile" tool
- If user asks for modifications/performance, use "generate_mod_recommendations" tool
- If user reports symptoms/problems, use "diagnose_symptoms" tool
- If user wants a build plan, use "create_build_plan" tool
- If user needs car specs, use "get_car_specs" tool
- If you can answer with general knowledge, provide direct response
- If user's needs are fully met, end the conversation

Be intelligent and context-aware. Don't repeat actions unnecessarily.
"""

    try:
        response = await call_claude(prompt, temperature=0.3)
        
        # Parse LLM response
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]
        
        decision = json.loads(cleaned_response)
        
        # Execute the decision
        return await execute_planner_decision(state, decision)
        
    except Exception as e:
        print(f"❌ Error in planner: {e}")
        # Fallback to ending conversation
        state["final_message"] = "I encountered an error processing your request. Please try again."
        state["agent_trace"].append(f"Planner error: {str(e)}")
        return state

async def execute_planner_decision(state: AgentState, decision: Dict[str, Any]) -> AgentState:
    """Execute the planner's decision"""
    
    action = decision.get("action", "end")
    reasoning = decision.get("reasoning", "No reasoning provided")
    
    # Log the decision
    state["agent_trace"].append(f"Planner → {action}: {reasoning}")
    
    if action == "use_tool":
        # Execute tool
        tool_name = decision.get("tool_name")
        tool_parameters = decision.get("tool_parameters", {})
        
        print(f"🔧 Executing tool: {tool_name} with params: {tool_parameters}")
        
        tool_result = await execute_tool(tool_name, **tool_parameters)
        
        # Store tool result in state
        state["tool_trace"].append({
            "tool": tool_name,
            "parameters": tool_parameters,
            "result": tool_result,
            "reasoning": reasoning
        })
        
        # Update state based on tool result
        if tool_result.get("success") and tool_result.get("result"):
            result = tool_result["result"]
            
            if tool_name == "update_car_profile":
                # Profile updated in tool, refresh car profile
                pass
            elif tool_name == "generate_mod_recommendations":
                state["mod_recommendations"] = result.get("recommendations", [])
            elif tool_name == "diagnose_symptoms":
                state["symptom_summary"] = result.get("diagnosis", {}).get("explanation", "")
            elif tool_name == "create_build_plan":
                state["build_plan"] = result.get("build_plan", [])
            elif tool_name == "get_car_specs":
                state["car_specs"] = result
        
        # Don't end conversation, let planner decide next action
        return state
        
    elif action == "respond":
        # Provide direct response
        response_type = decision.get("response_type", "info")
        response_text = decision.get("response", "")
        
        if response_type == "info":
            state["info_answer"] = response_text
        elif response_type == "modcoach":
            state["mod_recommendations"] = [{"name": "Custom Response", "justification": response_text}]
        elif response_type == "diagnostic":
            state["symptom_summary"] = response_text
        elif response_type == "buildplanner":
            state["build_plan"] = [{"stage": "Custom", "description": response_text}]
        
        # Don't end conversation, let planner decide next action
        return state
        
    elif action == "end":
        # End conversation
        final_response = decision.get("final_response", "Thank you for using TalonAI!")
        state["final_message"] = final_response
        state["agent_trace"].append(f"Planner → end: {reasoning}")
        return state
    
    else:
        # Unknown action, end conversation
        state["final_message"] = "I'm not sure how to help with that. Please try rephrasing your question."
        state["agent_trace"].append(f"Planner → unknown action: {action}")
        return state