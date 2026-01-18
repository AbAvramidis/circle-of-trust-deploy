"""Unit tests for group chat functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.group_chat import (
    run_group_chat,
    build_conversation_context,
    build_prompt_with_context,
    generate_group_chat_title
)


@pytest.mark.asyncio
async def test_run_group_chat():
    """Test running a group chat with selected members."""
    with patch('backend.group_chat.ADVISORS', [
        {"id": "advisor_a", "name": "Advisor A", "model": "model-a", "prompt_file": "prompts/a.md"},
        {"id": "advisor_b", "name": "Advisor B", "model": "model-b", "prompt_file": "prompts/b.md"},
        {"id": "advisor_c", "name": "Advisor C", "model": "model-c", "prompt_file": "prompts/c.md"},
    ]):
        with patch('backend.group_chat.query_ollama', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {"content": "Test response"}
            
            with patch('backend.ollama_client.get_system_prompt', new_callable=AsyncMock) as mock_system:
                mock_system.return_value = "System prompt"
                
                member_ids = ["advisor_a", "advisor_b"]
                conversation_history = []
                
                results = await run_group_chat("Hello", member_ids, conversation_history)
                
                assert len(results) == 2
                assert results[0]["advisor_id"] == "advisor_a"
                assert results[0]["advisor_name"] == "Advisor A"
                assert results[0]["response"] == "Test response"
                assert results[1]["advisor_id"] == "advisor_b"
                assert results[1]["advisor_name"] == "Advisor B"


@pytest.mark.asyncio
async def test_run_group_chat_with_context():
    """Test group chat with conversation history."""
    with patch('backend.group_chat.ADVISORS', [
        {"id": "advisor_a", "name": "Advisor A", "model": "model-a", "prompt_file": "prompts/a.md"},
    ]):
        with patch('backend.group_chat.query_ollama', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {"content": "Response with context"}
            
            with patch('backend.ollama_client.get_system_prompt', new_callable=AsyncMock) as mock_system:
                mock_system.return_value = "System prompt"
                
                conversation_history = [
                    {"role": "user", "content": "First question"},
                    {
                        "role": "assistant",
                        "responses": [
                            {"advisor_name": "Advisor A", "response": "First answer"}
                        ]
                    }
                ]
                
                results = await run_group_chat("Follow-up question", ["advisor_a"], conversation_history)
                
                assert len(results) == 1
                # Verify that query was called with messages containing context
                call_args = mock_query.call_args
                # The messages are passed as a keyword argument
                messages_arg = call_args[1]["messages"]
                assert len(messages_arg) == 1
                assert "Previous conversation:" in messages_arg[0]["content"]


def test_build_conversation_context():
    """Test building conversation context from history."""
    history = [
        {"role": "user", "content": "Question 1"},
        {
            "role": "assistant",
            "responses": [
                {"advisor_name": "Advisor A", "response": "Answer 1A"},
                {"advisor_name": "Advisor B", "response": "Answer 1B"}
            ]
        },
        {"role": "user", "content": "Question 2"},
        {
            "role": "assistant",
            "responses": [
                {"advisor_name": "Advisor A", "response": "Answer 2A"}
            ]
        }
    ]
    
    context = build_conversation_context(history)
    
    assert "Previous conversation:" in context
    assert "User: Question 1" in context
    assert "Advisor A: Answer 1A" in context
    assert "Advisor B: Answer 1B" in context
    assert "User: Question 2" in context
    assert "Advisor A: Answer 2A" in context


def test_build_conversation_context_empty():
    """Test context building with empty history."""
    context = build_conversation_context([])
    assert context == ""


def test_build_conversation_context_max_messages():
    """Test context building respects max_messages limit."""
    history = [{"role": "user", "content": f"Question {i}"} for i in range(20)]
    
    context = build_conversation_context(history, max_messages=5)
    
    # Should only include last 5 messages
    assert "Question 15" in context
    assert "Question 19" in context
    assert "Question 10" not in context


def test_build_prompt_with_context():
    """Test prompt building with context."""
    user_query = "What do you think?"
    context = "Previous conversation:\nUser: Hello\nAdvisor: Hi there"
    advisor = {"id": "test", "name": "Test"}
    
    prompt = build_prompt_with_context(user_query, context, advisor)
    
    assert context in prompt
    assert user_query in prompt
    assert "User: What do you think?" in prompt


def test_build_prompt_without_context():
    """Test prompt building without context."""
    user_query = "What do you think?"
    context = ""
    advisor = {"id": "test", "name": "Test"}
    
    prompt = build_prompt_with_context(user_query, context, advisor)
    
    assert prompt == user_query


@pytest.mark.asyncio
async def test_generate_group_chat_title():
    """Test generating a title for group chat."""
    with patch('backend.group_chat.generate_conversation_title', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Discussion about AI"
        
        title = await generate_group_chat_title("What is AI?", ["Advisor A", "Advisor B"])
        
        assert title == "Discussion about AI"
        mock_gen.assert_called_once_with("What is AI?")


@pytest.mark.asyncio
async def test_run_group_chat_empty_members():
    """Test group chat with no members selected."""
    with patch('backend.group_chat.ADVISORS', []):
        results = await run_group_chat("Hello", [], [])
        assert results == []


@pytest.mark.asyncio
async def test_run_group_chat_filters_members():
    """Test that only selected members are included."""
    with patch('backend.group_chat.ADVISORS', [
        {"id": "advisor_a", "name": "Advisor A", "model": "model-a", "prompt_file": "prompts/a.md"},
        {"id": "advisor_b", "name": "Advisor B", "model": "model-b", "prompt_file": "prompts/b.md"},
        {"id": "advisor_c", "name": "Advisor C", "model": "model-c", "prompt_file": "prompts/c.md"},
    ]):
        with patch('backend.group_chat.query_ollama', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {"content": "Response"}
            
            with patch('backend.ollama_client.get_system_prompt', new_callable=AsyncMock) as mock_system:
                mock_system.return_value = "System prompt"
                
                # Only select advisor_a and advisor_c
                results = await run_group_chat("Hello", ["advisor_a", "advisor_c"], [])
                
                assert len(results) == 2
                advisor_ids = [r["advisor_id"] for r in results]
                assert "advisor_a" in advisor_ids
                assert "advisor_c" in advisor_ids
                assert "advisor_b" not in advisor_ids
