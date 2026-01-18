import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.council import (
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    run_full_council,
    calculate_aggregate_rankings
)
from backend.ollama_client import get_system_prompt

@pytest.mark.asyncio
async def test_stage1_collect_responses():
    # Mock query_advisors_parallel
    with patch('backend.council.query_advisors_parallel', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = {
            "Advisor A": {"content": "Response A"},
            "Advisor B": {"content": "Response B"}
        }
        
        results = await stage1_collect_responses("test query")
        
        assert len(results) == 2
        assert results[0]['model'] == "Advisor A"
        assert results[0]['response'] == "Response A"
        assert results[1]['model'] == "Advisor B"
        assert results[1]['response'] == "Response B"

@pytest.mark.asyncio
async def test_stage2_collect_rankings():
    stage1_results = [
        {"model": "Advisor A", "response": "Response A content"},
        {"model": "Advisor B", "response": "Response B content"}
    ]
    
    # Mock query_advisors_parallel
    with patch('backend.council.query_advisors_parallel', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = {
            "Advisor A": {"content": "FINAL RANKING:\n1. Response B\n2. Response A"},
            "Advisor B": {"content": "FINAL RANKING:\n1. Response A\n2. Response B"}
        }
        
        results, label_map = await stage2_collect_rankings("test query", stage1_results)
        
        assert len(results) == 2
        assert "Response A" in label_map
        assert "Response B" in label_map
        assert label_map["Response A"] == "Advisor A"
        
        # Check parsed rankings
        assert results[0]['parsed_ranking'] == ["Response B", "Response A"]

@pytest.mark.asyncio
async def test_stage3_synthesize_final():
    stage1_results = [{"model": "A", "response": "Resp A"}]
    stage2_results = [{"model": "A", "ranking": "Rank A"}]
    
    # Mock query_ollama
    with patch('backend.council.query_ollama', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = {"content": "Final Answer"}
        
        result = await stage3_synthesize_final("query", stage1_results, stage2_results)
        
        assert result['response'] == "Final Answer"

def test_calculate_aggregate_rankings():
    stage2_results = [
        {
            "model": "A", 
            "ranking": "FINAL RANKING:\n1. Response A\n2. Response B", 
            "parsed_ranking": ["Response A", "Response B"]
        }, 
        {
            "model": "B", 
            "ranking": "FINAL RANKING:\n1. Response B\n2. Response A", 
            "parsed_ranking": ["Response B", "Response A"]
        }
    ]
    label_to_model = {
        "Response A": "Model A",
        "Response B": "Model B"
    }
    
    agg = calculate_aggregate_rankings(stage2_results, label_to_model)
    
    # Model A: positions [1, 2] -> avg 1.5
    # Model B: positions [2, 1] -> avg 1.5
    
    assert len(agg) == 2
    assert agg[0]['average_rank'] == 1.5

@pytest.mark.asyncio
async def test_get_system_prompt():
    # Create a temporary file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        tmp.write("# Test\n\n## System Prompt\n\n```markdown\nYou are a test.\n```\n\n## Other")
        tmp_path = tmp.name
        
    try:
        prompt = await get_system_prompt(tmp_path)
        assert prompt == "You are a test."
    finally:
        os.remove(tmp_path)

