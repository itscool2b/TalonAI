import json
from typing import List, Dict, Any
from django.db import models
from django.utils import timezone
from datetime import timedelta
from .models import ConversationMemory

async def store_conversation_memory(
    user_id: str,
    session_id: str,
    query: str,
    agent_trace: List[str],
    final_output: Dict[str, Any],
    car_profile: Dict[str, Any]
) -> None:
    """
    Store a conversation interaction in memory
    """
    await ConversationMemory.objects.acreate(
        user_id=user_id,
        session_id=session_id,
        query=query,
        agent_trace=agent_trace,
        final_output=final_output,
        car_profile_snapshot=car_profile
    )
    
    # Clean up old memories after storing new one
    await cleanup_old_memories(user_id)

async def cleanup_old_memories(user_id: str, max_memories: int = 10, days_to_keep: int = 7) -> None:
    """
    Clean up old memories to prevent database bloat
    - Keep only max_memories per user
    - Delete memories older than days_to_keep
    """
    # Delete memories older than days_to_keep
    cutoff_date = timezone.now() - timedelta(days=days_to_keep)
    await ConversationMemory.objects.filter(
        user_id=user_id,
        created_at__lt=cutoff_date
    ).adelete()
    
    # If still too many memories, delete oldest ones
    memory_count = await ConversationMemory.objects.filter(user_id=user_id).acount()
    if memory_count > max_memories:
        # Get IDs of oldest memories to delete
        old_memories = await ConversationMemory.objects.filter(
            user_id=user_id
        ).order_by('created_at')[:memory_count - max_memories].values_list('id', flat=True)
        
        await ConversationMemory.objects.filter(id__in=old_memories).adelete()

async def get_recent_memory(
    user_id: str, 
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Get recent conversation history for a user
    """
    memories = await ConversationMemory.objects.filter(
        user_id=user_id
    ).order_by('-created_at')[:limit].values()
    
    return [
        {
            "query": memory["query"],
            "agent_trace": memory["agent_trace"],
            "final_output": memory["final_output"],
            "car_profile_snapshot": memory["car_profile_snapshot"],
            "created_at": memory["created_at"].isoformat()
        }
        for memory in memories
    ]

async def get_session_memory(
    user_id: str,
    session_id: str
) -> List[Dict[str, Any]]:
    """
    Get all conversations from a specific session
    """
    memories = await ConversationMemory.objects.filter(
        user_id=user_id,
        session_id=session_id
    ).order_by('created_at').values()
    
    return [
        {
            "query": memory["query"],
            "agent_trace": memory["agent_trace"],
            "final_output": memory["final_output"],
            "car_profile_snapshot": memory["car_profile_snapshot"],
            "created_at": memory["created_at"].isoformat()
        }
        for memory in memories
    ]

def format_memory_for_prompt(memories: List[Dict[str, Any]]) -> str:
    """
    Format memory for inclusion in planner prompt
    """
    if not memories:
        return "No previous conversations found."
    
    formatted = "📚 RECENT CONVERSATION HISTORY:\n"
    for i, memory in enumerate(memories, 1):
        formatted += f"\n{i}. Query: {memory['query']}\n"
        formatted += f"   Agents: {', '.join(memory['agent_trace'])}\n"
        formatted += f"   Output: {memory['final_output'].get('type', 'unknown')}\n"
        formatted += f"   Date: {memory['created_at'][:10]}\n"
    
    return formatted 