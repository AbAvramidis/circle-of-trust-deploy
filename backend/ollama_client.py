"""Ollama API client for making LLM requests."""

import httpx
import os
import re
import time
from typing import List, Dict, Any, Optional
from . import config
from .config import OLLAMA_API_URL
from .monitoring import record_request

async def get_system_prompt(prompt_file: str) -> str:
    """
    Read and parse the system prompt from a markdown file.
    Extracts content from the 'System Prompt' section.
    """
    try:
        # Handle relative paths from project root
        if not os.path.isabs(prompt_file):
            # Assuming backend is one level deep, but let's try to find the file relative to CWD
            # or relative to the file location.
            # The config has "prompts/..." which is relative to project root.
            # We are running from project root usually.
            if not os.path.exists(prompt_file):
                # Try looking up one level if we are in backend/
                if os.path.exists(os.path.join("..", prompt_file)):
                    prompt_file = os.path.join("..", prompt_file)
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regex to find the System Prompt section
        # Looking for ## System Prompt followed by content, until the next ## header
        match = re.search(r'## System Prompt\s*\n+(?:```markdown\n)?(.*?)(?:```\n)?\s*(?:##|$)', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return ""
    except Exception as e:
        print(f"Error reading prompt file {prompt_file}: {e}")
        return ""

async def query_ollama(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 300.0,
    system_prompt: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via Ollama API.

    Args:
        model: Ollama model identifier
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds
        system_prompt: Optional system prompt to prepend/insert

    Returns:
        Response dict with 'content', or None if failed
    """
    # If system prompt is provided, insert it as the first message
    final_messages = messages.copy()
    if system_prompt:
        # Check if there is already a system message
        if final_messages and final_messages[0]['role'] == 'system':
            final_messages[0]['content'] = system_prompt
        else:
            final_messages.insert(0, {"role": "system", "content": system_prompt})

    payload = {
        "model": model,
        "messages": final_messages,
        "stream": False
    }

    start_time = time.time()
    success = False
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OLLAMA_API_URL,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['message']
            
            success = True
            return {
                'content': message.get('content'),
                # Ollama doesn't typically return reasoning_details in the same way, 
                # but we can pass through other fields if needed.
            }

    except Exception as e:
        print(f"Error querying ollama model {model}: {e}")
        return None
    finally:
        elapsed_ms = (time.time() - start_time) * 1000
        record_request(model, elapsed_ms, success)

async def query_advisors_parallel(
    user_query: str
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query all advisors in parallel with their specific personas.

    Args:
        user_query: The user's question

    Returns:
        Dict mapping advisor name (or model) to response dict
    """
    import asyncio

    async def query_advisor(advisor):
        system_prompt = await get_system_prompt(advisor["prompt_file"])
        messages = [{"role": "user", "content": user_query}]
        
        response = await query_ollama(
            model=advisor["model"],
            messages=messages,
            system_prompt=system_prompt
        )
        return advisor["name"], response

    # Create tasks for all advisors
    tasks = [query_advisor(advisor) for advisor in config.ADVISORS]

    # Wait for all to complete
    results = await asyncio.gather(*tasks)

    # Map advisor names to their responses
    return {name: response for name, response in results}
