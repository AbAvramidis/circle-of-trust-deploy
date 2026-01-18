"""Database-based storage for conversations."""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from .models import Conversation, Message, GroupChatSession, GroupChatMessage
from datetime import datetime, timezone

async def create_conversation(db: AsyncSession, conversation_id: str) -> Optional[Conversation]:
    """
    Create a new conversation.
    """
    db_conversation = Conversation(
        id=conversation_id,
        title="New Conversation",
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_conversation)
    await db.commit()
    # Re-query to ensure everything is loaded correctly (including empty messages)
    return await get_conversation(db, conversation_id)


async def get_conversation(db: AsyncSession, conversation_id: str) -> Optional[Conversation]:
    """
    Load a conversation from storage.
    """
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    return result.scalars().first()


async def list_conversations(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).
    """
    result = await db.execute(
        select(Conversation).order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()
    
    # We need to get message counts. 
    # Ideally we'd do a count query, but for now let's just load them or assume 0 if not loaded?
    # selectinload might be heavy for a list.
    # Let's do a separate query or just return the objects and let Pydantic handle it if we load messages?
    # The current API expects a list of dicts with message_count.
    
    # Optimized query for metadata + count would be better, but let's keep it simple first.
    # We can fetch messages eagerly or just count them.
    
    # Let's just return the objects and let the caller handle it, 
    # BUT the caller expects a specific dict structure in the current implementation.
    # Let's match the previous return format.
    
    output: List[Dict[str, Any]] = []
    for conv in conversations:
        # This is N+1 if we access messages here without loading them.
        # But for now, let's just return the list.
        # To avoid N+1, we should probably join or count.
        # For simplicity in this migration, let's just return the list and maybe skip message_count or fetch it.
        
        # Let's do a fetch with messages for now to be safe, or just use the object.
        # Actually, let's use a query that includes the count if possible, or just lazy load.
        # Since we are async, lazy load is tricky (needs await).
        
        # Let's just load conversations with messages for now.
        pass

    # Re-query with eager load for now to be safe
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "created_at": c.created_at.isoformat(),
            "title": c.title,
            "message_count": len(c.messages)
        }
        for c in conversations
    ]


async def add_user_message(db: AsyncSession, conversation_id: str, content: str):
    """
    Add a user message to a conversation.
    """
    message = Message(
        conversation_id=conversation_id,
        role="user",
        content=content
    )
    db.add(message)
    await db.commit()


async def add_assistant_message(
    db: AsyncSession,
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any]
):
    """
    Add an assistant message with all 3 stages to a conversation.
    """
    message = Message(
        conversation_id=conversation_id,
        role="assistant",
        stage1=stage1,
        stage2=stage2,
        stage3=stage3
    )
    db.add(message)
    await db.commit()


async def update_conversation_title(db: AsyncSession, conversation_id: str, title: str):
    """
    Update the title of a conversation.
    """
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalars().first()
    if conversation:
        setattr(conversation, 'title', title)
        await db.commit()


async def delete_conversation(db: AsyncSession, conversation_id: str) -> bool:
    """
    Delete a conversation.
    """
    conversation = await get_conversation(db, conversation_id)
    if conversation:
        await db.delete(conversation)
        await db.commit()
        return True
    return False


# ============================================================================
# Group Chat Session Storage Functions
# ============================================================================

async def create_group_chat_session(db: AsyncSession, session_id: str, member_ids: List[str], title: str = "New Group Chat") -> Optional[GroupChatSession]:
    """
    Create a new group chat session.
    """
    db_session = GroupChatSession(
        id=session_id,
        title=title,
        member_ids=member_ids,
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_session)
    await db.commit()
    return await get_group_chat_session(db, session_id)


async def get_group_chat_session(db: AsyncSession, session_id: str) -> Optional[GroupChatSession]:
    """
    Load a group chat session from storage.
    """
    result = await db.execute(
        select(GroupChatSession)
        .options(selectinload(GroupChatSession.messages))
        .where(GroupChatSession.id == session_id)
    )
    return result.scalars().first()


async def list_group_chat_sessions(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    List all group chat sessions (metadata only).
    """
    result = await db.execute(
        select(GroupChatSession)
        .options(selectinload(GroupChatSession.messages))
        .order_by(GroupChatSession.created_at.desc())
    )
    sessions = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "created_at": s.created_at.isoformat(),
            "title": s.title,
            "member_ids": s.member_ids,
            "message_count": len(s.messages)
        }
        for s in sessions
    ]


async def add_group_chat_user_message(db: AsyncSession, session_id: str, content: str):
    """
    Add a user message to a group chat session.
    """
    message = GroupChatMessage(
        session_id=session_id,
        role="user",
        content=content
    )
    db.add(message)
    await db.commit()


async def add_group_chat_assistant_message(
    db: AsyncSession,
    session_id: str,
    responses: List[Dict[str, Any]]
):
    """
    Add an assistant message with responses from all selected members.
    
    Args:
        responses: List of dicts with keys: advisor_id, advisor_name, response
    """
    message = GroupChatMessage(
        session_id=session_id,
        role="assistant",
        responses=responses
    )
    db.add(message)
    await db.commit()


async def update_group_chat_title(db: AsyncSession, session_id: str, title: str):
    """
    Update the title of a group chat session.
    """
    result = await db.execute(
        select(GroupChatSession).where(GroupChatSession.id == session_id)
    )
    session = result.scalars().first()
    if session:
        setattr(session, 'title', title)
        await db.commit()


async def delete_group_chat_session(db: AsyncSession, session_id: str) -> bool:
    """
    Delete a group chat session.
    """
    session = await get_group_chat_session(db, session_id)
    if session:
        await db.delete(session)
        await db.commit()
        return True
    return False
