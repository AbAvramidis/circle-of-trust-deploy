from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), index=True)
    role = Column(String) # 'user' or 'assistant'
    content = Column(Text, nullable=True) # For user messages
    
    # For assistant messages (structured data)
    stage1 = Column(JSON, nullable=True)
    stage2 = Column(JSON, nullable=True)
    stage3 = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")


class GroupChatSession(Base):
    __tablename__ = "group_chat_sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="New Group Chat")
    member_ids = Column(JSON)  # List of advisor IDs participating
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship to messages
    messages = relationship("GroupChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="GroupChatMessage.created_at")


class GroupChatMessage(Base):
    __tablename__ = "group_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("group_chat_sessions.id"), index=True)
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text, nullable=True)  # For user messages
    
    # For assistant messages - multiple responses from different members
    responses = Column(JSON, nullable=True)  # List of {advisor_id, advisor_name, response}
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("GroupChatSession", back_populates="messages")
