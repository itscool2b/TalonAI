import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import async_only_middleware
from asgiref.sync import sync_to_async
from .models import CarProfile, Mod, Symptom, BuildGoal
from .state import AgentState
from .agent_loop import run_agent_system
from .memory import store_conversation_memory

@csrf_exempt
@async_only_middleware
async def chat_view(request):
    """
    Main chat endpoint for the AI agent system
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Validate required fields
    if "query" not in body:
        return JsonResponse({"error": "Missing 'query' field"}, status=400)
    if "user_id" not in body:
        return JsonResponse({"error": "Missing 'user_id' field"}, status=400)

    user_query = body["query"].strip()
    user_id = body["user_id"].strip()
    session_id = body.get("session_id", "default")

    # Validate input
    if not user_query:
        return JsonResponse({"error": "Query cannot be empty"}, status=400)
    if not user_id:
        return JsonResponse({"error": "User ID cannot be empty"}, status=400)

    @sync_to_async
    def get_car_profile(user_id: str) -> dict:
        """
        Retrieve car profile and all related data from database
        """
        try:
            profile, created = CarProfile.objects.get_or_create(
                user_id=user_id,
                defaults={
                    "make": "",
                    "model": "",
                    "year": 2020,
                    "resale_pref": ""
                }
            )
            
            return {
                "make": profile.make or "",
                "model": profile.model or "",
                "year": profile.year or 2020,
                "resale_pref": profile.resale_pref or "",
                "mods": [
                    {
                        "name": mod.name,
                        "brand": mod.brand,
                        "status": mod.status,
                        "install_date": mod.install_date.isoformat() if mod.install_date else None,
                        "notes": mod.notes,
                        "source_link": mod.source_link
                    } for mod in profile.mods.all()
                ],
                "symptoms": [
                    {
                        "description": s.description,
                        "severity": s.severity,
                        "resolved": s.resolved,
                        "resolution_notes": s.resolution_notes
                    } for s in profile.symptoms.filter(resolved=False)
                ],
                "goals": [
                    {
                        "goal_type": g.goal_type,
                        "priority": g.priority,
                        "notes": g.notes
                    } for g in profile.goals.all()
                ]
            }


    try:
        car_profile_dict = await get_car_profile(user_id)
    except Exception as e:
        return JsonResponse({"error": f"Failed to load car profile: {str(e)}"}, status=500)

    # Initialize agent state
    state: AgentState = {
        "query": user_query,
        "user_id": user_id,
        "session_id": session_id,
        "car_profile": car_profile_dict,
        "mod_recommendations": None,
        "symptom_summary": None,
        "build_plan": None,
        "final_message": None,
        "agent_trace": [],
        "flags": {},
        'info_answer': None,
        'tool_trace': []
    }

    try:
        # Run the agentic system (this will use memory automatically)
        result = await run_agent_system(state)
        
        # Store the conversation in memory
        await store_conversation_memory(
            user_id=user_id,
            session_id=session_id,
            query=user_query,
            agent_trace=result.get("agent_trace", []),
            final_output=result,
            car_profile=car_profile_dict
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        # Return error response if agent system fails
        return JsonResponse({
            "error": f"Agent system error: {str(e)}",
            "type": "error",
            "message": "Sorry, I encountered an error processing your request. Please try again."
        }, status=500)
