import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from backend.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_update_council_config_generates_personas():
    payload = {
        "advisors": [
            {
                "name": "Marie Curie",
                "description": "Pioneer in radioactivity",
                "model": "gemma:latest"
            }
        ]
    }

    with patch("backend.main.generate_persona_markdown", new_callable=AsyncMock) as mock_generate, \
         patch("backend.main.save_persona_file") as mock_save, \
         patch("backend.main.save_advisors") as mock_save_advisors:
        
        mock_generate.return_value = "# Persona: Marie Curie..."
        
        response = client.post("/api/council/config", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["advisors"]) == 1
        assert data["advisors"][0]["name"] == "Marie Curie"
        
        # Verify persona generation was called
        mock_generate.assert_called_once()
        args, _ = mock_generate.call_args
        assert args[0] == "Marie Curie"
        
        # Verify file saving was called
        mock_save.assert_called_once()
        
        # Verify config saving was called
        mock_save_advisors.assert_called_once()
