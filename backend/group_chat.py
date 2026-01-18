"""Group chat orchestration for conversing with selected council members."""

from typing import List, Dict, Any
from .ollama_client import query_ollama
from .config import ADVISORS
from .council import clean_response_content, generate_conversation_title


async def run_group_chat(user_query: str, member_ids: List[str], conversation_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run a group chat where selected members respond to the user's query.
    
    Args:
        user_query: The user's question
        member_ids: List of advisor IDs to include in the chat
        conversation_history: Previous messages for context (last N messages)
        
    Returns:
        List of dicts with 'advisor_id', 'advisor_name', 'model', and 'response' keys
    """
    # Filter advisors to only selected members
    selected_advisors = [a for a in ADVISORS if a["id"] in member_ids]
    
    if not selected_advisors:
        return []
    
    # Build context from conversation history
    context = build_conversation_context(conversation_history, max_messages=10)
    
    # Query each selected advisor
    responses = []
    for advisor in selected_advisors:
        # Build prompt with context
        full_prompt = build_prompt_with_context(user_query, context, advisor)
        
        # Query the advisor with proper message format
        messages = [{"role": "user", "content": full_prompt}]
        
        # Load system prompt from file
        system_prompt = None
        if advisor.get("prompt_file"):
            from .ollama_client import get_system_prompt
            system_prompt = await get_system_prompt(advisor["prompt_file"])
        
        # Query the advisor
        response = await query_ollama(
            model=advisor["model"],
            messages=messages,
            system_prompt=system_prompt
        )
        
        # Extract response text
        response_text = ""
        if response and isinstance(response, dict):
            response_text = response.get("content", "")
        
        # Clean response
        cleaned_response = clean_response_content(response_text)
        
        responses.append({
            "advisor_id": advisor["id"],
            "advisor_name": advisor["name"],
            "model": advisor["model"],
            "response": cleaned_response
        })
    
    return responses


def build_conversation_context(conversation_history: List[Dict[str, Any]], max_messages: int = 10) -> str:
    """
    Build a text representation of recent conversation history.
    
    Args:
        conversation_history: List of message dicts with 'role', 'content', and 'responses'
        max_messages: Maximum number of messages to include
        
    Returns:
        Formatted conversation history string
    """
    if not conversation_history:
        return ""
    
    # Take last N messages
    recent_messages = conversation_history[-max_messages:]
    
    context_parts = ["Previous conversation:"]
    
    for msg in recent_messages:
        if msg["role"] == "user":
            context_parts.append(f"\nUser: {msg['content']}")
        elif msg["role"] == "assistant" and msg.get("responses"):
            # Format all advisor responses
            for resp in msg["responses"]:
                context_parts.append(f"\n{resp['advisor_name']}: {resp['response']}")
    
    return "\n".join(context_parts)


def build_prompt_with_context(user_query: str, context: str, advisor: Dict[str, Any]) -> str:
    """
    Build a prompt that includes conversation context.
    
    Args:
        user_query: Current user question
        context: Formatted conversation history
        advisor: Advisor configuration
        
    Returns:
        Full prompt string
    """
    if context:
        return f"{context}\n\nUser: {user_query}\n\nPlease respond to the user's latest question, taking into account the conversation history."
    else:
        return user_query


async def generate_group_chat_title(first_message: str, member_names: List[str]) -> str:
    """
    Generate a title for a group chat session.
    
    Args:
        first_message: The first user message
        member_names: Names of the council members in the chat
        
    Returns:
        Generated title string
    """
    # Use the same title generation as regular conversations, but add member context
    members_str = ", ".join(member_names[:3])
    if len(member_names) > 3:
        members_str += f" +{len(member_names) - 3}"
    
    base_title = await generate_conversation_title(first_message)
    
    # Optionally prefix with members or just use the base title
    # For now, let's just use the base title since the UI will show members separately
    return base_title
