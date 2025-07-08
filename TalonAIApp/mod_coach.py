from typing import List, Dict, Optional, Union, Any
from typing_extensions import TypedDict
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from claude import call_claude

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
    prompt_str = prompt.format(car_profile=json.dumps(state["car_profile"], indent=2), tool_trace=state['tool_trace'], agent_trace=state['agent_trace'])
    output = await call_claude(prompt_str)
    parsed = parse_modcoach_output(output)

    state["mod_recommendations"] = parsed["mod_recommendations"]
    state["flags"].update(parsed["additional_flags"])
    state["tool_call"] = parsed["tool_call"]
    state["agent_trace"].append("modcoach")

    tool_output = {}
    if parsed["tool_call"]:
        tool_output = await mcp_retrieval(
            parsed["tool_call"],
            car_profile=state["car_profile"],
            mods=parsed["mod_recommendations"]
        )

        
        state.setdefault("tool_trace", []).append({
            "agent": "modcoach",
            "tool": parsed["tool_call"],
            "input": {
                "car_profile": state["car_profile"],
                "mod_recommendations": parsed["mod_recommendations"]
            },
            "output": tool_output
        })

    refinement_prompt = modcoach_tool_refiner.format(
        car_profile=json.dumps(state["car_profile"], indent=2),
        mod_recommendations=json.dumps(parsed["mod_recommendations"], indent=2),
        tool_output=json.dumps(tool_output, indent=2),tool_trace=state['tool_trace'], agent_trace=state['agent_trace']
    )
    refined_raw = await call_claude(refinement_prompt)

    def parse_refined_mods(output: str) -> List[Dict[str, str]]:
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
            
            return json.loads(cleaned_output).get("mod_recommendations", [])
        except Exception as e:
            return []

    refined_mods = parse_refined_mods(refined_raw)
    state["mod_recommendations"] = refined_mods
    state["agent_trace"].append("modcoach_tool_refiner")
    
    # Set final message to indicate completion
    state["final_message"] = "Mod recommendations completed successfully."
    
    return state
