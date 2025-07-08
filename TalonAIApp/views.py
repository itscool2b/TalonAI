import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import async_only_middleware
from asgiref.sync import sync_to_async
from .models import CarProfile, Mod, Symptom, BuildGoal
from .state import AgentState
from .planner import run_planner

@csrf_exempt
@async_only_middleware
async def chat_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    body = await request.json()
    user_query = body["query"]
    user_id = body["user_id"]

    @sync_to_async
    def get_car_profile_deep(user_id: str) -> dict:
        profile, _ = CarProfile.objects.get_or_create(user_id=user_id)

        return {
            "make": profile.make,
            "model": profile.model,
            "year": profile.year,
            "resale_pref": profile.resale_pref,
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

    car_profile_dict = await get_car_profile_deep(user_id)

    state: AgentState = {
        "query": user_query,
        "user_id": user_id,
        "car_profile": car_profile_dict,
        "mod_recommendations": None,
        "symptom_summary": None,
        "build_plan": None,
        "final_message": None,
        "agent_trace": [],
        "flags": {}
    }

    updated_state = await run_planner(state)
    return JsonResponse(updated_state)
