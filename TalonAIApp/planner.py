from typing import Dict, Any
import json
from .claude import call_claude
from .state import AgentState
from .memory import get_recent_memory, format_memory_for_prompt
from .info import info_pipeline
from .mod_coach import mod_coach_pipeline
from .diagnostic import diagnostic_pipeline
from .build_planner import buildplanner_pipeline
from .profile_updater import profile_updater_pipeline

async def run_agentic_planner(state: AgentState) -> AgentState:
    """
    Fully dynamic LLM-based planner that intelligently decides what agents to run
    """
    max_iterations = 5  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Get recent memory for context
        try:
            memories = await get_recent_memory(state.get("user_id", ""), limit=3)
            memory_context = format_memory_for_prompt(memories)
        except Exception as e:
            print(f"⚠️ Memory retrieval failed: {e}")
            memory_context = "No previous conversations found."
        
        prompt = f"""
You are an intelligent automotive assistant planner. You analyze user queries and current state to decide what actions to take.

CURRENT STATE:
- User Query: "{state.get('query', '')}"
- Car Profile: {json.dumps(state.get('car_profile', {}), indent=2)}
- Previous Actions: {json.dumps(state.get('agent_trace', []), indent=2)}
- Current Results:
  * Info Answer: {state.get('info_answer', 'None')}
  * Profile Updated: {state.get('profile_updated', False)}
  * Mod Recommendations: {len(state.get('mod_recommendations') or [])} recommendations
  * Diagnostic Results: {'Available' if state.get('symptom_summary') else 'None'}
  * Build Plan: {len(state.get('build_plan') or [])} stages

MEMORY CONTEXT:
{memory_context}

AVAILABLE AGENTS:
• `profile_updater` — Extract and update car profile information from user queries
• `info` — Answer general automotive questions with expert knowledge
• `modcoach` — Generate performance modification recommendations
• `diagnostic` — Diagnose car problems based on symptoms
• `buildplanner` — Create comprehensive staged build plans
• `end` — Complete the session when user's needs are met

DECISION LOGIC:
1. **Profile Updates**: If user mentions car details (make/model/year/name), run profile_updater
2. **General Questions**: Use info agent for automotive knowledge, greetings, explanations
3. **Performance Mods**: Use modcoach when user asks about modifications, upgrades, performance
4. **Problems/Issues**: Use diagnostic when user reports symptoms, noises, problems
5. **Build Planning**: Use buildplanner for multi-stage modification plans
6. **End Session**: When user's query has been fully addressed

EFFICIENCY RULES:
- Don't repeat the same agent unless new information is needed
- Simple greetings → info agent, then END
- If user's needs are met → END immediately
- Profile updates can run alongside other agents when car info is mentioned

Your response must be valid JSON:

```json
{{
  "action": "profile_updater|info|modcoach|diagnostic|buildplanner|end",
  "reasoning": "Clear explanation of why this action is chosen",
  "confidence": "high|medium|low"
}}
```

Return ONLY valid JSON. Be intelligent about what the user actually needs.
"""

        print(f"\n🧠 AGENTIC PLANNER (Iteration {iteration}): Analyzing current state...")
        raw = await call_claude(prompt, temperature=0.3)
        decision = parse_agentic_output(raw)
        
        action = decision["action"]
        reasoning = decision["reasoning"]
        
        print(f"🎯 AGENTIC PLANNER: {action} - {reasoning}")
        state["agent_trace"].append(f"AgenticPlanner[{iteration}] → {action}: {reasoning}")
        
        # Execute the chosen action
        if action == "profile_updater":
            print(f"👤 Running PROFILE UPDATER agent...")
            state = await profile_updater_pipeline(state)
        elif action == "info":
            print(f"📚 Running INFO agent...")
            state = await info_pipeline(state)
        elif action == "modcoach":
            print(f"🚀 Running MODCOACH agent...")
            state = await mod_coach_pipeline(state)
        elif action == "diagnostic":
            print(f"🔧 Running DIAGNOSTIC agent...")
            state = await diagnostic_pipeline(state)
        elif action == "buildplanner":
            print(f"📋 Running BUILDPLANNER agent...")
            state = await buildplanner_pipeline(state)
        elif action == "end":
            print(f"✅ AGENTIC PLANNER: Session complete")
            if not state.get("final_message"):
                state["final_message"] = "Session complete. Happy driving!"
            break
    
    if iteration >= max_iterations:
        print(f"⚠️ AGENTIC PLANNER: Reached max iterations, ending session")
        state["final_message"] = "I've reached the maximum number of planning iterations. Please try rephrasing your question if you need more help."
        state["agent_trace"].append(f"AgenticPlanner[{iteration}] → end: Reached maximum iterations")
    
    return state

def parse_agentic_output(response: str) -> Dict[str, Any]:
    try:
        # Clean up the response - remove markdown code blocks if present
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        
        cleaned_response = cleaned_response.strip()
        
        parsed = json.loads(cleaned_response)
        action = parsed.get("action")
        reasoning = parsed.get("reasoning", "")
        
        allowed_actions = {"profile_updater", "modcoach", "diagnostic", "buildplanner", "info", "end"}
        
        if action not in allowed_actions:
            raise ValueError(f"Invalid action: {action}")
        
        return {
            "action": action,
            "reasoning": reasoning
        }
    except Exception as e:
        return {
            "action": "end",
            "reasoning": f"Error parsing response: {str(e)}"
        }