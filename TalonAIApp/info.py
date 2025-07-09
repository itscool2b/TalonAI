from typing import List, Dict, Optional, Union, Any
from typing_extensions import TypedDict
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from .claude import call_claude

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

init_prompt = PromptTemplate.from_template("""You are the `info` agent in a modular AI system for car enthusiasts. Your role is to provide comprehensive answers to any automotive question using your extensive automotive knowledge.

────────────────────────────────────────────────
📦 USER QUERY
{query}

🧭 AGENT TRACE
{agent_trace}

🧪 TOOL TRACE
{tool_trace}

🧠 YOUR TASK
────────────────────────────────────────────────
1. **Provide a comprehensive answer** using your automotive knowledge for:
   - General car questions and explanations
   - Greetings and introductions
   - Technical concepts and definitions  
   - How automotive systems work
   - General advice and guidance

2. **Only use tools** if you need specific data you don't have:
   - Exact specifications for specific car models
   - Current forum discussions or community feedback
   - Regulatory information or technical standards

3. **Be conversational and helpful** - if someone greets you, respond warmly and ask how you can help with their car.

────────────────────────────────────────────────
🛠️ MCP TOOLS (use only when needed)
- `lookup_glossary_term` - for specific technical definitions
- `tech_spec_lookup` - for exact car specifications
- `fetch_forum_threads` - for community discussions
- `explain_tuning_concept` - for advanced tuning details

────────────────────────────────────────────────
🧾 RESPONSE FORMAT
```json
{{
  "answer": "Complete, helpful response to the user's question",
  "tool_call": null
}}

⚠️ Provide complete answers. Only set tool_call if you genuinely need external data.
""")

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
    """
    Fully dynamic LLM-based info agent - answers general automotive questions
    """
    
    query = state.get("query", "")
    car_profile = state.get("car_profile", {})
    
    prompt = f"""
You are an expert automotive assistant. Answer the user's question with accurate, helpful, and enthusiastic information.

User Query: "{query}"
Car Profile: {json.dumps(car_profile, indent=2)}

Instructions:
- Provide comprehensive, conversational answers
- Be specific to their car if the profile is relevant
- Include practical advice and tips
- Be enthusiastic about cars and helpful
- If it's a greeting, be welcoming and explain what you can help with
- If they mention car details, acknowledge them warmly

Return JSON:
{{
    "answer": "your_comprehensive_answer",
    "car_specific": true_if_you_used_their_car_info,
    "response_type": "greeting|technical|general|recommendation",
    "confidence": "high|medium|low"
}}

Be thorough and helpful in your response.
"""

    try:
        response = await call_claude(prompt, temperature=0.3)
        
        # Parse response
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]
        
        result = json.loads(cleaned_response)
        
        # Store results in state
        state["info_answer"] = result.get("answer", "I'd be happy to help with automotive questions!")
        state["info_car_specific"] = result.get("car_specific", False)
        state["info_response_type"] = result.get("response_type", "general")
        state["info_confidence"] = result.get("confidence", "medium")
        
        return state
        
    except Exception as e:
        print(f"Error in info agent: {e}")
        # Fallback response
        state["info_answer"] = "I'm your automotive assistant! I can help with car information, modifications, diagnostics, and build planning. What would you like to know?"
        return state
