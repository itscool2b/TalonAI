import json
import re
from typing import Dict, Any, List, Optional
from asgiref.sync import sync_to_async
from .models import CarProfile, Mod, Symptom, BuildGoal
from .claude import call_claude

class ToolRegistry:
    """Registry for all available tools"""
    
    def __init__(self):
        self.tools = {}
        self.register_default_tools()
    
    def register_tool(self, name: str, func, description: str, parameters: Dict[str, Any]):
        """Register a tool with the registry"""
        self.tools[name] = {
            'function': func,
            'description': description,
            'parameters': parameters
        }
    
    def get_tool(self, name: str):
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        return [
            {
                'name': name,
                'description': tool['description'],
                'parameters': tool['parameters']
            }
            for name, tool in self.tools.items()
        ]
    
    def register_default_tools(self):
        """Register all default tools"""
        self.register_tool(
            'update_car_profile',
            update_car_profile_tool,
            'Extract and update car profile information from user query',
            {
                'user_id': 'string - User ID',
                'query': 'string - User query to extract car info from',
                'current_profile': 'object - Current car profile data'
            }
        )
        
        self.register_tool(
            'get_car_specs',
            get_car_specs_tool,
            'Get technical specifications for a specific car',
            {
                'make': 'string - Car manufacturer',
                'model': 'string - Car model',
                'year': 'integer - Car year'
            }
        )
        
        self.register_tool(
            'generate_mod_recommendations',
            generate_mod_recommendations_tool,
            'Generate performance modification recommendations',
            {
                'car_profile': 'object - Car profile data',
                'goals': 'string - Performance goals',
                'budget': 'string - Budget constraints'
            }
        )
        
        self.register_tool(
            'diagnose_symptoms',
            diagnose_symptoms_tool,
            'Diagnose car problems based on symptoms',
            {
                'symptoms': 'string - Described symptoms',
                'car_profile': 'object - Car profile data'
            }
        )
        
        self.register_tool(
            'create_build_plan',
            create_build_plan_tool,
            'Create a staged build plan for modifications',
            {
                'modifications': 'array - List of desired modifications',
                'timeline': 'string - Desired timeline',
                'car_profile': 'object - Car profile data'
            }
        )

# Tool registry instance
tool_registry = ToolRegistry()

