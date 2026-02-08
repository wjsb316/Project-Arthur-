from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, delete, select
import json
import logging
import base64
from typing import Dict, Any, Optional
import tempfile
import os

from ..database import get_db, get_session_maker
from ..models.chat import ChatSession, ChatMessage
from ..models.users import User
from .auth import get_current_user
from ..utils.embedding_factory import embedding_factory
from ..utils.whisper_factory import whisper_factory
from ..utils.neurtts_factory import neurtts_factory

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
    session_id: Optional[int] = None  # Allows continuing a specific session

class DeleteSessionsRequest(BaseModel):
    session_ids: list[int]

def build_chat_router(
    provider: ModelProvider,
    memory_store: MemoryStore,
    personal_brain: PersonalBrain,
    audit_log: AuditLog,
    voice_system_prompt: Optional[str] = None,
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
        manager,
        voice_system_prompt=voice_system_prompt,
    )

    async def _process_chat_core(
        text_input: str,
        user: User,
        new_session: bool = False,
        session_id: Optional[int] = None,
        is_voice: bool = False,
    ):
        if not text_input:
             raise HTTPException(status_code=400, detail="Text required")

        # 1. Get/Create Session & Save User Message (Closed Loop)
        current_session_id = None
        user_msg_id = None
        try:
            if session_id:
                # Continuing a specific session - verify it belongs to this user
                current_session_id = await chat_store.verify_and_get_session(
                    session_id,
                    user.user_id
                )
                if not current_session_id:
                    raise HTTPException(status_code=404, detail="Session not found")
            elif new_session:
                current_session_id = await chat_store.create_session(
                    user.user_id,
                    title=text_input[:30]
                )
            else:
                current_session_id = await chat_store.get_or_create_recent_session(
                    user.user_id, 
                    title_hint=text_input
                )
            # Save User Message with Embedding
            user_msg_id = await chat_store.save_message(
                session_id=current_session_id,
                user_id=user.user_id,
                role="user",
                content=text_input
            )
        except Exception as e:
            logger.error(f"Failed to save user message/session: {e}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Failed to save message: {e}")

        # 2. Execute LangGraph
        initial_state = {
            "user_input": text_input,
            "user_id": user.user_id,
            "session_id": current_session_id,
            "trace_id": f"chat-{current_session_id}-{user_msg_id}",  # Simple trace ID
            "stream_id": f"chat-{current_session_id}-{user_msg_id}",
            "is_voice": is_voice,
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
            "session_id": current_session_id,
            "message_id": user_msg_id,
            "response": {
                "role": "Arthur",
                "content": final_response_content,
                "confidence": final_response_data.get("confidence"),
                "model_health": final_response_data.get("model_health")
            }
        }

    @router.post("")
    async def chat(
        request: ChatRequest,
        user: User = Depends(get_current_user),
    ):
        return await _process_chat_core(
            text_input=request.text,
            user=user,
            new_session=request.new_session,
            session_id=request.session_id,
            is_voice=False,
        )

    @router.post("/voice")
    async def voice_chat(
        file: UploadFile = File(...),
        speed: float = Query(1.0, ge=0.5, le=2.0, description="Playback speed: 1.0=normal, <1=slower (may sound odd)"),
        user: User = Depends(get_current_user),
    ):
        try:
            # 1. Save upload to temporary file
            suffix = os.path.splitext(file.filename)[1] if file.filename else ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            try:
                # 2. Transcribe using factory
                segments, info = whisper_factory.transcribe(tmp_path, beam_size=5)
                
                # Collect all segments
                transcribed_text = " ".join([segment.text for segment in segments]).strip()
                logger.info(f"Transcribed audio: {transcribed_text} (language: {info.language}, prob: {info.language_probability})")
                
                if not transcribed_text:
                    raise HTTPException(status_code=400, detail="Could not transcribe audio")

                # 3. Process as chat (voice mode: use TTS-oriented system prompt)
                result = await _process_chat_core(
                    text_input=transcribed_text,
                    user=user,
                    new_session=False,
                    session_id=None,
                    is_voice=True,
                )

                # 4. Synthesize speech response
                response_text = result["response"]["content"]
                audio_base64 = None
                if response_text:
                    wav_bytes = await neurtts_factory.generate_audio_wav(response_text, speed=speed)
                    if wav_bytes:
                        audio_base64 = base64.b64encode(wav_bytes).decode('utf-8')
                    
                result["audio_base64"] = audio_base64
                return result
                
            finally:
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Voice processing failed: {e}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Voice processing failed: {e}")
    
    @router.post("/voice/stream")
    async def voice_chat_stream(
        file: UploadFile = File(...),
        speed: float = Query(1.0, ge=0.5, le=2.0, description="Playback speed: 1.0=normal, <1=slower (may sound odd)"),
        session_id: Optional[int] = Query(None, description="Continue this chat session (e.g. from chat window)"),
        user: User = Depends(get_current_user),
    ):
        """
        Voice chat endpoint with streaming audio response.
        Returns audio chunks as they're generated for lower latency.
        """
        try:
            # 1. Save upload to temporary file
            suffix = os.path.splitext(file.filename)[1] if file.filename else ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            try:
                # 2. Transcribe using factory
                segments, info = whisper_factory.transcribe(tmp_path, beam_size=5)
                
                # Collect all segments
                transcribed_text = " ".join([segment.text for segment in segments]).strip()
                logger.info(f"Transcribed audio: {transcribed_text} (language: {info.language}, prob: {info.language_probability})")
                
                if not transcribed_text:
                    raise HTTPException(status_code=400, detail="Could not transcribe audio")

                # 3. Process as chat (voice mode: use TTS-oriented system prompt)
                result = await _process_chat_core(
                    text_input=transcribed_text,
                    user=user,
                    new_session=False,
                    session_id=session_id,
                    is_voice=True,
                )

                # 4. Stream speech response
                response_text = result["response"]["content"]
                if not response_text:
                    raise HTTPException(status_code=500, detail="No response generated")
                
                # Stream audio chunks as they're generated
                async def audio_generator():
                    async for chunk in neurtts_factory.generate_audio_stream(response_text, speed=speed):
                        yield chunk
                
                return StreamingResponse(
                    audio_generator(),
                    media_type="application/octet-stream",
                    headers={
                        "X-Session-ID": str(result["session_id"]),
                        "X-Message-ID": str(result["message_id"]),
                        "X-Transcribed-Text": transcribed_text,
                        "X-Audio-Format": "pcm16-length-prefixed",  # 4-byte uint32 LE length + PCM data
                        "X-Audio-Sample-Rate": "24000",
                        "X-Audio-Channels": "1",
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no",  # Disable nginx buffering if present
                    }
                )
                
            finally:
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Voice streaming failed: {e}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Voice streaming failed: {e}")

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
