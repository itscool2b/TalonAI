from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from .claude import call_claude

async def format_agent_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dynamic LLM-based response formatter that organizes all state data properly
    """
    
    # Create dynamic prompt to format the response
    prompt = f"""
You are a response formatting specialist. Format the agent system output into a well-structured JSON response.

AGENT STATE:
{json.dumps(state, indent=2)}

INSTRUCTIONS:
1. Analyze the agent trace to determine what happened
2. Extract the most relevant information for the user
3. Format it into a clean, structured response

RESPONSE FORMAT:
Return a JSON object with this structure:
{{
    "type": "info|modcoach|diagnostic|buildplanner",
    "query": "original user query",
    "user_id": "user_id",
    "session_id": "session_id", 
    "timestamp": "current_timestamp",
    "agent_trace": ["list of agent actions"],
    "tool_trace": ["list of tool calls"],
    "response": "main response text for user",
    "message": "user-friendly message",
    "response_type": "descriptive_type",
    "data": {{
        // Relevant data based on response type
        // For modcoach: mod_recommendations, total_recommendations
        // For diagnostic: symptom_summary, diagnosis_confidence
        // For buildplanner: build_plan, total_stages
        // For info: answer, knowledge_base
    }},
    "car_profile": {{
        // Car profile data
    }},
    "debug_flags": {{
        // Any debug information
    }}
}}

FORMATTING RULES:
1. Determine response type based on what agents ran and what data is available
2. Create a helpful, conversational response text
3. Include all relevant data in the data section
4. Add debug flags if useful information is available
5. Make the message user-friendly and actionable

Be intelligent about determining the response type and formatting the data appropriately.
"""

    try:
        response = await call_claude(prompt, temperature=0.1)
        
        # Parse LLM response
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]
        
        formatted_response = json.loads(cleaned_response)
        
        # Add timestamp if not present
        if "timestamp" not in formatted_response:
            formatted_response["timestamp"] = datetime.utcnow().isoformat()
        
        return formatted_response
        
    except Exception as e:
        print(f"❌ Error in response formatter: {e}")
        # Fallback to basic response
        return {
            "type": "error",
            "query": state.get("query", ""),
            "user_id": state.get("user_id", ""),
            "session_id": state.get("session_id", ""),
            "timestamp": datetime.utcnow().isoformat(),
            "response": "I encountered an error formatting the response. Please try again.",
            "message": "I encountered an error formatting the response. Please try again.",
            "response_type": "error",
            "error": str(e),
            "agent_trace": state.get("agent_trace", []),
            "tool_trace": state.get("tool_trace", []),
            "data": {},
            "car_profile": state.get("car_profile", {})
        } 