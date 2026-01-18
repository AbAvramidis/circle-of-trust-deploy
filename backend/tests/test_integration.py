import pytest
import os
import json
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from fastapi.testclient import TestClient
from backend.main import app
from backend.persona_generator import generate_persona_markdown, save_persona_file
from backend.monitoring import get_ollama_status, record_request, get_stats, STATS
from backend.config import save_advisors, load_advisors, ADVISORS

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# --- Persona Generator Tests ---

@pytest.mark.asyncio
async def test_generate_persona_markdown():
    with patch('backend.persona_generator.search_wikipedia', new_callable=AsyncMock) as mock_search:
        with patch('backend.persona_generator.get_wikipedia_extract', new_callable=AsyncMock) as mock_get:
            mock_search.return_value = "Test Page"
            mock_get.return_value = "Test Content"
            
            content = await generate_persona_markdown("Test Name", "Test Description")
            
            assert "# Persona: Test Name" in content
            assert "Test Content" in content
            mock_search.assert_called_with("Test Name")
            mock_get.assert_called_with("Test Page")

def test_save_persona_file():
    with patch("builtins.open", mock_open()) as mock_file:
        with patch("os.makedirs") as mock_dirs:
            filename = save_persona_file("Test Name", "Content")
            
            assert filename == "prompts/test_name.md"
            mock_dirs.assert_called_with("prompts", exist_ok=True)
            mock_file.assert_called_with("prompts/test_name.md", "w", encoding="utf-8")
            mock_file().write.assert_called_with("Content")

# --- Monitoring Tests ---

@pytest.mark.asyncio
async def test_get_ollama_status_online():
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        # Mock version response
        mock_version = MagicMock()
        mock_version.status_code = 200
        mock_version.json.return_value = {"version": "0.1.0"}
        
        # Mock ps response
        mock_ps = MagicMock()
        mock_ps.status_code = 200
        mock_ps.json.return_value = {"models": [{"name": "llama3"}]}
        
        mock_get.side_effect = [mock_version, mock_ps]
        
        status = await get_ollama_status()
        
        assert status["service"] == "online"
        assert status["version"] == "0.1.0"
        assert len(status["running_models"]) == 1
        assert status["running_models"][0]["name"] == "llama3"

@pytest.mark.asyncio
async def test_get_ollama_status_offline():
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        import httpx
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        
        status = await get_ollama_status()
        
        assert status["service"] == "offline"

def test_monitoring_stats():
    # Reset stats
    STATS["requests_total"] = 0
    STATS["requests_failed"] = 0
    STATS["total_latency_ms"] = 0
    STATS["models_usage"] = {}
    
    record_request("model_a", 100, True)
    record_request("model_a", 200, True)
    record_request("model_b", 50, False)
    
    stats = get_stats()
    
    assert stats["global"]["total_requests"] == 3
    assert stats["global"]["failed_requests"] == 1
    assert stats["global"]["average_latency_ms"] == 150.0 # (100+200)/2
    
    assert stats["models"]["model_a"]["count"] == 2
    assert stats["models"]["model_a"]["average_latency_ms"] == 150.0
    
    assert stats["models"]["model_b"]["count"] == 1
    assert stats["models"]["model_b"]["errors"] == 1

# --- Config Tests ---

def test_save_and_load_advisors():
    test_advisors = [{"name": "Test", "model": "test-model"}]
    
    with patch("builtins.open", mock_open(read_data=json.dumps({"advisors": test_advisors}))) as mock_file:
        with patch("os.makedirs"):
            with patch("os.path.exists", return_value=True):
                # Test Save
                save_advisors(test_advisors)
                mock_file.assert_called_with("data/council_config.json", "w")
                
                # Test Load
                with patch("json.load", return_value={"advisors": test_advisors}):
                    load_advisors()
                    from backend.config import ADVISORS
                    assert ADVISORS == test_advisors

# --- API Integration Tests ---

def test_get_models_endpoint(client):
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "gpt-oss:latest"}, {"name": "llama3:latest"}]}
        mock_get.return_value = mock_resp
        
        response = client.get("/api/models")
        
        assert response.status_code == 200
        assert "gpt-oss:latest" in response.json()["models"]

def test_update_council_config_endpoint(client):
    # Mock generate_persona_markdown to avoid LLM call
    with patch('backend.main.generate_persona_markdown', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "# Persona"
        
        # Mock save_persona_file
        with patch('backend.main.save_persona_file') as mock_save:
            # Mock save_advisors
            with patch('backend.main.save_advisors') as mock_save_adv:
                
                payload = {
                    "advisors": [
                        {"name": "New Advisor", "description": "Desc", "model": "llama3"}
                    ]
                }
                
                response = client.post("/api/council/config", json=payload)
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert len(data["advisors"]) == 1
                assert data["advisors"][0]["name"] == "New Advisor"
                
                # Verify persona generation was called
                mock_gen.assert_called()
                mock_save.assert_called()

def test_update_council_config_missing_description(client):
    # Test that missing description doesn't cause 422
    with patch('backend.main.generate_persona_markdown', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "# Persona"
        with patch('backend.main.save_persona_file'):
            with patch('backend.main.save_advisors'):
                payload = {
                    "advisors": [
                        {"name": "New Advisor", "model": "llama3"} # No description
                    ]
                }
                response = client.post("/api/council/config", json=payload)
                assert response.status_code == 200
                data = response.json()
                assert data["advisors"][0]["description"] == ""

def test_monitoring_endpoint(client):
    with patch('backend.main.get_ollama_status', new_callable=AsyncMock) as mock_status:
        mock_status.return_value = {"service": "online"}
        
        response = client.get("/api/monitoring")
        
        assert response.status_code == 200
        assert response.json()["status"]["service"] == "online"
        assert "stats" in response.json()

def test_conversation_flow(client):
    # 1. Create Conversation
    response = client.post("/api/conversations", json={})
    assert response.status_code == 200
    conv_id = response.json()["id"]
    
    # 2. Send Message (Mocking the council process to avoid real LLM calls)
    with patch('backend.main.run_full_council', new_callable=AsyncMock) as mock_run:
        # Mock return values: stage1, stage2, stage3, metadata
        mock_run.return_value = (
            [{"model": "A", "response": "Resp A"}],
            [{"model": "A", "ranking": "Rank A"}],
            {"model": "Chairman", "response": "Final Answer"},
            {"label_to_model": {}, "aggregate_rankings": []}
        )
        
        # Mock title generation
        with patch('backend.main.generate_conversation_title', new_callable=AsyncMock) as mock_title:
            mock_title.return_value = "Test Title"
            
            payload = {"content": "Hello Council"}
            response = client.post(f"/api/conversations/{conv_id}/message", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["stage3"]["response"] == "Final Answer"
            
            # 3. Get Conversation
            response = client.get(f"/api/conversations/{conv_id}")
            assert response.status_code == 200
            conv = response.json()
            assert conv["title"] == "Test Title"
            assert len(conv["messages"]) == 2 # User + Assistant
