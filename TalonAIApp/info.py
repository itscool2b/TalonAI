from typing import List, Dict, Optional, Union, Any
from typing_extensions import TypedDict
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from claude import call_claude

import json
from typing import Any, Dict

def parse_info_initial(output: str) -> Dict[str, Any]:
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
            "answer": parsed.get("answer", ""),
            "tool_call": parsed.get("tool_call")
        }
    except json.JSONDecodeError:
        return {"answer": "", "tool_call": None}



#prompts

init_prompt = PromptTemplate.from_template("""You are the `info` agent in a modular AI system for car enthusiasts. Your role is to answer factual or informational questions related to automotive topics using your own knowledge and external tools if needed.

────────────────────────────────────────────────
📦 USER QUERY
{query}

🧭 AGENT TRACE
{agent_trace}

🧪 TOOL TRACE
{tool_trace}

🧠 YOUR TASK
────────────────────────────────────────────────
1. Understand the user's question.
2. If confident, provide a direct answer.
3. Otherwise, suggest the **most relevant MCP tool** — but only if it's not already in `tool_trace`.

────────────────────────────────────────────────
🛠️ MCP TOOLS
- `lookup_glossary_term`
- `compare_facts`
- `fetch_forum_threads`
- `get_regulation_info`
- `tech_spec_lookup`
- `explain_tuning_concept`

────────────────────────────────────────────────
🧾 RESPONSE FORMAT
```json
{{
  "answer": "...",
  "tool_call": "tool_name_or_null"
}}

⚠️ Return valid JSON only. No extra text.""")

refiner = PromptTemplate.from_template("""You are the `info` agent refining your answer based on retrieved tool data.

────────────────────────────────────────────────
📦 ORIGINAL USER QUERY
{query}

🛠️ MCP TOOL OUTPUT
{tool_output}

🧭 AGENT TRACE
{agent_trace}

🧪 TOOL TRACE
{tool_trace}

🧠 YOUR TASK
Use the tool output to revise your answer. Do NOT reuse information from tools already listed in the trace unless new data changes the answer significantly.

────────────────────────────────────────────────
🧾 RESPONSE FORMAT
Plain string only. No JSON, markdown, or extra text.
""")

#mcp

async def mcp_retrieval(tool_call, query):
    """Mock MCP tool retrieval for info agent"""
    if tool_call == "lookup_glossary_term":
        return {
            "term": "horsepower",
            "definition": "A unit of power equal to 550 foot-pounds per second, used to measure engine output",
            "context": "In automotive terms, horsepower measures the engine's ability to do work over time",
            "related_terms": ["torque", "brake horsepower", "wheel horsepower"]
        }
    elif tool_call == "tech_spec_lookup":
        return {
            "specification": "2023 Acura Integra Engine",
            "displacement": "1.5L Turbo",
            "stock_horsepower": "200 HP",
            "stock_torque": "192 lb-ft",
            "compression_ratio": "10.3:1",
            "fuel_system": "Direct Injection"
        }
    elif tool_call == "explain_tuning_concept":
        return {
            "concept": "ECU Tuning",
            "explanation": "ECU tuning modifies the engine control unit's software to optimize air/fuel ratios, ignition timing, and boost pressure for better performance",
            "benefits": ["Increased horsepower", "Better throttle response", "Improved fuel efficiency"],
            "risks": ["Voided warranty", "Potential engine damage if done incorrectly"]
        }
    elif tool_call == "fetch_forum_threads":
        return {
            "threads": [
                {
                    "title": "Best mods for 2023 Integra",
                    "author": "IntegraOwner2023",
                    "replies": 45,
                    "key_points": ["Cold air intake first", "Exhaust system next", "ECU tune for best results"]
                },
                {
                    "title": "Dyno results after intake + exhaust",
                    "author": "ModdedIntegra",
                    "replies": 23,
                    "key_points": ["+22 HP gain", "Better sound", "Improved throttle response"]
                }
            ]
        }
    else:
        return {
            "tool_error": f"Unknown tool: {tool_call}",
            "fallback_data": "Using general automotive knowledge to answer your question"
        }


#pipeline

async def info_pipeline(state):
    prompt_str = init_prompt.format(query=state['query'],tool_trace=state['tool_trace'], agent_trace=state['agent_trace'])

    raw = await call_claude(prompt_str)
    parsed = parse_info_initial(raw)

    state['info_answer'] = parsed['answer']
    state['agent_trace'].append("info")

    if parsed['tool_call']:
        tool_output = await mcp_retrieval(parsed['tool_call'], query=state['query'])

        
        state.setdefault("tool_trace", []).append({
            "agent": "info",
            "tool": parsed["tool_call"],
            "input": {
                "query": state["query"]
            },
            "output": tool_output
        })

        refinement_prompt = refiner.format(
            query=state['query'],
            tool_output=json.dumps(tool_output, indent=2),tool_trace=state['tool_trace'], agent_trace=state['agent_trace']
        )

        refined = await call_claude(refinement_prompt)
        state['info_answer'] = refined
        state["agent_trace"].append("info_tool_refiner")

    # Set final message to indicate completion
    state["final_message"] = "Information query completed successfully."
    
    return state
