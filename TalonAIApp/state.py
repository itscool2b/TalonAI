from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict):
    query: str
    user_id: str
    car_profile: Dict[str, Any]
    mod_recommendations: Optional[List[Dict]]
    symptom_summary: Optional[str]
    build_plan: Optional[List[Dict[str, Any]]]
    final_message: Optional[str]
    agent_trace: List[str]
    flags: Dict[str, bool]
    info_answer: Optional[str]
    tool_trace: List[Dict[str, Any]]
