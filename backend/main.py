"""FastAPI backend for Circle of Trust."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import asyncio
import re
import os
from sqlalchemy.ext.asyncio import AsyncSession

from . import storage
from .database import init_db, get_db
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .group_chat import run_group_chat, generate_group_chat_title
from . import config
from .config import save_advisors, OLLAMA_API_URL
from .persona_generator import generate_persona_markdown, save_persona_file
from .monitoring import get_ollama_status, get_stats
import httpx

app = FastAPI(title="Circle of Trust API")

@app.on_event("startup")
async def on_startup():
    await init_db()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Message(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: Optional[str] = None
    stage1: Optional[List[Dict[str, Any]]] = None
    stage2: Optional[List[Dict[str, Any]]] = None
    stage3: Optional[Dict[str, Any]] = None
    created_at: datetime

class Conversation(BaseModel):
    """Full conversation with all messages."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    title: str
    messages: List[Message]

class AdvisorConfig(BaseModel):
    name: str
    description: Optional[str] = ""
    model: str

class CouncilConfigRequest(BaseModel):
    advisors: List[AdvisorConfig]


class CreateGroupChatRequest(BaseModel):
    """Request to create a new group chat session."""
    member_ids: List[str]


class GroupChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: Optional[str] = None
    responses: Optional[List[Dict[str, Any]]] = None
    created_at: datetime


class GroupChatSession(BaseModel):
    """Full group chat session with all messages."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    title: str
    member_ids: List[str]
    messages: List[GroupChatMessage]


class GroupChatSessionMetadata(BaseModel):
    """Group chat session metadata for list view."""
    id: str
    created_at: str
    title: str
    member_ids: List[str]
    message_count: int


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Circle of Trust API"}

@app.get("/api/models")
async def list_models():
    """List available Ollama models."""
    try:
        async with httpx.AsyncClient() as client:
            # Ollama tags endpoint
            response = await client.get(f"{OLLAMA_API_URL.replace('/chat', '/tags')}")
            if response.status_code == 200:
                data = response.json()
                return {"models": [model["name"] for model in data.get("models", [])]}
            return {"models": []}
    except Exception as e:
        print(f"Error fetching models: {e}")
        return {"models": []}

@app.get("/api/monitoring")
async def get_monitoring_data():
    """Get monitoring data including Ollama status and request stats."""
    status = await get_ollama_status()
    stats = get_stats()
    return {
        "status": status,
        "stats": stats
    }

@app.get("/api/council/config")
async def get_council_config():
    """Get current council configuration."""
    return {"advisors": config.ADVISORS}

@app.post("/api/council/config")
async def update_council_config(request: CouncilConfigRequest):
    """Update council configuration and generate personas if needed."""
    new_advisors = []
    
    for i, advisor in enumerate(request.advisors):
        # Sanitize name for ID and filename
        safe_name = re.sub(r'[^a-z0-9_]', '', advisor.name.lower().replace(' ', '_'))
        prompt_file = f"prompts/{safe_name}.md"
        
        # Always generate persona to ensure it's up to date with Wikipedia
        print(f"Generating persona for {advisor.name}...")
        content = await generate_persona_markdown(advisor.name, advisor.description or "")
        if content:
            save_persona_file(advisor.name, content)
        else:
            # Fallback if generation fails but file doesn't exist
            if not os.path.exists(prompt_file):
                basic_content = f"# {advisor.name}\n\n## System Prompt\n\nYou are {advisor.name}. {advisor.description or ''}."
                save_persona_file(advisor.name, basic_content)
        
        new_advisors.append({
            "id": safe_name,
            "name": advisor.name,
            "model": advisor.model,
            "prompt_file": prompt_file,
            "description": advisor.description or "" # Save description for UI
        })
    
    # Save to config
    save_advisors(new_advisors)
    
    return {"status": "success", "advisors": new_advisors}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """List all conversations (metadata only)."""
    return await storage.list_conversations(db)


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest, db: AsyncSession = Depends(get_db)):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = await storage.create_conversation(db, conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific conversation with all its messages."""
    conversation = await storage.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a conversation."""
    success = await storage.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "id": conversation_id}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = await storage.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation.messages) == 0

    # Add user message
    await storage.add_user_message(db, conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        await storage.update_conversation_title(db, conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    # Add assistant message with all stages
    await storage.add_assistant_message(
        db,
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = await storage.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation.messages) == 0

    async def event_generator():
        try:
            # Add user message
            await storage.add_user_message(db, conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                await storage.update_conversation_title(db, conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            await storage.add_assistant_message(
                db,
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================================
# Group Chat Endpoints
# ============================================================================

@app.get("/api/group-chats", response_model=List[GroupChatSessionMetadata])
async def list_group_chat_sessions(db: AsyncSession = Depends(get_db)):
    """List all group chat sessions (metadata only)."""
    return await storage.list_group_chat_sessions(db)


@app.post("/api/group-chats", response_model=GroupChatSession)
async def create_group_chat_session(request: CreateGroupChatRequest, db: AsyncSession = Depends(get_db)):
    """Create a new group chat session with selected members."""
    if not request.member_ids:
        raise HTTPException(status_code=400, detail="At least one member must be selected")
    
    session_id = str(uuid.uuid4())
    session = await storage.create_group_chat_session(db, session_id, request.member_ids)
    return session


@app.get("/api/group-chats/{session_id}", response_model=GroupChatSession)
async def get_group_chat_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific group chat session with all its messages."""
    session = await storage.get_group_chat_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Group chat session not found")
    return session


