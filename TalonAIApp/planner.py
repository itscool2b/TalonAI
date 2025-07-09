from typing import List, Dict, Optional, Union, Any, TypedDict
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from .claude import call_claude
import json
from .state import AgentState
from .mod_coach import mod_coach_pipeline
from .info import info_pipeline
from .diagnostic import diagnostic_pipeline
from .build_planner import buildplanner_pipeline
from .memory import get_recent_memory, format_memory_for_prompt
#

# More agentic planner that can adapt based on results
agentic_planner = PromptTemplate.from_template("""
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
User Query: {query}

Car Profile: {car_profile}

Previous Actions: {agent_trace}

Current State: {flags}

Build Plan: {build_plan}

Mod Recommendations: {mod_recommendations}

Symptom Summary: {symptom_summary}

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
- "I need to understand the car first before recommending mods"
- "The diagnostic revealed a serious problem - I should focus on that before mods"
- "The user seems confused about turbocharging - let me explain first"
- "I have enough information now to give a comprehensive answer"
- "The user just said hello/hi/greeting - I should use info agent to welcome them"
- "This is a simple greeting or non-automotive question - info agent can handle it"
- "User hasn't described any symptoms - don't use diagnostic agent"
- "User hasn't asked for mods or performance - don't use modcoach agent"

**IMPORTANT GUIDELINES:**
- **Simple greetings** (hello, hi, hey) → use `info` agent for friendly welcome
- **General questions** about cars → use `info` agent  
- **Performance/upgrade requests** → use `modcoach` agent
- **Symptoms/problems** (noises, issues, errors) → use `diagnostic` agent
- **Long-term build planning** → use `buildplanner` agent
- **Complete responses** → use `end` action

**Your response must be valid JSON:**

```json
{{
  "action": "modcoach",
  "reasoning": "User wants performance upgrades and we have a complete car profile"
}}
```

**OR for complex scenarios:**

```json
{{
  "action": "diagnostic",
  "reasoning": "User reports symptoms that need investigation first"
}}
```

**OR for greetings:**

```json
{{
  "action": "info",
  "reasoning": "User is greeting me or asking a general question - should provide friendly welcome and guidance"
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
    """)

#

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

async def run_agentic_planner(state):
    """
    Agentic planner that can adapt its strategy based on results
    """
    max_iterations = 5  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Get recent memory for context
        # Temporarily disable memory until table is created
        # memories = await get_recent_memory(state.get("user_id", ""), limit=3)
        # memory_context = format_memory_for_prompt(memories)
        memory_context = "No previous conversations found."
        
        prompt = agentic_planner.format(
            query=state["query"],
            car_profile=json.dumps(state["car_profile"], indent=2),
            agent_trace=json.dumps(state["agent_trace"], indent=2),
            flags=json.dumps(state["flags"], indent=2),
            build_plan=json.dumps(state["build_plan"], indent=2) if state["build_plan"] else "None",
            mod_recommendations=json.dumps(state["mod_recommendations"], indent=2) if state["mod_recommendations"] else "None",
            symptom_summary=state["symptom_summary"] or "None",
            memory_context=memory_context
        )
        
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
    
    return state

