from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, delete, select
import json
import logging
from typing import Dict, Any

from ..database import get_db, get_session_maker
from ..models.chat import ChatSession, ChatMessage
from ..models.users import User
from .auth import get_current_user
from ..utils.embedding_factory import embedding_factory

from ..models import ModelProvider, ProviderHealth
from ..memory import MemoryStore
from ..personal_brain import PersonalBrain
from ..persistence.audit import AuditLog
from ..persistence.chat import ChatStore
from ..agent.graph import build_agent_graph, StreamManager

logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    text: str
    new_session: bool = False

class DeleteSessionsRequest(BaseModel):
    session_ids: list[int]

def build_chat_router(
    provider: ModelProvider,
    memory_store: MemoryStore,
    personal_brain: PersonalBrain,
    audit_log: AuditLog,
) -> APIRouter:
    router = APIRouter(prefix="/api/chat", tags=["chat"])
    manager = StreamManager(provider)
    session_factory = get_session_maker()
    chat_store = ChatStore(session_factory)
    
    agent_graph = build_agent_graph(
        memory_store, 
        chat_store,
        provider,
        personal_brain,
        audit_log,
        manager
    )

    @router.post("")
    async def chat(
        request: ChatRequest,
        user: User = Depends(get_current_user),
    ):
        text_input = request.text
        if not text_input:
             raise HTTPException(status_code=400, detail="Text required")

        # 1. Get/Create Session & Save User Message (Closed Loop)
        session_id = None
        user_msg_id = None
        try:
            if request.new_session:
                session_id = await chat_store.create_session(
                    user.user_id,
                    title=text_input[:30]
                )
            else:
                session_id = await chat_store.get_or_create_recent_session(
                    user.user_id, 
                    title_hint=text_input
                )
            # Save User Message with Embedding
            user_msg_id = await chat_store.save_message(
                session_id=session_id,
                user_id=user.user_id,
                role="user",
                content=text_input
            )
        except Exception as e:
            logger.error(f"Failed to save user message/session: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save message: {e}")

        # 2. Execute LangGraph
        initial_state = {
            "user_input": text_input,
            "user_id": user.user_id,
            "session_id": session_id,
            "trace_id": f"chat-{session_id}-{user_msg_id}", # Simple trace ID
            "stream_id": f"chat-{session_id}-{user_msg_id}",
            "memories": [],
            "chat_history": [],
            "agents": [],
            "final_prompt": "",
            "response_generator": None
        }
        
        final_state = await agent_graph.ainvoke(initial_state)
        
        # 3. Consume the stream to trigger generation and persistence
        generator = final_state.get("response_generator")
        if not generator:
             logger.error("Graph did not return a response generator")
             raise HTTPException(status_code=500, detail="Internal processing error")

        final_response_content = ""
        final_response_data = {}

        try:
            async for chunk in generator:
                # We iterate to drive the generator to completion
                # The generator saves to DB internally at the end
                try:
                    # Chunks are JSON strings
                    data = json.loads(chunk)
                    payload = data.get("payload", {})
                    if payload.get("name") == "assistant_final":
                         final_response_data = payload.get("args", {})
                         final_response_content = final_response_data.get("text", "")
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Error during generation: {e}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

        # 4. Store open loop (short term memory)
        await memory_store.store_open_loop(text_input, user.user_id)

        # 5. Return response
        return {
            "status": "ok",
            "session_id": session_id,
            "message_id": user_msg_id,
            "response": {
                "role": "Arthur",
                "content": final_response_content,
                "confidence": final_response_data.get("confidence"),
                "model_health": final_response_data.get("model_health")
            }
        }

    @router.get("/history")
    async def get_chat_history(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        stmt = text("""
            SELECT 
                s.id as session_id,
                s.created_at as session_created_at,
                m.role,
                m.content,
                m.created_at as message_created_at
            FROM chat_sessions s
            JOIN chat_messages m ON s.id = m.session_id
            WHERE s.user_id = :user_id
            ORDER BY s.created_at DESC, m.created_at ASC
        """)
        
        result = await db.execute(stmt, {"user_id": user.user_id})
        rows = result.fetchall()
        
        history = []
        current_session = None
        
        for row in rows:
            if current_session is None or current_session["id"] != row.session_id:
                if current_session:
                    history.append(current_session)
                current_session = {
                    "id": row.session_id,
                    "created_at": str(row.session_created_at),
                    "messages": []
                }
            
            current_session["messages"].append({
                "role": row.role,
                "content": row.content,
                "created_at": str(row.message_created_at)
            })
            
        if current_session:
            history.append(current_session)
            
        return history

    @router.delete("/sessions")
    async def delete_sessions(
        request: DeleteSessionsRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        if not request.session_ids:
            return {"status": "ok", "deleted": 0}

        # 1. Fetch message IDs
        stmt_msgs = select(ChatMessage.id).join(ChatSession).where(
            ChatSession.id.in_(request.session_ids),
            ChatSession.user_id == user.user_id
        )
        result_msgs = await db.execute(stmt_msgs)
        msg_ids = result_msgs.scalars().all()

        if msg_ids:
            logger.info(f"Deleting {len(msg_ids)} messages and their vectors")
            # 2. Delete vectors
            for m_id in msg_ids:
                 await db.execute(text("DELETE FROM chat_message_vectors WHERE id = :id"), {"id": m_id})
            
            # 3. Delete messages
            await db.execute(delete(ChatMessage).where(ChatMessage.id.in_(msg_ids)))
        
        # 4. Delete sessions
        stmt = delete(ChatSession).where(
            ChatSession.id.in_(request.session_ids),
            ChatSession.user_id == user.user_id
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Deleted {result.rowcount} sessions")
        
        return {"status": "ok", "deleted": result.rowcount}

    @router.delete("/history")
    async def clear_history(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        logger.info(f"Clearing history for user {user.user_id}")
        # 1. Fetch all message IDs
        stmt_msgs = select(ChatMessage.id).join(ChatSession).where(ChatSession.user_id == user.user_id)
        result_msgs = await db.execute(stmt_msgs)
        msg_ids = result_msgs.scalars().all()
        
        if msg_ids:
            logger.info(f"Deleting {len(msg_ids)} messages and their vectors")
            # 2. Delete vectors
            for m_id in msg_ids:
                 await db.execute(text("DELETE FROM chat_message_vectors WHERE id = :id"), {"id": m_id})
            
            # 3. Delete messages
            await db.execute(delete(ChatMessage).where(ChatMessage.id.in_(msg_ids)))

        # 4. Delete sessions
        stmt = delete(ChatSession).where(ChatSession.user_id == user.user_id)
        result = await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Deleted {result.rowcount} sessions")
        return {"status": "ok", "deleted": result.rowcount}

    return router
