from typing import Dict, Any, List, Optional
import json
from datetime import datetime

def format_agent_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive response formatter that organizes all state data properly
    """
    
    # Extract basic information
    agent_trace = state.get("agent_trace", [])
    query = state.get("query", "")
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")
    
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
        "tool_trace": state.get("tool_trace", [])
    }
    
    # Add agent-specific data
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
    
    # Add car profile information
    response["car_profile"] = state.get("car_profile", {})
    
    # Add debug information if available
    if state.get("flags"):
        response["debug_flags"] = state.get("flags")
    
    return response

def determine_primary_agent(agent_trace: List[str]) -> str:
    """Determine the primary agent based on trace"""
    # Priority order: diagnostic > modcoach > buildplanner > info
    if any("diagnostic" in str(a).lower() for a in agent_trace):
        return "diagnostic"
    elif any("modcoach" in str(a).lower() for a in agent_trace):
        return "modcoach"
    elif any("buildplanner" in str(a).lower() for a in agent_trace):
        return "buildplanner"
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
    
    if mod_recommendations and len(mod_recommendations) > 0:
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
            "total_recommendations": len(mod_recommendations)
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
    
    if build_plan and len(build_plan) > 0:
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
            "total_stages": len(build_plan)
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
    
    else:
        return "I'm here to help with your automotive questions. Whether you need information about car maintenance, performance modifications, diagnostics, or build planning, I'm ready to assist!"

def format_mod_recommendations_text(mod_recommendations: List[Dict[str, Any]]) -> str:
    """Format mod recommendations into readable text"""
    if not mod_recommendations:
        return "No specific recommendations available at this time."
    
    text = "Based on your car and goals, here are my recommendations:\n\n"
    
    for i, mod in enumerate(mod_recommendations, 1):
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
    if not build_plan:
        return "No build plan available at this time."
    
    text = "Here's your comprehensive build plan:\n\n"
    
    for i, stage in enumerate(build_plan, 1):
        stage_name = stage.get("stage", f"Stage {i}")
        mods = stage.get("mods", [])
        timeline = stage.get("timeline", "TBD")
        
        text += f"**{stage_name}** (Timeline: {timeline})\n"
        
        for mod in mods:
            mod_name = mod.get("name", "Unknown mod")
            text += f"   • {mod_name}\n"
        
        text += "\n"
    
    return text 