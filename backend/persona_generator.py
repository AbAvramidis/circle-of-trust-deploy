import httpx
import urllib.parse
import os
import re
from typing import Optional

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "LLM-Council-App/1.0 (Educational Purpose)"
}

async def search_wikipedia(query: str) -> Optional[str]:
    """
    Search Wikipedia for a page title matching the query.
    Returns the best matching title or None.
    """
    params = {
        "action": "opensearch",
        "search": query,
        "limit": 1,
        "namespace": 0,
        "format": "json"
    }
    
    async with httpx.AsyncClient(headers=HEADERS) as client:
        try:
            response = await client.get(WIKIPEDIA_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            # Opensearch returns [query, [titles], [descriptions], [urls]]
            if data and len(data) > 1 and data[1]:
                return data[1][0]
        except Exception as e:
            print(f"Error searching Wikipedia for {query}: {e}")
    
    return None

async def get_wikipedia_extract(title: str) -> str:
    """
    Get the text extract (intro) for a Wikipedia page.
    """
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "titles": title,
        "format": "json"
    }
    
    async with httpx.AsyncClient(headers=HEADERS) as client:
        try:
            response = await client.get(WIKIPEDIA_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id != "-1":
                    return page_data.get("extract", "")
        except Exception as e:
            print(f"Error fetching Wikipedia content for {title}: {e}")
            
    return ""

async def generate_persona_markdown(name: str, description: str) -> str:
    """
    Generate the system prompt content for a persona by scraping Wikipedia.
    """
    print(f"Generating persona for: {name}")
    
    # 1. Search for the page
    title = await search_wikipedia(name)
    
    wiki_content = ""
    if title:
        print(f"Found Wikipedia page: {title}")
        # 2. Get the content
        wiki_content = await get_wikipedia_extract(title)
    else:
        print(f"No Wikipedia page found for {name}")
        
    # 3. Construct the markdown
    markdown = f"""# Persona: {name}

## System Prompt
You are **{name}**.
{description}

"""

    if wiki_content:
        markdown += f"""**Background & Context**
{wiki_content}

"""

    markdown += """**Instructions**
1. **Adopt the Persona**: Speak, think, and reason exactly as this character would. Use their vocabulary, tone, and mannerisms.
2. **Stay in Character**: Never break character. Do not mention you are an AI.
3. **Perspective**: Answer questions based on your specific background, historical context, and expertise.
4. **Format**: Provide clear, thoughtful responses.
"""

    return markdown


def save_persona_file(name: str, content: str):
    """
    Save the persona content to a markdown file in the prompts directory.
    """
    # Sanitize name for filename
    safe_name = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_'))
    filename = f"prompts/{safe_name}.md"
    
    # Ensure prompts directory exists
    os.makedirs("prompts", exist_ok=True)
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved persona to {filename}")
        return filename
    except Exception as e:
        print(f"Error saving persona file {filename}: {e}")
        return None

