"""Tests for group chat storage functions."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend import storage
from backend.models import GroupChatSession, GroupChatMessage
import uuid

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session
        await session.close()
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_group_chat_session(db_session):
    """Test creating a new group chat session."""
    session_id = str(uuid.uuid4())
    member_ids = ["advisor_a", "advisor_b", "advisor_c"]
    
    session = await storage.create_group_chat_session(db_session, session_id, member_ids)
    
    assert session.id == session_id
    assert session.title == "New Group Chat"
    assert session.member_ids == member_ids
    
    # Verify it's in the DB
    fetched = await storage.get_group_chat_session(db_session, session_id)
    assert fetched is not None
    assert fetched.id == session_id
    assert fetched.member_ids == member_ids


@pytest.mark.asyncio
async def test_create_group_chat_session_with_title(db_session):
    """Test creating a group chat session with custom title."""
    session_id = str(uuid.uuid4())
    member_ids = ["advisor_a", "advisor_b"]
    title = "Discussion about AI"
    
    session = await storage.create_group_chat_session(
        db_session, session_id, member_ids, title
    )
    
    assert session.title == title


@pytest.mark.asyncio
async def test_get_group_chat_session_not_found(db_session):
    """Test getting a non-existent group chat session."""
    result = await storage.get_group_chat_session(db_session, "nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_list_group_chat_sessions(db_session):
    """Test listing all group chat sessions."""
    # Create 2 sessions
    session_id_1 = str(uuid.uuid4())
    session_id_2 = str(uuid.uuid4())
    
    await storage.create_group_chat_session(
        db_session, session_id_1, ["advisor_a"], "Session 1"
    )
    await storage.create_group_chat_session(
        db_session, session_id_2, ["advisor_b", "advisor_c"], "Session 2"
    )
    
    sessions = await storage.list_group_chat_sessions(db_session)
    
    assert len(sessions) == 2
    assert sessions[0]["title"] == "Session 2"  # Most recent first
    assert sessions[1]["title"] == "Session 1"
    assert sessions[0]["message_count"] == 0
    assert sessions[0]["member_ids"] == ["advisor_b", "advisor_c"]


@pytest.mark.asyncio
async def test_add_group_chat_user_message(db_session):
    """Test adding a user message to a group chat."""
    session_id = str(uuid.uuid4())
    await storage.create_group_chat_session(db_session, session_id, ["advisor_a"])
    
    await storage.add_group_chat_user_message(db_session, session_id, "Hello everyone")
    
    session = await storage.get_group_chat_session(db_session, session_id)
    assert len(session.messages) == 1
    assert session.messages[0].role == "user"
    assert session.messages[0].content == "Hello everyone"


@pytest.mark.asyncio
async def test_add_group_chat_assistant_message(db_session):
    """Test adding an assistant message with responses."""
    session_id = str(uuid.uuid4())
    await storage.create_group_chat_session(
        db_session, session_id, ["advisor_a", "advisor_b"]
    )
    
    responses = [
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
    
    await storage.add_group_chat_assistant_message(db_session, session_id, responses)
    
    db_session.expire_all()
    session = await storage.get_group_chat_session(db_session, session_id)
    
    assert len(session.messages) == 1
    assert session.messages[0].role == "assistant"
    assert session.messages[0].responses == responses
    assert len(session.messages[0].responses) == 2


@pytest.mark.asyncio
async def test_full_group_chat_conversation(db_session):
    """Test a complete group chat conversation flow."""
    session_id = str(uuid.uuid4())
    await storage.create_group_chat_session(
        db_session, session_id, ["advisor_a", "advisor_b"]
    )
    
    # User message 1
    await storage.add_group_chat_user_message(db_session, session_id, "Question 1")
    
    # Assistant responses 1
    responses_1 = [
        {"advisor_id": "advisor_a", "advisor_name": "A", "response": "Answer 1A"},
        {"advisor_id": "advisor_b", "advisor_name": "B", "response": "Answer 1B"}
    ]
    await storage.add_group_chat_assistant_message(db_session, session_id, responses_1)
    
    # User message 2
    await storage.add_group_chat_user_message(db_session, session_id, "Question 2")
    
    # Assistant responses 2
    responses_2 = [
        {"advisor_id": "advisor_a", "advisor_name": "A", "response": "Answer 2A"},
        {"advisor_id": "advisor_b", "advisor_name": "B", "response": "Answer 2B"}
    ]
    await storage.add_group_chat_assistant_message(db_session, session_id, responses_2)
    
    db_session.expire_all()
    session = await storage.get_group_chat_session(db_session, session_id)
    
    assert len(session.messages) == 4
    assert session.messages[0].role == "user"
    assert session.messages[0].content == "Question 1"
    assert session.messages[1].role == "assistant"
    assert len(session.messages[1].responses) == 2
    assert session.messages[2].role == "user"
    assert session.messages[2].content == "Question 2"
    assert session.messages[3].role == "assistant"
    assert len(session.messages[3].responses) == 2


@pytest.mark.asyncio
async def test_update_group_chat_title(db_session):
    """Test updating a group chat session title."""
    session_id = str(uuid.uuid4())
    await storage.create_group_chat_session(db_session, session_id, ["advisor_a"])
    
    new_title = "Updated Title"
    await storage.update_group_chat_title(db_session, session_id, new_title)
    
    session = await storage.get_group_chat_session(db_session, session_id)
    assert session.title == new_title


@pytest.mark.asyncio
async def test_delete_group_chat_session(db_session):
    """Test deleting a group chat session."""
    session_id = str(uuid.uuid4())
    await storage.create_group_chat_session(db_session, session_id, ["advisor_a"])
    
    # Add some messages
    await storage.add_group_chat_user_message(db_session, session_id, "Test")
    
    # Delete the session
    success = await storage.delete_group_chat_session(db_session, session_id)
    assert success is True
    
    # Verify it's gone
    session = await storage.get_group_chat_session(db_session, session_id)
    assert session is None


@pytest.mark.asyncio
async def test_delete_group_chat_session_not_found(db_session):
    """Test deleting a non-existent group chat session."""
    success = await storage.delete_group_chat_session(db_session, "nonexistent-id")
    assert success is False


@pytest.mark.asyncio
async def test_list_group_chat_sessions_with_messages(db_session):
    """Test that list includes message count."""
    session_id = str(uuid.uuid4())
    await storage.create_group_chat_session(db_session, session_id, ["advisor_a"])
    
    # Add messages
    await storage.add_group_chat_user_message(db_session, session_id, "Msg 1")
    await storage.add_group_chat_assistant_message(
        db_session, session_id, [{"advisor_id": "advisor_a", "response": "Reply 1"}]
    )
    await storage.add_group_chat_user_message(db_session, session_id, "Msg 2")
    
    sessions = await storage.list_group_chat_sessions(db_session)
    
    assert len(sessions) == 1
    assert sessions[0]["message_count"] == 3
