from typing import List, Dict, Optional, Union, Any
from typing_extensions import TypedDict
from openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from .claude import call_claude

prompt = PromptTemplate.from_template("""You are the `modcoach` agent in a modular AI system that assists car enthusiasts with planning performance upgrades. Your job is to recommend intelligent, goal-aligned modifications for the user's car.

────────────────────────────────────────────────
📦 INPUT: Car Profile
────────────────────────────────────────────────
{car_profile}

The car profile may include: make, model, year, current mods, goals (e.g. sound, power, handling), usage (e.g. daily, track), and budget.

────────────────────────────────────────────────
🧠 YOUR TASK
────────────────────────────────────────────────
1. Evaluate the profile and current mods.
2. Suggest a set of **next upgrade recommendations** based on typical modding paths.
3. For each mod, include:
   - `name`: Name of the upgrade (e.g. "Catback Exhaust")
   - `type`: Category (e.g. "exhaust", "suspension", "tuning")
   - `justification`: 1–2 sentence reason why this mod fits the profile

4. Set any **follow-up flags**. For example:
   - `"needs_diag": true` if symptoms seem unresolved
   - `"profile_missing": true` if profile lacks key fields

5. Suggest a **tool_call** for further detail. Choose the most relevant tool based on the user's car and your recommendations:
   - `lookup_mod_details` — Show specs, expected gains, fitment info
   - `compare_mod_options` — Compare brands or variants of similar mods
   - `estimate_mod_cost` — Provide estimated cost (parts + labor)
   - `suggest_install_order` — Recommend best install order for stacking upgrades
   - `check_compatibility` — Check mod fitment with user's car
   - `fetch_user_reviews` — Retrieve real user reviews for recommended mods

────────────────────────────────────────────────
🧾 RESPONSE FORMAT (MUST FOLLOW EXACTLY)
────────────────────────────────────────────────
Return only a JSON object like this:

```json
{
  "mod_recommendations": [
    {
      "name": "Cold Air Intake",
      "type": "intake",
      "justification": "Improves airflow and throttle response for turbocharged engines."
    },
    {
      "name": "Stage 1 Tune",
      "type": "tuning",
      "justification": "Unlocks extra horsepower with the current bolt-ons."
    }
  ],
  "additional_flags": {
    "needs_diag": false,
    "profile_missing": false
  },
  "tool_call": "compare_mod_options"
}

⚠️ DO NOT include any extra commentary or markdown. Only return a valid JSON object.
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
        parsed = json.loads(output)
        return {
            "mod_recommendations": parsed.get("mod_recommendations", []),
            "additional_flags": parsed.get("additional_flags", {}),
            "tool_call": parsed.get("tool_call", None)
        }
    except json.JSONDecodeError:
        return {
            "mod_recommendations": [],
            "additional_flags": {"parse_error": True},
            "tool_call": None
        }

def mcp_retrieval():
    pass

def mod_coach_pipeline():
    
    prompt_str = prompt.format(car_profile=json.dumps(state["car_profile"], indent=2))

    output = await call_claude(prompt_str)

    parsed = parse_modcoach_output(output)
    #updates

    state["mod_recommendations"] = parsed["mod_recommendations"]
    state["flags"].update(parsed["additional_flags"])
    state["tool_call"] = parsed["tool_call"]
    state["agent_trace"].append("modcoach")


    return state

