from typing import List, Dict, Optional, Union, Any
from typing_extensions import TypedDict
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from claude import call_claude
import json
from typing import Dict, Any

def parse_diagnostic_output(output: str) -> Dict[str, Any]:
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
            "symptom_summary": parsed.get("symptom_summary", ""),
            "followup_recommendations": parsed.get("followup_recommendations", [])
        }
    except json.JSONDecodeError:
        return {
            "symptom_summary": "",
            "followup_recommendations": [],
            "error": "parse_error"
        }

init_prompt = PromptTemplate.from_template("""
You are the `diagnostic` agent in a modular AI system that helps car enthusiasts identify likely causes of mechanical issues.

────────────────────────────────────────────────
📦 CAR PROFILE
{car_profile}

User Symptom Report:
{query}

🧭 AGENT TRACE
{agent_trace}

🧪 TOOL TRACE
{tool_trace}

🧠 YOUR TASK
────────────────────────────────────────────────
1. Analyze the issue based on the car.
2. Suggest a summary and follow-up steps.
3. Suggest a tool ONLY if it hasn't been used yet (per `tool_trace`).

────────────────────────────────────────────────
🛠️ MCP TOOLS
- `lookup_official_dtc`
- `symptom_fault_matcher`
- `get_known_issues`

────────────────────────────────────────────────
🧾 RESPONSE FORMAT
```json
{{
  "symptom_summary": "...",
  "followup_recommendations": [...],
  "tool_call": "tool_name_or_null"
}}

⚠️ JSON only — no extra text.
""")
refiner = PromptTemplate.from_template("""
You are the `diagnostic` agent refining your diagnosis using tool output.

────────────────────────────────────────────────
📦 CAR PROFILE
{car_profile}

📝 USER SYMPTOM REPORT
{query}

🛠️ TOOL OUTPUT
{tool_output}

🧭 AGENT TRACE
{agent_trace}

🧪 TOOL TRACE
{tool_trace}

🧠 YOUR TASK
Use the tool data to improve or confirm your summary.

Avoid repeating findings from tools already in `tool_trace` unless the information differs from before.

────────────────────────────────────────────────
🧾 RESPONSE FORMAT
```json
{{
  "symptom_summary": "...",
  "followup_recommendations": [...]
}}

⚠️ Valid JSON only. No markdown or comments.
""")
async def mcp_retrieval(tool_call, car_profile, symptom_query):
    """Mock MCP tool retrieval for diagnostic agent"""
    if tool_call == "lookup_official_dtc":
        return {
            "dtc_codes": ["P0300", "P0301", "P0302"],
            "descriptions": ["Random/Multiple Cylinder Misfire Detected", "Cylinder 1 Misfire Detected", "Cylinder 2 Misfire Detected"],
            "severity": "Medium",
            "common_causes": ["Faulty spark plugs", "Bad ignition coils", "Vacuum leaks", "Low fuel pressure"]
        }
    elif tool_call == "symptom_fault_matcher":
        return {
            "matched_symptoms": ["engine misfire", "rough idle", "power loss"],
            "likely_causes": [
                {"cause": "Faulty ignition system", "confidence": 85},
                {"cause": "Vacuum leak", "confidence": 70},
                {"cause": "Fuel system issue", "confidence": 60}
            ],
            "diagnostic_steps": [
                "Check spark plugs and ignition coils",
                "Inspect for vacuum leaks",
                "Test fuel pressure",
                "Scan for trouble codes"
            ]
        }
    elif tool_call == "get_known_issues":
        return {
            "known_issues": [
                {
                    "issue": "Ignition coil failure",
                    "frequency": "Common on 2023 Integra",
                    "symptoms": ["Misfire", "Rough idle", "Check engine light"],
                    "solution": "Replace affected ignition coil(s)"
                },
                {
                    "issue": "Turbo wastegate sticking",
                    "frequency": "Occasional",
                    "symptoms": ["Power loss", "Boost issues", "Engine hesitation"],
                    "solution": "Clean or replace wastegate actuator"
                }
            ],
            "tsb_references": ["TSB-2023-001", "TSB-2023-015"]
        }
    else:
        return {
            "tool_error": f"Unknown tool: {tool_call}",
            "fallback_data": "Using general diagnostic knowledge for analysis"
        }


async def diagnostic_pipeline(state: Dict[str, Any]) -> Dict[str, Any]:
    prompt_str = init_prompt.format(
        car_profile=json.dumps(state["car_profile"], indent=2),
        query=state["query"],
        agent_trace=json.dumps(state["agent_trace"]),
        tool_trace=json.dumps(state["tool_trace"])
    )

    raw = await call_claude(prompt_str)

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
    except json.JSONDecodeError:
        parsed = {
            "symptom_summary": "",
            "tool_call": None
        }

    state["symptom_summary"] = parsed.get("symptom_summary", "")
    state["agent_trace"].append("diagnostic")

    tool_call = parsed.get("tool_call")
    tool_output = {}

    if tool_call:
        tool_output = await mcp_retrieval(
            tool_call,
            car_profile=state["car_profile"],
            symptom_query=state["query"]
        )

        
        state["tool_trace"].append({
            "agent": "diagnostic",
            "tool": tool_call,
            "input": {
                "car_profile": state["car_profile"],
                "symptom_query": state["query"]
            },
            "output": tool_output
        })

        refinement_prompt = refiner.format(
            car_profile=json.dumps(state["car_profile"], indent=2),
            query=state["query"],
            tool_output=json.dumps(tool_output, indent=2),
            agent_trace=json.dumps(state["agent_trace"]),
            tool_trace=json.dumps(state["tool_trace"])
        )

        refined = await call_claude(refinement_prompt)
        refined_parsed = parse_diagnostic_output(refined)

        
        state["symptom_summary"] = refined_parsed.get("symptom_summary", "")
        state["agent_trace"].append("diagnostic_tool_refiner")

    # Set final message to indicate completion
    state["final_message"] = "Diagnostic analysis completed successfully."
    
    return state