# Keep the old planner for backward compatibility
classifier = PromptTemplate.from_template("""
You are the central **Planner Agent** in a modular AI system for car enthusiasts. Your role is to evaluate the current system state and select the **most appropriate sub-agents** to run in order to best fulfill the user's request.

────────────────────────────────────────────────
🚗 SYSTEM OVERVIEW (Available Sub-Agents)
────────────────────────────────────────────────
• `modcoach`     — Recommends next performance upgrades based on car profile and goals  
• `diagnostic`   — Analyzes mechanical symptoms like noises, power loss, or misfires  
• `buildplanner` — Constructs a multi-step build plan for long-term performance goals  
• `info`         — Answers direct factual or informational queries  
• `end`          — Ends the session once the user's request has been fully handled  

────────────────────────────────────────────────
📦 CURRENT SYSTEM STATE
────────────────────────────────────────────────
User Query:
{query}

Car Profile:
{car_profile}

Agent Trace:
{agent_trace}

Flags:
{flags}

Build Plan:
{build_plan}

Mod Recommendations:
{mod_recommendations}

Symptom Summary:
{symptom_summary}

────────────────────────────────────────────────
🧠 DECISION INSTRUCTION
────────────────────────────────────────────────
Analyze the user's query and determine which agents need to run. Complex queries may require MULTIPLE agents.

**GUIDELINES:**
- If the user asks about mods, upgrades, or performance → include `modcoach`
- If the user reports symptoms or problems → include `diagnostic`  
- If the user wants a long-term build plan → include `buildplanner`
- If the user asks factual questions → include `info`
- Only include `end` if the user's request has been COMPLETELY fulfilled

**MULTI-AGENT SCENARIOS:**
- "I want more horsepower but I'm hearing noises" → `["diagnostic", "modcoach"]`
- "I need a build plan and what is ECU tuning?" → `["info", "buildplanner"]`
- "My car is misfiring and I want to know about turbo upgrades" → `["diagnostic", "info", "modcoach"]`

Your response must follow this exact format:

```json
{{
  "agents": ["diagnostic", "modcoach"],
  "additional_flags": {{
    "needs_diag": true,
    "profile_missing": false
  }}
}}

🛑 Do NOT include explanations, comments, or extra text. Only return valid JSON.
    """)

#

def parse_planner_output(response: str) -> Dict[str, Any]:
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
        agents = parsed.get("agents", [parsed.get("next_agent")])  # Support both old and new format
        flags = parsed.get("additional_flags", {})
        allowed = {"modcoach", "diagnostic", "buildplanner", "profile", "info", "end"}
        
        # Validate all agents
        for agent in agents:
            if agent not in allowed:
                raise ValueError(f"Invalid agent returned: {agent}")
        
        return {"agents": agents, "flags": flags}
    except Exception as e:
        return {"agents": ["end"], "flags": {}, "error": str(e)}

async def run_planner(state):
    prompt = classifier.format(
        query=state["query"],
        car_profile=json.dumps(state["car_profile"], indent=2),
        agent_trace=json.dumps(state["agent_trace"], indent=2),
        flags=json.dumps(state["flags"], indent=2),
        build_plan=json.dumps(state["build_plan"], indent=2) if state["build_plan"] else "None",
        mod_recommendations=json.dumps(state["mod_recommendations"], indent=2) if state["mod_recommendations"] else "None",
        symptom_summary=state["symptom_summary"] or "None"
    )
    
    print(f"\n🔄 PLANNER: Processing query: '{state['query']}'")
    raw = await call_claude(prompt)
    parsed = parse_planner_output(raw)
    agents = parsed["agents"]
    flags = parsed["flags"]
    
    print(f"🎯 PLANNER: Chose agents {agents} with flags: {flags}")
    
    state["agent_trace"].append(f"Planner → {', '.join(agents)}")
    state["flags"].update(flags)
    
    # Run all selected agents in sequence
    for agent in agents:
        if agent == "modcoach":
            print(f"🚀 Running MODCOACH agent...")
            state = await mod_coach_pipeline(state)
        elif agent == "diagnostic":
            print(f"🔧 Running DIAGNOSTIC agent...")
            state = await diagnostic_pipeline(state)
        elif agent == "buildplanner":
            print(f"📋 Running BUILDPLANNER agent...")
            state = await buildplanner_pipeline(state)
        elif agent == "info":
            print(f"📚 Running INFO agent...")
            state = await info_pipeline(state)
        elif agent == "end":
            print(f"✅ PLANNER: Ending session")
            state["final_message"] = "Session complete. Happy driving."
            break
    
    return state

#


#