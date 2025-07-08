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

async def buildplanner_pipeline(state: Dict[str, Any]) -> Dict[str, Any]:
    prompt_str = buildplanner_prompt.format(
        car_profile=json.dumps(state["car_profile"], indent=2),
        mod_recommendations=json.dumps(state["mod_recommendations"], indent=2),
        agent_trace=json.dumps(state["agent_trace"]),
        tool_trace=json.dumps(state["tool_trace"])
    )

    raw = await call_claude(prompt_str)
    parsed = parse_buildplanner_output(raw)

    state["build_plan"] = parsed["build_plan"]
    state["agent_trace"].append("buildplanner")

    tool_call = parsed.get("tool_call")
    tool_output = {}

    if tool_call:
        tool_output = await mcp_retrieval(
            tool_call,
            car_profile=state["car_profile"],
            build_plan=parsed["build_plan"]
        )

        state["tool_trace"].append({
            "agent": "buildplanner",
            "tool": tool_call,
            "input": {
                "car_profile": state["car_profile"],
                "build_plan": parsed["build_plan"]
            },
            "output": tool_output
        })

        refinement_prompt = buildplanner_refiner.format(
            car_profile=json.dumps(state["car_profile"], indent=2),
            build_plan=json.dumps(parsed["build_plan"], indent=2),
            tool_output=json.dumps(tool_output, indent=2),
            agent_trace=json.dumps(state["agent_trace"]),
            tool_trace=json.dumps(state["tool_trace"])
        )

        refined_raw = await call_claude(refinement_prompt)
        refined_plan = parse_buildplanner_refined(refined_raw)

        if refined_plan:
            state["build_plan"] = refined_plan

        state["agent_trace"].append("buildplanner_tool_refiner")

    # Set final message to indicate completion
    state["final_message"] = "Build plan completed successfully."
    
    return state
