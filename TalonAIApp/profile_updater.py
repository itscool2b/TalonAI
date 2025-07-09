import json
from .claude import call_claude
from .models import CarProfile
from asgiref.sync import sync_to_async

async def profile_updater_pipeline(state):
    """
    Dynamic LLM-based profile updater agent
    """
    
    query = state.get("query", "")
    user_id = state.get("user_id", "")
    
    # Get current profile
    try:
        current_profile = await get_current_profile(user_id)
    except Exception as e:
        current_profile = {}
    
    prompt = f"""
You are a car profile extraction and update specialist. Analyze the user's query and determine if it contains car information that should be stored.

Current Profile: {json.dumps(current_profile, indent=2)}
User Query: "{query}"

Extract any car information from the query including:
- Make (manufacturer) 
- Model
- Year
- Performance preferences
- Goals
- Name (if mentioned)

Determine if the profile should be updated and provide a summary.

Return JSON:
{{
    "should_update": true_or_false,
    "updates": {{
        "make": "extracted_make_or_null",
        "model": "extracted_model_or_null", 
        "year": extracted_year_or_null,
        "resale_pref": "extracted_preference_or_null"
    }},
    "extracted_info": {{
        "name": "extracted_name_or_null",
        "interests": ["performance", "goals"],
        "summary": "what_was_learned_about_user"
    }},
    "response": "conversational_response_to_user_about_profile_update"
}}

Only include fields you actually found. Be conversational in your response.
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
        
        # Update database if needed
        if result.get("should_update") and result.get("updates"):
            await update_profile_in_db(user_id, result["updates"])
            
        # Store results in state
        state["profile_updated"] = result.get("should_update", False)
        state["extracted_info"] = result.get("extracted_info", {})
        state["profile_response"] = result.get("response", "Profile information noted.")
        
        return state
        
    except Exception as e:
        print(f"Error in profile updater: {e}")
        state["profile_response"] = "I'll keep that information in mind for future recommendations."
        return state

@sync_to_async
def get_current_profile(user_id: str):
    """Get current car profile from database"""
    try:
        profile = CarProfile.objects.get(user_id=user_id)
        return {
            "make": profile.make,
            "model": profile.model,
            "year": profile.year,
            "resale_pref": profile.resale_pref
        }
    except CarProfile.DoesNotExist:
        return {}

@sync_to_async  
def update_profile_in_db(user_id: str, updates):
    """Update car profile in database"""
    try:
        profile, created = CarProfile.objects.get_or_create(
            user_id=user_id,
            defaults={"make": "", "model": "", "year": 2020, "resale_pref": ""}
        )
        
        for key, value in updates.items():
            if value is not None and hasattr(profile, key):
                if key == 'year':
                    profile.year = int(value)
                else:
                    setattr(profile, key, str(value))
        
        profile.save()
        return True
        
    except Exception as e:
        print(f"Error updating profile: {e}")
        return False

# Keep the old function for backward compatibility but make it call the pipeline
async def update_car_profile_from_query(user_id: str, query: str):
    """Legacy function - now calls the agent pipeline"""
    state = {"user_id": user_id, "query": query}
    result_state = await profile_updater_pipeline(state)
    return result_state.get("profile_updated", False) 