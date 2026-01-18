"""Integration tests for group chat API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.main import app
from unittest.mock import AsyncMock, patch
import uuid

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_db():
    """Create a test database."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async def get_test_db():
        async with AsyncSessionLocal() as session:
            yield session
    
    # Override the dependency
    from backend.main import get_db
    app.dependency_overrides[get_db] = get_test_db
    
    yield engine
    
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_group_chats_empty(test_db):
    """Test listing group chats when none exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/group-chats")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_create_group_chat(test_db):
    """Test creating a new group chat session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/group-chats",
            json={"member_ids": ["advisor_a", "advisor_b"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "New Group Chat"
        assert data["member_ids"] == ["advisor_a", "advisor_b"]
        assert data["messages"] == []


@pytest.mark.asyncio
async def test_create_group_chat_no_members(test_db):
    """Test creating a group chat with no members fails."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/group-chats",
            json={"member_ids": []}
        )
        assert response.status_code == 400
        assert "At least one member must be selected" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_group_chat(test_db):
    """Test getting a specific group chat session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a session first
        create_response = await client.post(
            "/api/group-chats",
            json={"member_ids": ["advisor_a"]}
        )
        session_id = create_response.json()["id"]
        
        # Get the session
        response = await client.get(f"/api/group-chats/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["member_ids"] == ["advisor_a"]


@pytest.mark.asyncio
async def test_get_group_chat_not_found(test_db):
    """Test getting a non-existent group chat session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/group-chats/nonexistent-id")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_group_chat(test_db):
    """Test deleting a group chat session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a session
        create_response = await client.post(
            "/api/group-chats",
            json={"member_ids": ["advisor_a"]}
        )
        session_id = create_response.json()["id"]
        
        # Delete it
        response = await client.delete(f"/api/group-chats/{session_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify it's gone
        get_response = await client.get(f"/api/group-chats/{session_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_group_chat_not_found(test_db):
    """Test deleting a non-existent group chat session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/group-chats/nonexistent-id")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_group_chat_message(test_db):
    """Test sending a message in a group chat."""
    # Mock the group chat runner
    with patch('backend.main.run_group_chat', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = [
            {
                "advisor_id": "advisor_a",
                "advisor_name": "Advisor A",
                "model": "model-a",
                "response": "Response from A"
            },
            {
                "advisor_id": "advisor_b",
                "advisor_name": "Advisor B",
                "model": "model-b",
                "response": "Response from B"
            }
        ]

        with patch('backend.main.generate_group_chat_title', new_callable=AsyncMock) as mock_title:
            mock_title.return_value = "Discussion about AI"

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Create a session
                create_response = await client.post(
                    "/api/group-chats",
                    json={"member_ids": ["advisor_a", "advisor_b"]}
                )
                session_id = create_response.json()["id"]
                
                # Send a message
                response = await client.post(
                    f"/api/group-chats/{session_id}/message",
                    json={"content": "Hello everyone"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "responses" in data
                assert len(data["responses"]) == 2
                assert data["responses"][0]["advisor_name"] == "Advisor A"
                
                # Verify title was generated (first message)
                mock_title.assert_called_once()


@pytest.mark.asyncio
async def test_send_group_chat_message_not_found(test_db):
    """Test sending a message to a non-existent session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/group-chats/nonexistent-id/message",
            json={"content": "Hello"}
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_group_chats_multiple(test_db):
    """Test listing multiple group chat sessions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create 3 sessions
        await client.post(
            "/api/group-chats",
            json={"member_ids": ["advisor_a"]}
        )
        await client.post(
            "/api/group-chats",
            json={"member_ids": ["advisor_b", "advisor_c"]}
        )
        await client.post(
            "/api/group-chats",
            json={"member_ids": ["advisor_a", "advisor_b", "advisor_c"]}
        )
        
        # List them
        response = await client.get("/api/group-chats")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
        # Should be ordered by created_at desc
        assert all("id" in item for item in data)
        assert all("member_ids" in item for item in data)
        assert all("message_count" in item for item in data)


@pytest.mark.asyncio
async def test_group_chat_conversation_flow(test_db):
    """Test a full conversation flow in a group chat."""
    with patch('backend.main.run_group_chat', new_callable=AsyncMock) as mock_run:
        # First call (first message)
        mock_run.side_effect = [
            [
                {"advisor_id": "advisor_a", "advisor_name": "A", "response": "Answer 1"}
            ],
            [
                {"advisor_id": "advisor_a", "advisor_name": "A", "response": "Answer 2"}
            ]
        ]

        with patch('backend.main.generate_group_chat_title', new_callable=AsyncMock) as mock_title:
            mock_title.return_value = "AI Discussion"

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Create session
                create_response = await client.post(
                    "/api/group-chats",
                    json={"member_ids": ["advisor_a"]}
                )
                session_id = create_response.json()["id"]
                
                # Send first message
                await client.post(
                    f"/api/group-chats/{session_id}/message",
                    json={"content": "Question 1"}
                )
                
                # Send second message
                await client.post(
                    f"/api/group-chats/{session_id}/message",
                    json={"content": "Question 2"}
                )
                
                # Get the session to verify messages
                get_response = await client.get(f"/api/group-chats/{session_id}")
                data = get_response.json()
                
                assert len(data["messages"]) == 4  # 2 user + 2 assistant
                assert data["messages"][0]["role"] == "user"
                assert data["messages"][0]["content"] == "Question 1"
                assert data["messages"][1]["role"] == "assistant"
                assert len(data["messages"][1]["responses"]) == 1
                assert data["messages"][2]["role"] == "user"
                assert data["messages"][3]["role"] == "assistant"
                
                # Title should only be generated once (first message)
                assert mock_title.call_count == 1


@pytest.mark.asyncio
async def test_group_chat_with_context(test_db):
    """Test that conversation history is passed to run_group_chat."""
    with patch('backend.main.run_group_chat', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = [
            {"advisor_id": "advisor_a", "advisor_name": "A", "response": "Answer"}
        ]

        with patch('backend.main.generate_group_chat_title', new_callable=AsyncMock) as mock_title:
            mock_title.return_value = "Discussion"

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Create session
                create_response = await client.post(
                    "/api/group-chats",
                    json={"member_ids": ["advisor_a"]}
                )
                session_id = create_response.json()["id"]
                
                # Send first message
                await client.post(
                    f"/api/group-chats/{session_id}/message",
                    json={"content": "Question 1"}
                )
                
                # Send second message
                await client.post(
                    f"/api/group-chats/{session_id}/message",
                    json={"content": "Question 2"}
                )
                
                # Verify second call included conversation history
                assert mock_run.call_count == 2
                second_call_args = mock_run.call_args_list[1]
                conversation_history = second_call_args[0][2]
                
                assert len(conversation_history) > 0
                assert conversation_history[0]["role"] == "user"
                assert conversation_history[0]["content"] == "Question 1"
