from typing import Dict, Any
import json
from .claude import call_claude
from .state import AgentState
from .memory import get_recent_memory, format_memory_for_prompt
from .info import info_pipeline
from .mod_coach import mod_coach_pipeline
from .diagnostic import diagnostic_pipeline
from .build_planner import buildplanner_pipeline

async def run_agentic_planner(state: AgentState) -> AgentState:
    """
    Agentic planner that can adapt its strategy based on results
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
You are an **Autonomous Planning Agent** in a modular AI system for car enthusiasts. Unlike a simple router, you have the ability to:

1. **Dynamically adapt** your strategy based on intermediate results
2. **Decide when to stop** or continue based on what you discover
3. **Request additional information** if needed
4. **Change your approach** if initial attempts don't work
5. **Learn from context** and previous interactions

────────────────────────────────────────────────
🚗 AVAILABLE CAPABILITIES
────────────────────────────────────────────────
• `modcoach`     — Recommends performance upgrades based on car profile and goals  
• `diagnostic`   — Analyzes mechanical symptoms and problems
• `buildplanner` — Creates long-term build plans
• `info`         — Provides factual information

• `end`          — Complete the session when satisfied

────────────────────────────────────────────────
📦 CURRENT CONTEXT
────────────────────────────────────────────────
User Query: {state.get('query', '')}

Car Profile: {json.dumps(state.get('car_profile', {}), indent=2)}

Previous Actions: {json.dumps(state.get('agent_trace', []), indent=2)}

Current State: {json.dumps(state.get('flags', {}), indent=2)}

Build Plan: {json.dumps(state.get('build_plan'), indent=2) if state.get('build_plan') else 'None'}

Mod Recommendations: {json.dumps(state.get('mod_recommendations'), indent=2) if state.get('mod_recommendations') else 'None'}

Symptom Summary: {state.get('symptom_summary') or 'None'}

{memory_context}

────────────────────────────────────────────────
🧠 AGENTIC DECISION MAKING
────────────────────────────────────────────────
You are NOT a simple classifier. You are an autonomous agent that:

1. **Evaluates the current situation** - What do we know? What's missing?
2. **Plans the next action** - What would be most valuable to do next?
3. **Adapts to results** - If an action reveals new information, how should you respond?
4. **Knows when to stop** - Are we satisfied with the outcome?

**Think like a real agent:**
- "Can the info agent answer this question directly with general automotive knowledge?"
- "Does this require specialized diagnosis tools or symptom analysis?"
- "Does this need specific mod recommendations based on car profile?" 
- "Does this require multi-stage build planning?"
- "Is this a complete answer or do we need more specialized help?"

**DECISION LOGIC:**
1. **Start with info agent** for any question that can be answered with general knowledge
2. **Use diagnostic agent** only when specific symptoms need analysis or troubleshooting tools
3. **Use modcoach agent** only when specific performance modifications are requested  
4. **Use buildplanner agent** only when multi-stage build sequences are needed
5. **End session** when the user's question has been fully addressed

**EFFICIENCY RULES:**
- **If info agent has already run and provided a complete answer** → END the session
- **Don't repeat the same agent multiple times** unless new information is needed
- **Simple greetings and general questions** → info agent ONCE, then END

**WHEN TO END:**
- Info agent just handled a greeting (hello, hi, hey) → END immediately
- Info agent provided a complete answer to a general question → END immediately  
- Any agent provided what the user requested → END immediately
- User's question has been fully addressed → END immediately

**Your response must be valid JSON:**

```json
{{
  "action": "info",
  "reasoning": "This is a general question the info agent can answer with automotive knowledge"
}}
```

**OR when specialized tools are needed:**

```json
{{
  "action": "diagnostic",
  "reasoning": "User reports specific symptoms that require diagnostic tools and analysis"
}}
```

**OR to end:**

```json
{{
  "action": "end",
  "reasoning": "Have provided comprehensive answer to user's query",
  "summary": "User now has the information and recommendations they requested"
}}
```

🛑 Return ONLY valid JSON. No explanations outside the JSON.
"""

        print(f"\n🧠 AGENTIC PLANNER (Iteration {iteration}): Analyzing current state...")
        raw = await call_claude(prompt)
        decision = parse_agentic_output(raw)
        
        action = decision["action"]
        reasoning = decision["reasoning"]
        
        print(f"🎯 AGENTIC PLANNER: {action} - {reasoning}")
        state["agent_trace"].append(f"AgenticPlanner[{iteration}] → {action}: {reasoning}")
        
        # Execute the chosen action
        if action == "modcoach":
            print(f"🚀 Running MODCOACH agent...")
            state = await mod_coach_pipeline(state)
        elif action == "diagnostic":
            print(f"🔧 Running DIAGNOSTIC agent...")
            state = await diagnostic_pipeline(state)
        elif action == "buildplanner":
            print(f"📋 Running BUILDPLANNER agent...")
            state = await buildplanner_pipeline(state)
        elif action == "info":
            print(f"📚 Running INFO agent...")
            state = await info_pipeline(state)

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
        
        allowed_actions = {"modcoach", "diagnostic", "buildplanner", "info", "end"}
        
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