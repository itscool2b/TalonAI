from typing import List, Dict, Optional, Union, Any
from typing_extensions import TypedDict
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from .claude import call_claude

prompt = PromptTemplate.from_template("""You are the `modcoach` agent in a modular AI system that assists car enthusiasts with planning performance upgrades. Your job is to recommend intelligent, goal-aligned modifications for the user's car.

────────────────────────────────────────────────
📦 INPUT: Car Profile
{car_profile}

🧭 AGENT TRACE
{agent_trace}

🧪 TOOL TRACE
{tool_trace}

🧠 YOUR TASK
────────────────────────────────────────────────
1. Evaluate the profile and current mods.
2. Suggest a set of **next upgrade recommendations** based on typical modding paths.
3. DO NOT reuse any tools listed in the `tool_trace` unless the car profile or goals have changed significantly.

For each mod, include:
- `name`: Name of the upgrade
- `type`: Category
- `justification`: Why this mod fits the profile

Then suggest a **tool_call** for further detail — only if it hasn't already been used.

────────────────────────────────────────────────
🧾 RESPONSE FORMAT
```json
{{
  "mod_recommendations": [...],
  "additional_flags": {{...}},
  "tool_call": "tool_name_or_null"
}}

⚠️ Return only valid JSON. No extra text.
""")

modcoach_tool_refiner = PromptTemplate.from_template("""
You are the `modcoach` agent refining your earlier modification suggestions based on retrieved tool data.

────────────────────────────────────────────────
📦 CAR PROFILE
{car_profile}

📝 PRIOR MOD RECOMMENDATIONS:
{mod_recommendations}

🛠️ MCP TOOL OUTPUT:
{tool_output}

🧭 AGENT TRACE
{agent_trace}

🧪 TOOL TRACE
{tool_trace}

🧠 YOUR TASK
────────────────────────────────────────────────
Using the tool data, validate or revise the mod suggestions.

If any tools in `tool_trace` were already used, don't repeat their findings unless new data significantly alters your reasoning.

────────────────────────────────────────────────
🧾 RESPONSE FORMAT
```json
{{
  "mod_recommendations": [...]
}}

⚠️ Return only valid JSON. No markdown or commentary.
""")

import json
from typing import Any, Dict, Optional

def parse_modcoach_output(output: str) -> Dict[str, Any]:
    """
    Parses the raw string output from Claude (modcoach agent).
    Returns a dict with:
        - mod_recommendations: list of mod dicts
        - additional_flags: dict of boolean flags
        - tool_call: str
    """
    try:
        # Clean up the response - remove markdown code blocks if present
        cleaned_output = output.strip()
        if cleaned_output.startswith("```json"):
            cleaned_output = cleaned_output[7:]
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output[3:]
        if cleaned_output.endswith("```"):
            cleaned_output = cleaned_output[:-3]
        
        cleaned_output = cleaned_output.strip()
        
        parsed = json.loads(cleaned_output)
        return {
            "mod_recommendations": parsed.get("mod_recommendations", []),
            "additional_flags": parsed.get("additional_flags", {}),
            "tool_call": parsed.get("tool_call", None)
        }
    except json.JSONDecodeError as e:
        print(f"DEBUG: Modcoach parse error: {e}")
        print(f"DEBUG: Raw output: {output}")
        return {
            "mod_recommendations": [],
            "additional_flags": {"parse_error": True},
            "tool_call": None
        }

async def mcp_retrieval(tool_name, car_profile, mods):
    """Mock MCP tool retrieval for modcoach agent"""
    if tool_name == "check_compatibility":
        return {
            "compatible_mods": [mod["name"] for mod in mods if "intake" in mod["name"].lower() or "exhaust" in mod["name"].lower()],
            "incompatible_mods": [],
            "fitment_notes": "All suggested mods are compatible with your Acura Integra platform",
            "installation_difficulty": "Easy to Moderate"
        }
    elif tool_name == "estimate_power_gains":
        return {
            "estimated_hp_gain": "15-25 HP",
            "estimated_tq_gain": "10-15 lb-ft",
            "dyno_notes": "Based on similar builds on 2023 Integra platform",
            "recommended_tune": "Stage 1 ECU tune recommended for optimal gains"
        }
    elif tool_name == "price_analysis":
        return {
            "total_cost": "$800-1200",
            "cost_breakdown": {
                "intake": "$200-300",
                "exhaust": "$400-600",
                "tune": "$200-300"
            },
            "value_rating": "High - Good power per dollar ratio"
        }
    else:
        return {
            "tool_error": f"Unknown tool: {tool_name}",
            "fallback_data": "Using general automotive knowledge for recommendations"
        }

async def mod_coach_pipeline(state):
    """
    Fully dynamic LLM-based modification coach agent
    """
    
    query = state.get("query", "")
    car_profile = state.get("car_profile", {})
    
    prompt = f"""
You are a performance modification expert and coach. Generate specific, actionable modification recommendations.

User Query: "{query}"
Car Profile: {json.dumps(car_profile, indent=2)}

Instructions:
- Generate 3-5 specific modification recommendations
- Be realistic about costs and gains
- Consider the user's car platform specifically
- Prioritize modifications by impact and cost-effectiveness
- Include installation difficulty and supporting modifications needed
- Be enthusiastic but realistic about expectations

Return JSON:
{{
    "recommendations": [
        {{
            "name": "specific_modification_name",
            "type": "intake|exhaust|engine|suspension|etc",
            "priority": "high|medium|low",
            "estimated_cost": "$XXX-$XXX",
            "power_gain": "estimated_hp_gain",
            "justification": "why_this_mod_for_their_car",
            "difficulty": "easy|medium|hard",
            "supporting_mods": ["required", "supporting", "modifications"]
        }}
    ],
    "total_estimated_cost": "$XXX-$XXX",
    "expected_results": "overall_performance_improvement",
    "installation_order": ["mod1", "mod2", "mod3"],
    "important_notes": ["key", "considerations"]
}}

Be specific to their car platform and provide realistic recommendations.
"""

    try:
        response = await call_claude(prompt, temperature=0.2)
        
        # Parse response
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]
        
        result = json.loads(cleaned_response)
        
        # Store results in state
        state["mod_recommendations"] = result.get("recommendations", [])
        state["total_mod_cost"] = result.get("total_estimated_cost", "")
        state["expected_results"] = result.get("expected_results", "")
        state["installation_order"] = result.get("installation_order", [])
        state["mod_notes"] = result.get("important_notes", [])
        
        return state
        
    except Exception as e:
        print(f"Error in mod coach agent: {e}")
        # Fallback response
        state["mod_recommendations"] = [{
            "name": "Performance Air Filter",
            "type": "intake",
            "justification": "Easy first modification with immediate throttle response improvement"
        }]
        return state