@app.delete("/api/group-chats/{session_id}")
async def delete_group_chat_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a group chat session."""
    success = await storage.delete_group_chat_session(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Group chat session not found")
    return {"status": "success", "id": session_id}


@app.post("/api/group-chats/{session_id}/message")
async def send_group_chat_message(session_id: str, request: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    """
    Send a message in a group chat and get responses from all selected members.
    """
    # Check if session exists
    session = await storage.get_group_chat_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Group chat session not found")

    # Check if this is the first message
    is_first_message = len(session.messages) == 0

    # Add user message
    await storage.add_group_chat_user_message(db, session_id, request.content)

    # Build conversation history for context
    conversation_history = []
    for msg in session.messages:
        if msg.role == "user":
            conversation_history.append({"role": "user", "content": msg.content})
        elif msg.role == "assistant" and msg.responses:
            conversation_history.append({"role": "assistant", "responses": msg.responses})

    # Get responses from all selected members (cast member_ids to list)
    member_ids_list = list(session.member_ids) if session.member_ids else []
    responses = await run_group_chat(request.content, member_ids_list, conversation_history)

    # Add assistant message with all responses
    await storage.add_group_chat_assistant_message(db, session_id, responses)

    # Generate title if first message
    if is_first_message:
        member_names = [resp["advisor_name"] for resp in responses]
        title = await generate_group_chat_title(request.content, member_names)
        await storage.update_group_chat_title(db, session_id, title)

    return {"responses": responses}


@app.post("/api/group-chats/{session_id}/message/stream")
async def send_group_chat_message_stream(session_id: str, request: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    """
    Send a message in a group chat and stream responses from selected members.
    """
    # Check if session exists
    session = await storage.get_group_chat_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Group chat session not found")

    # Check if this is the first message
    is_first_message = len(session.messages) == 0

    async def event_generator():
        try:
            # Add user message
            await storage.add_group_chat_user_message(db, session_id, request.content)

            # Build conversation history for context
            conversation_history = []
            for msg in session.messages:
                if msg.role == "user":
                    conversation_history.append({"role": "user", "content": msg.content})
                elif msg.role == "assistant" and msg.responses:
                    conversation_history.append({"role": "assistant", "responses": msg.responses})

            # Start title generation in parallel if first message
            title_task = None
            if is_first_message:
                # We'll get member names after responses
                pass

            # Get responses from all selected members (cast member_ids to list)
            member_ids_list = list(session.member_ids) if session.member_ids else []
            yield f"data: {json.dumps({'type': 'responses_start'})}\n\n"
            responses = await run_group_chat(request.content, member_ids_list, conversation_history)
            yield f"data: {json.dumps({'type': 'responses_complete', 'data': responses})}\n\n"

            # Generate title if first message
            if is_first_message:
                member_names = [resp["advisor_name"] for resp in responses]
                title = await generate_group_chat_title(request.content, member_names)
                await storage.update_group_chat_title(db, session_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save assistant message
            await storage.add_group_chat_assistant_message(db, session_id, responses)

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
