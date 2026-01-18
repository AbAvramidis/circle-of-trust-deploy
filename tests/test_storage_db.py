import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend import storage
from backend.models import Conversation, Message
import uuid

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session
        await session.close()
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_conversation(db_session):
    conv_id = str(uuid.uuid4())
    conv = await storage.create_conversation(db_session, conv_id)
    
    assert conv.id == conv_id
    assert conv.title == "New Conversation"
    
    # Verify it's in the DB
    fetched = await storage.get_conversation(db_session, conv_id)
    assert fetched is not None
    assert fetched.id == conv_id

@pytest.mark.asyncio
async def test_add_messages(db_session):
    conv_id = str(uuid.uuid4())
    await storage.create_conversation(db_session, conv_id)
    
    # Add user message
    await storage.add_user_message(db_session, conv_id, "Hello")
    
    conv = await storage.get_conversation(db_session, conv_id)
    assert len(conv.messages) == 1
    assert conv.messages[0].role == "user"
    assert conv.messages[0].content == "Hello"
    
    # Add assistant message
    stage1 = [{"model": "A", "response": "Hi"}]
    stage2 = [{"model": "A", "ranking": "1"}]
    stage3 = {"model": "Chair", "response": "Hello there"}
    
    await storage.add_assistant_message(db_session, conv_id, stage1, stage2, stage3)
    
    # Refresh conversation
    # Note: In a real session, we might need to refresh or expire, 
    # but get_conversation does a fresh select.
    # However, since we are in the same session transaction, we might see cached objects.
    # storage.get_conversation does a select, which should see the new messages if committed.
    # storage functions commit.
    
    # We need to expire the relationship or refresh the object to see the new messages 
    # if we are reusing the same object instance in the session identity map.
    # storage.get_conversation returns a scalar result.
    
    # Let's force a refresh by clearing session or just calling get_conversation again.
    db_session.expire_all()
    conv = await storage.get_conversation(db_session, conv_id)
    
    assert len(conv.messages) == 2
    assert conv.messages[1].role == "assistant"
    assert conv.messages[1].stage3["response"] == "Hello there"

@pytest.mark.asyncio
async def test_list_conversations(db_session):
    # Create 2 conversations
    c1 = await storage.create_conversation(db_session, str(uuid.uuid4()))
    c2 = await storage.create_conversation(db_session, str(uuid.uuid4()))
    
    # Add a message to c1
    await storage.add_user_message(db_session, c1.id, "msg")
    
    # Expire session to ensure fresh data
    db_session.expire_all()

    convs = await storage.list_conversations(db_session)
    assert len(convs) == 2
    
    # Check structure
    assert "id" in convs[0]
    assert "message_count" in convs[0]
    
    # Find c1
    c1_meta = next(c for c in convs if c["id"] == c1.id)
    assert c1_meta["message_count"] == 1

@pytest.mark.asyncio
async def test_delete_conversation(db_session):
    conv_id = str(uuid.uuid4())
    await storage.create_conversation(db_session, conv_id)
    
    assert await storage.delete_conversation(db_session, conv_id) is True
    assert await storage.get_conversation(db_session, conv_id) is None
    assert await storage.delete_conversation(db_session, conv_id) is False
