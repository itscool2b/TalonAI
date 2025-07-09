from typing import List, Dict, Optional, Union, Any
from typing_extensions import TypedDict
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from .claude import call_claude

import json
from typing import Any, Dict

buildplanner_prompt = PromptTemplate.from_template("""
You are the `buildplanner` agent in a modular AI system that helps car enthusiasts plan long-term upgrade sequences. Your job is to generate a complete **multi-stage build plan** for the user's car based on their profile, goals, and prior mod recommendations.

────────────────────────────────────────────────
📦 CAR PROFILE
{car_profile}

💡 EXISTING MOD RECOMMENDATIONS
{mod_recommendations}

🧭 AGENT TRACE
{agent_trace}

🧪 TOOL TRACE
{tool_trace}

────────────────────────────────────────────────
🧠 YOUR TASK
1. Create a **3–5 stage build plan** with sequential upgrade steps (e.g. intake → downpipe → tune).
2. Base your plan on the user's profile, goals, and any previously suggested mods.
3. If useful, suggest one MCP tool to enrich or validate the build plan — but **only if it hasn't been used already**, based on the `tool_trace`.

────────────────────────────────────────────────
🛠️ MCP TOOLS
- `suggest_install_order`: Optimal order to stack compatible mods
- `estimate_mod_cost`: Budget planning for each build stage
- `check_compatibility`: Ensure parts work with car platform

────────────────────────────────────────────────
🧾 RESPONSE FORMAT
```json
{{
  "build_plan": [
    {{ "stage": 1, "mods": ["Cold Air Intake", "Turbo Inlet Pipe"] }},
    {{ "stage": 2, "mods": ["Downpipe", "Stage 1 Tune"] }}
  ],
  "tool_call": "tool_name_or_null"
}}

⚠️ Output JSON only — no markdown, no extra text.
""")

buildplanner_refiner = PromptTemplate.from_template("""
You are the `buildplanner` agent refining your long-term car upgrade plan using external tool data.

────────────────────────────────────────────────
📦 CAR PROFILE
{car_profile}

🧱 ORIGINAL BUILD PLAN
{build_plan}

🛠️ MCP TOOL OUTPUT
{tool_output}

🧭 AGENT TRACE
{agent_trace}

🧪 TOOL TRACE
{tool_trace}

────────────────────────────────────────────────
🧠 YOUR TASK
1. Adjust, confirm, or reorder build stages based on fitment, cost, or install strategy.
2. Remove incompatible mods or re-sequence upgrades if needed.
3. Ensure the final build path makes sense for the user's goals and platform.

────────────────────────────────────────────────
🧾 RESPONSE FORMAT
```json
{{
  "build_plan": [
    {{ "stage": 1, "mods": ["..."] }},
    {{ "stage": 2, "mods": ["..."] }}
  ]
}}

⚠️ No markdown, no extra text — plain JSON only.
""")

def parse_buildplanner_output(raw: str) -> Dict[str, Any]:
    try:
        # Clean up the response - remove markdown code blocks if present
        cleaned_raw = raw.strip()
        if cleaned_raw.startswith("```json"):
            cleaned_raw = cleaned_raw[7:]
        if cleaned_raw.startswith("```"):
            cleaned_raw = cleaned_raw[3:]
        if cleaned_raw.endswith("```"):
            cleaned_raw = cleaned_raw[:-3]
        
        cleaned_raw = cleaned_raw.strip()
        
        parsed = json.loads(cleaned_raw)
        return {
            "build_plan": parsed.get("build_plan", []),
            "tool_call": parsed.get("tool_call")
        }
    except json.JSONDecodeError:
        return {
            "build_plan": [],
            "tool_call": None,
            "error": "parse_error"
        }

def parse_buildplanner_refined(raw: str) -> List[Dict[str, Any]]:
    try:
        # Clean up the response - remove markdown code blocks if present
        cleaned_raw = raw.strip()
        if cleaned_raw.startswith("```json"):
            cleaned_raw = cleaned_raw[7:]
        if cleaned_raw.startswith("```"):
            cleaned_raw = cleaned_raw[3:]
        if cleaned_raw.endswith("```"):
            cleaned_raw = cleaned_raw[:-3]
        
        cleaned_raw = cleaned_raw.strip()
        
        return json.loads(cleaned_raw).get("build_plan", [])
    except json.JSONDecodeError:
        return []

