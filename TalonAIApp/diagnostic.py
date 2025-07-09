from typing import List, Dict, Optional, Union, Any
from typing_extensions import TypedDict
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from .claude import call_claude
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


async def diagnostic_pipeline(state):
    """
    Fully dynamic LLM-based diagnostic agent
    """
    
    query = state.get("query", "")
    car_profile = state.get("car_profile", {})
    
    prompt = f"""
You are an expert automotive diagnostic technician. Analyze the user's symptoms and provide comprehensive diagnosis.

User Query: "{query}"
Car Profile: {json.dumps(car_profile, indent=2)}

Instructions:
- Analyze any symptoms described in the query
- Consider the specific car platform and common issues
- Provide likely causes ranked by probability
- Include diagnostic steps and recommended actions
- Be thorough but practical in your recommendations
- Consider safety concerns and urgency

Return JSON:
{{
    "diagnosis": {{
        "most_likely_cause": "primary_diagnosis",
        "confidence": "high|medium|low",
        "explanation": "detailed_explanation_of_the_issue"
    }},
    "possible_causes": [
        {{
            "cause": "alternative_diagnosis",
            "probability": "percentage_likelihood",
            "symptoms_match": "how_well_symptoms_align"
        }}
    ],
    "diagnostic_steps": [
        {{
            "step": "what_to_check_or_test",
            "tools_needed": ["required", "tools"],
            "difficulty": "easy|medium|hard"
        }}
    ],
    "recommended_actions": [
        {{
            "action": "what_to_do",
            "urgency": "immediate|soon|routine",
            "estimated_cost": "$XXX-$XXX"
        }}
    ],
    "safety_concerns": ["any", "safety", "issues"]
}}

Be thorough and consider the specific car platform and its known issues.
"""

    try:
        response = await call_claude(prompt, temperature=0.1)
        
        # Parse response
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]
        
        result = json.loads(cleaned_response)
        
        # Store results in state
        diagnosis = result.get("diagnosis", {})
        state["symptom_summary"] = diagnosis.get("explanation", "")
        state["most_likely_cause"] = diagnosis.get("most_likely_cause", "")
        state["diagnosis_confidence"] = diagnosis.get("confidence", "medium")
        state["possible_causes"] = result.get("possible_causes", [])
        state["diagnostic_steps"] = result.get("diagnostic_steps", [])
        state["recommended_actions"] = result.get("recommended_actions", [])
        state["safety_concerns"] = result.get("safety_concerns", [])
        
        return state
        
    except Exception as e:
        print(f"Error in diagnostic agent: {e}")
        # Fallback response
        state["symptom_summary"] = "I'd be happy to help diagnose car issues. Could you describe the specific symptoms you're experiencing?"
        return state