async def update_car_profile_tool(user_id: str, query: str, current_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Tool to extract and update car profile from user query"""
    
    prompt = f"""
    You are a car profile extraction specialist. Extract car information from the user's query and update the profile.
    
    Current Profile: {json.dumps(current_profile, indent=2)}
    
    User Query: "{query}"
    
    Extract any car information from the query including:
    - Make (manufacturer)
    - Model
    - Year
    - Performance interests
    - Modification goals
    - Budget constraints
    
    Return a JSON object with only the NEW information to update:
    {{
        "updates": {{
            "make": "extracted_make_or_null",
            "model": "extracted_model_or_null", 
            "year": extracted_year_or_null,
            "resale_pref": "extracted_preference_or_null"
        }},
        "extracted_info": {{
            "name": "extracted_name_or_null",
            "interests": ["list", "of", "interests"],
            "goals": "extracted_goals"
        }}
    }}
    
    Only include fields that you actually found in the query. Return null for fields not found.
    """
    
    try:
        response = await call_claude(prompt, temperature=0.1)
        
        # Parse JSON response
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]
        
        result = json.loads(cleaned_response)
        
        # Update database if we have updates
        if result.get('updates'):
            await update_profile_in_db(user_id, result['updates'])
        
        return result
        
    except Exception as e:
        print(f"Error in update_car_profile_tool: {e}")
        return {"updates": {}, "extracted_info": {}}

async def get_car_specs_tool(make: str, model: str, year: int) -> Dict[str, Any]:
    """Tool to get car specifications"""
    
    prompt = f"""
    You are an automotive specifications expert. Provide detailed technical specifications for:
    
    Car: {year} {make} {model}
    
    Return comprehensive specifications in JSON format:
    {{
        "engine": {{
            "type": "engine_type",
            "displacement": "displacement",
            "horsepower": "hp_number",
            "torque": "torque_number",
            "fuel_type": "fuel_type"
        }},
        "performance": {{
            "acceleration": "0-60_time",
            "top_speed": "top_speed",
            "transmission": "transmission_type"
        }},
        "modification_potential": {{
            "tune_gains": "estimated_gains",
            "common_mods": ["list", "of", "common", "mods"],
            "platform_notes": "platform_specific_info"
        }},
        "known_issues": ["list", "of", "known", "issues"]
    }}
    
    Be specific and accurate. If you don't know exact specs, provide reasonable estimates based on the platform.
    """
    
    try:
        response = await call_claude(prompt, temperature=0.1)
        
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]
        
        return json.loads(cleaned_response)
        
    except Exception as e:
        print(f"Error in get_car_specs_tool: {e}")
        return {"error": str(e)}

async def generate_mod_recommendations_tool(car_profile: Dict[str, Any], goals: str, budget: str = None) -> Dict[str, Any]:
    """Tool to generate modification recommendations"""
    
    prompt = f"""
    You are a performance modification expert. Generate specific modification recommendations.
    
    Car Profile: {json.dumps(car_profile, indent=2)}
    
    Goals: {goals}
    Budget: {budget or "Not specified"}
    
    Generate targeted modification recommendations in JSON format:
    {{
        "recommendations": [
            {{
                "name": "modification_name",
                "type": "category",
                "priority": "high/medium/low",
                "estimated_cost": "cost_range",
                "power_gain": "estimated_hp_gain",
                "justification": "why_this_mod",
                "installation_difficulty": "easy/medium/hard",
                "supporting_mods": ["required", "supporting", "mods"]
            }}
        ],
        "installation_order": ["mod1", "mod2", "mod3"],
        "total_estimated_cost": "total_cost_range",
        "expected_results": "overall_performance_improvement",
        "warnings": ["important", "considerations"]
    }}
    
    Be specific to the car platform and realistic about gains and costs.
    """
    
    try:
        response = await call_claude(prompt, temperature=0.2)
        
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]
        
        return json.loads(cleaned_response)
        
    except Exception as e:
        print(f"Error in generate_mod_recommendations_tool: {e}")
        return {"error": str(e)}

async def diagnose_symptoms_tool(symptoms: str, car_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Tool to diagnose car problems"""
    
    prompt = f"""
    You are an automotive diagnostic expert. Diagnose the reported symptoms.
    
    Car Profile: {json.dumps(car_profile, indent=2)}
    
    Reported Symptoms: {symptoms}
    
    Provide a comprehensive diagnosis in JSON format:
    {{
        "diagnosis": {{
            "most_likely_cause": "primary_diagnosis",
            "confidence": "high/medium/low",
            "explanation": "detailed_explanation"
        }},
        "possible_causes": [
            {{
                "cause": "possible_cause",
                "probability": "percentage",
                "symptoms_match": "how_well_symptoms_match"
            }}
        ],
        "diagnostic_steps": [
            {{
                "step": "diagnostic_step",
                "tools_needed": ["required", "tools"],
                "difficulty": "easy/medium/hard"
            }}
        ],
        "immediate_actions": ["urgent", "actions", "to", "take"],
        "estimated_repair_cost": "cost_range",
        "safety_concerns": ["safety", "issues"]
    }}
    
    Be thorough and consider the specific car platform.
    """
    
    try:
        response = await call_claude(prompt, temperature=0.1)
        
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]
        
        return json.loads(cleaned_response)
        
    except Exception as e:
        print(f"Error in diagnose_symptoms_tool: {e}")
        return {"error": str(e)}

async def create_build_plan_tool(modifications: List[str], timeline: str, car_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Tool to create a staged build plan"""
    
    prompt = f"""
    You are a build planning expert. Create a staged modification plan.
    
    Car Profile: {json.dumps(car_profile, indent=2)}
    
    Desired Modifications: {json.dumps(modifications)}
    Timeline: {timeline}
    
    Create a comprehensive build plan in JSON format:
    {{
        "build_plan": [
            {{
                "stage": 1,
                "name": "stage_name",
                "timeframe": "timeframe",
                "modifications": [
                    {{
                        "name": "mod_name",
                        "cost": "cost_range",
                        "install_time": "time_estimate",
                        "prerequisites": ["required", "mods"]
                    }}
                ],
                "total_stage_cost": "stage_cost",
                "expected_results": "stage_results"
            }}
        ],
        "total_timeline": "total_time",
        "total_cost": "total_cost_range",
        "final_expected_power": "final_hp_estimate",
        "considerations": ["important", "notes"],
        "alternative_paths": ["alternative", "approaches"]
    }}
    
    Order stages logically with supporting mods first, then power mods.
    """
    
    try:
        response = await call_claude(prompt, temperature=0.2)
        
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:-3]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:-3]
        
        return json.loads(cleaned_response)
        
    except Exception as e:
        print(f"Error in create_build_plan_tool: {e}")
        return {"error": str(e)}

@sync_to_async
def update_profile_in_db(user_id: str, updates: Dict[str, Any]) -> bool:
    """Update car profile in database"""
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
        
        updated = False
        
        for key, value in updates.items():
            if value is not None and hasattr(profile, key):
                if key == 'year':
                    profile.year = int(value)
                else:
                    setattr(profile, key, str(value))
                updated = True
        
        if updated:
            profile.save()
        
        return updated
        
    except Exception as e:
        print(f"Error updating profile in DB: {e}")
        return False

async def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Execute a tool by name with given parameters"""
    tool = tool_registry.get_tool(tool_name)
    
    if not tool:
        return {"error": f"Tool '{tool_name}' not found"}
    
    try:
        result = await tool['function'](**kwargs)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)} 