async def mcp_retrieval(tool_call: str, **kwargs) -> Dict[str, Any]:
    """Mock MCP tool retrieval for buildplanner agent"""
    if tool_call == "suggest_install_order":
        return {
            "optimal_order": [
                {"stage": 1, "mods": ["Cold Air Intake", "High Flow Air Filter"]},
                {"stage": 2, "mods": ["Cat-Back Exhaust System"]},
                {"stage": 3, "mods": ["ECU Tune", "Downpipe"]},
                {"stage": 4, "mods": ["Intercooler Upgrade", "Charge Pipes"]},
                {"stage": 5, "mods": ["Turbo Upgrade", "Fuel System"]}
            ],
            "reasoning": "This order maximizes gains while maintaining reliability",
            "estimated_timeline": "3-6 months for full build"
        }
    elif tool_call == "estimate_mod_cost":
        return {
            "total_build_cost": "$3,500-5,200",
            "cost_breakdown": {
                "stage_1": "$400-600",
                "stage_2": "$800-1200",
                "stage_3": "$1200-1800",
                "stage_4": "$600-900",
                "stage_5": "$500-700"
            },
            "labor_estimate": "$800-1200",
            "dyno_tuning": "$300-500"
        }
    elif tool_call == "check_compatibility":
        return {
            "compatible_parts": [
                "Injen Cold Air Intake",
                "AWE Touring Exhaust",
                "Hondata FlashPro",
                "PRL Intercooler",
                "RV6 Downpipe"
            ],
            "incompatible_parts": [],
            "platform_notes": "2023 Integra has excellent aftermarket support",
            "warranty_impact": "Some mods may void powertrain warranty"
        }
    else:
        return {
            "tool_error": f"Unknown tool: {tool_call}",
            "fallback_data": "Using general automotive knowledge for build planning"
        }

async def buildplanner_pipeline(state):
    """
    Fully dynamic LLM-based build planner agent
    """
    
    query = state.get("query", "")
    car_profile = state.get("car_profile", {})
    
    prompt = f"""
You are a master build planning expert. Create comprehensive, staged modification plans for automotive builds.

User Query: "{query}"
Car Profile: {json.dumps(car_profile, indent=2)}

Instructions:
- Create a logical, staged build plan specific to their car and goals
- Start with supporting modifications, then move to power modifications
- Consider budget, timeline, and complexity progression
- Include realistic costs and timeframes
- Ensure each stage builds upon the previous ones
- Be specific to their car platform and goals

Return JSON:
{{
    "build_plan": [
        {{
            "stage": 1,
            "name": "descriptive_stage_name",
            "timeframe": "estimated_time_to_complete",
            "total_cost": "$XXX-$XXX",
            "priority": "high|medium|low",
            "modifications": [
                {{
                    "name": "specific_modification",
                    "cost": "$XXX-$XXX",
                    "install_time": "time_estimate",
                    "justification": "why_this_modification_in_this_stage"
                }}
            ],
            "expected_results": "what_this_stage_achieves",
            "prerequisites": ["required", "supporting", "mods"]
        }}
    ],
    "total_timeline": "overall_build_timeline",
    "total_cost": "$XXX-$XXX",
    "final_power_estimate": "estimated_final_horsepower",
    "build_philosophy": "approach_and_reasoning",
    "important_considerations": ["key", "notes", "and", "warnings"]
}}

Create 3-5 logical stages that build upon each other progressively.
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
        state["build_plan"] = result.get("build_plan", [])
        state["total_timeline"] = result.get("total_timeline", "")
        state["total_build_cost"] = result.get("total_cost", "")
        state["final_power_estimate"] = result.get("final_power_estimate", "")
        state["build_philosophy"] = result.get("build_philosophy", "")
        state["build_considerations"] = result.get("important_considerations", [])
        
        return state
        
    except Exception as e:
        print(f"Error in build planner agent: {e}")
        # Fallback response
        state["build_plan"] = [{
            "stage": 1,
            "name": "Foundation Stage",
            "modifications": [{"name": "Performance Air Filter", "justification": "Starting point for performance improvements"}]
        }]
        return state
