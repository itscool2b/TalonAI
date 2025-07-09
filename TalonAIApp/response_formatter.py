from typing import Dict, Any, List, Optional
import json
from datetime import datetime

def format_agent_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive response formatter that organizes all state data properly
    """
    try:
        # Extract basic information with safe defaults
        agent_trace = state.get("agent_trace", []) or []
        query = state.get("query", "") or ""
        user_id = state.get("user_id", "") or ""
        session_id = state.get("session_id", "") or ""
        
        # Determine primary response type based on agent trace
        primary_agent = determine_primary_agent(agent_trace)
        
        # Build comprehensive response
        response = {
            "type": primary_agent,
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_trace": agent_trace,
            "tool_trace": state.get("tool_trace", []) or []
        }
        
        # Add agent-specific data with error handling
        try:
            if primary_agent == "info":
                response.update(format_info_response(state))
            elif primary_agent == "modcoach":
                response.update(format_modcoach_response(state))
            elif primary_agent == "diagnostic":
                response.update(format_diagnostic_response(state))
            elif primary_agent == "buildplanner":
                response.update(format_buildplanner_response(state))
            else:
                response.update(format_default_response(state))
        except Exception as e:
            print(f"⚠️ Error formatting agent response: {e}")
            response.update(format_default_response(state))
        
        # Add car profile information
        response["car_profile"] = state.get("car_profile", {}) or {}
        
        # Add debug information if available
        if state.get("flags"):
            response["debug_flags"] = state.get("flags")
        
        return response
        
    except Exception as e:
        print(f"❌ Critical error in response formatter: {e}")
        # Return minimal safe response
        return {
            "type": "error",
            "query": state.get("query", ""),
            "user_id": state.get("user_id", ""),
            "session_id": state.get("session_id", ""),
            "timestamp": datetime.utcnow().isoformat(),
            "response": "I encountered an error processing your request. Please try again.",
            "message": "I encountered an error processing your request. Please try again.",
            "response_type": "error",
            "error": str(e)
        }

def determine_primary_agent(agent_trace: List[str]) -> str:
    """Determine the primary agent based on trace"""
    # Priority order: buildplanner > diagnostic > modcoach > info
    # BuildPlanner gets priority when it actually runs
    if any("buildplanner" in str(a).lower() for a in agent_trace):
        return "buildplanner"
    elif any("diagnostic" in str(a).lower() for a in agent_trace):
        return "diagnostic"
    elif any("modcoach" in str(a).lower() for a in agent_trace):
        return "modcoach"
    elif any("info" in str(a).lower() for a in agent_trace):
        return "info"
    else:
        return "info"  # Default fallback

def format_info_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """Format info agent response"""
    info_answer = state.get("info_answer", "")
    
    # Fallback if info_answer is empty
    if not info_answer or info_answer.strip() == "":
        info_answer = generate_fallback_info_response(state)
    
    return {
        "response": info_answer,
        "message": info_answer,
        "response_type": "informational",
        "data": {
            "answer": info_answer,
            "knowledge_base": "automotive_general"
        }
    }

def format_modcoach_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """Format modcoach agent response"""
    mod_recommendations = state.get("mod_recommendations", [])
    
    # Handle None case
    if mod_recommendations is None:
        mod_recommendations = []
    
    if mod_recommendations and len(mod_recommendations or []) > 0:
        message = "Here are my mod recommendations for your car:"
        response_text = format_mod_recommendations_text(mod_recommendations)
    else:
        message = "I'd be happy to recommend some mods! Tell me about your car and what you want to achieve."
        response_text = message
    
    return {
        "response": response_text,
        "message": message,
        "response_type": "modification_recommendations",
        "data": {
            "mod_recommendations": mod_recommendations,
            "total_recommendations": len(mod_recommendations or []) if mod_recommendations else 0
        }
    }

def format_diagnostic_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """Format diagnostic agent response"""
    symptom_summary = state.get("symptom_summary", "")
    followup_recommendations = state.get("followup_recommendations", [])
    
    if symptom_summary and symptom_summary.strip():
        message = "Here's my diagnosis of your car's issue:"
        response_text = symptom_summary
    else:
        message = "I'd be happy to help diagnose any car issues. Could you describe what symptoms you're experiencing?"
        response_text = message
    
    return {
        "response": response_text,
        "message": message,
        "response_type": "diagnostic_analysis",
        "data": {
            "symptom_summary": symptom_summary,
            "followup_recommendations": followup_recommendations,
            "diagnosis_confidence": "medium"  # Could be enhanced with actual confidence scoring
        }
    }

def format_buildplanner_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """Format buildplanner agent response"""
    build_plan = state.get("build_plan", [])
    
    # Handle None case
    if build_plan is None:
        build_plan = []
    
    # Ensure build_plan is always a list
    if not isinstance(build_plan, list):
        build_plan = []
    
    if build_plan and len(build_plan or []) > 0:
        message = "Here's your personalized build plan for your car!"
        response_text = format_build_plan_text(build_plan)
    else:
        message = "I'd be happy to help you create a build plan! Tell me about your car and what you want to achieve."
        response_text = message
    
    return {
        "response": response_text,
        "message": message,
        "response_type": "build_planning",
        "data": {
            "build_plan": build_plan,
            "total_stages": len(build_plan or []) if build_plan else 0
        }
    }

def format_default_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """Format default response when no specific agent data is available"""
    return {
        "response": "I'm your automotive assistant. How can I help you with your car today?",
        "message": "I'm your automotive assistant. How can I help you with your car today?",
        "response_type": "general_greeting",
        "data": {
            "status": "ready",
            "capabilities": ["info", "modcoach", "diagnostic", "buildplanner"]
        }
    }

def generate_fallback_info_response(state: Dict[str, Any]) -> str:
    """Generate fallback response when info agent returns empty"""
    query = state.get("query", "").lower()
    
    if any(greeting in query for greeting in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return "Hello! I'm your automotive assistant. I'm here to help you with any car-related questions, modifications, diagnostics, or build planning. What would you like to know about your vehicle?"
    
    elif "name" in query and "car" in query:
        return "I don't currently have your personal information stored. Could you tell me your name and what car you drive? This will help me provide more personalized assistance."
    
    elif "build plan" in query or "build" in query:
        return "I'd be happy to help you create a comprehensive build plan! Tell me about your car, your goals, and your budget, and I'll create a staged modification plan for you."
    
    elif "mod" in query or "modification" in query or "upgrade" in query:
        return "I can help you with performance modifications! Tell me about your car and what you want to achieve, and I'll recommend specific upgrades that would work well for your setup."
    
    elif "problem" in query or "issue" in query or "noise" in query or "symptom" in query:
        return "I can help diagnose car issues! Please describe the symptoms you're experiencing - things like noises, performance problems, warning lights, or any unusual behavior."
    
    else:
        return "I'm here to help with your automotive questions. Whether you need information about car maintenance, performance modifications, diagnostics, or build planning, I'm ready to assist!"

def format_mod_recommendations_text(mod_recommendations: List[Dict[str, Any]]) -> str:
    """Format mod recommendations into readable text"""
    if not mod_recommendations or mod_recommendations is None:
        return "No specific recommendations available at this time."
    
    text = "Based on your car and goals, here are my recommendations:\n\n"
    
    for i, mod in enumerate(mod_recommendations, 1):
        if mod is None:
            continue
        name = mod.get("name", "Unknown Modification")
        mod_type = mod.get("type", "general")
        justification = mod.get("justification", "No details available")
        confidence = mod.get("confidence", "medium")
        
        text += f"{i}. **{name}** ({mod_type})\n"
        text += f"   • {justification}\n"
        text += f"   • Confidence: {confidence}\n\n"
    
    return text

def format_build_plan_text(build_plan: List[Dict[str, Any]]) -> str:
    """Format build plan into readable text"""
    if not build_plan or build_plan is None:
        return "No build plan available at this time."
    
    text = "Here's your comprehensive build plan:\n\n"
    
    for i, stage in enumerate(build_plan, 1):
        if stage is None:
            continue
        stage_name = stage.get("stage", f"Stage {i}")
        mods = stage.get("mods", [])
        timeline = stage.get("timeline", "TBD")
        
        text += f"**{stage_name}** (Timeline: {timeline})\n"
        
        if mods:
            for mod in mods:
                if mod is None:
                    continue
                mod_name = mod.get("name", "Unknown mod") if isinstance(mod, dict) else str(mod)
                text += f"   • {mod_name}\n"
        
        text += "\n"
    
    return text 