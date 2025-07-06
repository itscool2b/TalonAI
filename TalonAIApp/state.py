from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict):
    query: str
    user_id: str
    car_profile: Dict[str, Any]                     # pulled from Supabase
    mod_recommendations: Optional[List[Dict]]       # set by ModCoach
    symptom_summary: Optional[str]                  # set by Diagnostic
    build_plan: Optional[List[Dict[str, Any]]]      # set by BuildPlanner: step-by-step plan
    plan_index: int                                  # which step we're on in the build plan
    plan_done: bool                                  # True when all steps finished
    final_message: Optional[str]                     # agent sets this to end chat
    agent_trace: List[str]                           # track agent activity (e.g. ModCoach ran)
    flags: Dict[str, bool]                           # inter-agent signals (e.g. {"needs_diag": True})
