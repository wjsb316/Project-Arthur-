from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, delete, select
import json
import logging

from ..database import get_db
from ..models.chat import ChatSession, ChatMessage
from ..models.users import User
from .auth import get_current_user
from ..utils.embedding_factory import embedding_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatRequest(BaseModel):
    text: str

class DeleteSessionsRequest(BaseModel):
    session_ids: list[int]

@router.post("")
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Generate embeddings using embedding_factory
    try:
        query_text = f"search_query: {request.text}"
        doc_text = f"search_document: {request.text}"
        
        query_embedding = embedding_factory.get_embedding(query_text)
        storage_embedding = embedding_factory.get_embedding(doc_text)
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

    query_embedding_json = json.dumps(query_embedding)
    storage_embedding_json = json.dumps(storage_embedding)

    # 2. Vector Similarity Search filtered by user
    threshold = 0.65  # Adjustable

    search_sql = text("""
        SELECT s.id as session_id, vec_distance_cosine(v.embedding, :embedding) as distance
        FROM chat_message_vectors v
        JOIN chat_messages m ON v.id = m.id
        JOIN chat_sessions s ON m.session_id = s.id
        WHERE s.user_id = :user_id
        ORDER BY distance ASC
        LIMIT 1
    """)
    
    result = await db.execute(search_sql, {"embedding": query_embedding_json, "user_id": user.user_id})
    match = result.fetchone()
    
    session_id = None
    if match:
        logger.info(f"Found match with distance {match.distance}")
        if match.distance < threshold:
            session_id = match.session_id
    
    # 3. Create or append
    if not session_id:
        logger.info("No matching session found. Creating new session.")
        new_session = ChatSession(user_id=user.user_id, title=request.text[:30])
        db.add(new_session)
        await db.flush()
        session_id = new_session.id
    else:
        logger.info(f"Continuing session {session_id}")

    # 4. Store text
    new_message = ChatMessage(
        session_id=session_id,
        user_id=user.user_id,
        role='user',
        content=request.text
    )
    db.add(new_message)
    await db.flush()

    # 5. Store vector
    await db.execute(text("""
        INSERT INTO chat_message_vectors(id, embedding) VALUES (:id, :embedding)
    """), {"id": new_message.id, "embedding": storage_embedding_json})
    
    # 6. Store Assistant Response (Placeholder)
    # To address "Role only says user", we store an assistant message.
    # In a real system, this would come from the LLM.
    assistant_message = ChatMessage(
        session_id=session_id,
        user_id=user.user_id,
        role='assistant',
        content="[System] This is a placeholder response. Integration with LLM required."
    )
    db.add(assistant_message)
    await db.flush() # Get ID

    await db.commit()
    
    # 7. Return status
    return {
        "status": "ok", 
        "session_id": session_id, 
        "message_id": new_message.id,
        "response_id": assistant_message.id,
        "is_continuation": bool(match and match.distance < threshold)
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

    # 1. Fetch message IDs associated with these sessions
    # Using JOIN ensures we only get messages for sessions belonging to this user
    stmt_msgs = select(ChatMessage.id).join(ChatSession).where(
        ChatSession.id.in_(request.session_ids),
        ChatSession.user_id == user.user_id
    )
    result_msgs = await db.execute(stmt_msgs)
    msg_ids = result_msgs.scalars().all()

    if msg_ids:
        logger.info(f"Deleting {len(msg_ids)} messages and their vectors")
        # 2. Delete vectors for these messages
        for m_id in msg_ids:
             await db.execute(text("DELETE FROM chat_message_vectors WHERE id = :id"), {"id": m_id})
        
        # 3. Explicitly delete messages to ensure they are gone even if cascade fails
        # We use IN clause with the fetched IDs
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
    # 1. Fetch all message IDs for this user via Session (covers old data without user_id)
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
