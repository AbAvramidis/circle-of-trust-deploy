import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.persona_generator import search_wikipedia, get_wikipedia_extract, generate_persona_markdown, save_persona_file
import os

@pytest.mark.asyncio
async def test_search_wikipedia_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Opensearch returns [query, [titles], [descriptions], [urls]]
    mock_response.json.return_value = ["query", ["Albert Einstein"], ["desc"], ["url"]]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await search_wikipedia("Albert Einstein")
        assert result == "Albert Einstein"
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_search_wikipedia_no_results():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = ["query", [], [], []]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await search_wikipedia("Unknown Person")
        assert result is None

@pytest.mark.asyncio
async def test_get_wikipedia_extract_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "query": {
            "pages": {
                "123": {
                    "extract": "Albert Einstein was a theoretical physicist."
                }
            }
        }
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await get_wikipedia_extract("Albert Einstein")
        assert result == "Albert Einstein was a theoretical physicist."

@pytest.mark.asyncio
async def test_generate_persona_markdown():
    with patch("backend.persona_generator.search_wikipedia", new_callable=AsyncMock) as mock_search, \
         patch("backend.persona_generator.get_wikipedia_extract", new_callable=AsyncMock) as mock_extract:
        
        mock_search.return_value = "Albert Einstein"
        mock_extract.return_value = "He developed the theory of relativity."
        
        name = "Albert Einstein"
        description = "Genius physicist"
        
        markdown = await generate_persona_markdown(name, description)
        
        assert f"# Persona: {name}" in markdown
        assert f"You are **{name}**." in markdown
        assert description in markdown
        assert "**Background & Context**" in markdown
        assert "He developed the theory of relativity." in markdown

def test_save_persona_file():
    with patch("builtins.open", new_callable=MagicMock) as mock_open, \
         patch("os.makedirs") as mock_makedirs:
        
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        save_persona_file("Test User", "Content")
        
        mock_makedirs.assert_called_with("prompts", exist_ok=True)
        mock_open.assert_called_with("prompts/test_user.md", "w", encoding="utf-8")
        mock_file.write.assert_called_with("Content")
