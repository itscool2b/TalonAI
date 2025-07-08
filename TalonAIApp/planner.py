from typing import List, Dict, Optional, Union, Any
from typing_extensions import TypedDict
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from .claude import call_claude
#


classifier = PromptTemplate.from_template("""
You are the central **Planner Agent** in a modular AI system for car enthusiasts. Your role is to evaluate the current system state and select the **single most appropriate sub-agent** to run next in order to best fulfill the user's request.

────────────────────────────────────────────────
🚗 SYSTEM OVERVIEW (Available Sub-Agents)
────────────────────────────────────────────────
• `modcoach`     — Recommends next performance upgrades based on car profile and goals  
• `diagnostic`   — Analyzes mechanical symptoms like noises, power loss, or misfires  
• `buildplanner` — Constructs a multi-step build plan for long-term performance goals  
• `profile`      — Updates or fills missing car profile fields (make, model, mods, etc.)  
• `info`         — Answers direct factual or informational queries  
• `end`          — Ends the session once the user’s request has been fully handled  

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
Choose the single best sub-agent to run next. Do NOT repeat previous agents unless necessary. Use `flags` and `agent_trace` to guide decisions.

Then determine if any flags need to be raised for follow-up action after this step.

Your response must follow this exact format:

```json
{
  "next_agent": "modcoach",
  "additional_flags": {
    "needs_diag": true,
    "profile_missing": false
  }
}

🛑 Do NOT include explanations, comments, or extra text. Only return valid JSON.

📌 Allowed agent tokens:

    modcoach

    diagnostic

    buildplanner

    profile

    info

    end
    """)

#

def parse_planner_output(response: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(response)
        next_agent = parsed.get("next_agent")
        flags = parsed.get("additional_flags", {})
        allowed = {"modcoach", "diagnostic", "buildplanner", "profile", "info", "end"}
        if next_agent not in allowed:
            raise ValueError("Invalid agent returned")
        return {"agent": next_agent, "flags": flags}
    except Exception as e:
        return {"agent": "end", "flags": {}, "error": str(e)}

async def run_planner(state: AgentState) -> AgentState:
    prompt = classifier.format(
        query=state["query"],
        car_profile=json.dumps(state["car_profile"], indent=2),
        agent_trace=json.dumps(state["agent_trace"], indent=2),
        flags=json.dumps(state["flags"], indent=2),
        build_plan=json.dumps(state["build_plan"], indent=2) if state["build_plan"] else "None",
        mod_recommendations=json.dumps(state["mod_recommendations"], indent=2) if state["mod_recommendations"] else "None",
        symptom_summary=state["symptom_summary"] or "None"
    )
    raw = await call_claude(prompt)
    parsed = parse_planner_output(raw)
    agent = parsed["agent"]
    flags = parsed["flags"]
    state["agent_trace"].append(f"Planner → {agent}")
    state["flags"].update(flags)
    if agent == "modcoach":
        pass  # TODO: await run_modcoach(state)
    elif agent == "diagnostic":
        pass  # TODO: await run_diagnostic(state)
    elif agent == "buildplanner":
        pass  # TODO: await run_buildplanner(state)
    elif agent == "profile":
        state["final_message"] = "Let's update your car profile."
    elif agent == "info":
        pass  # TODO: await run_info_agent(state)
    elif agent == "end":
        state["final_message"] = "Session complete. Happy driving."
    return state

#


#