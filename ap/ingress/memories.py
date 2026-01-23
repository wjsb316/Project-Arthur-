from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text

from ..database import get_db
from ..models.users import User
from ..models.memory import Memory
from .auth import get_current_user
from ..memory import MemoryStore
from ..database import get_session_maker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memories", tags=["memories"])

# Dependency to get memory store (reusing the session maker)
def get_memory_store():
    return MemoryStore(get_session_maker())

class MemoryCreate(BaseModel):
    content: str
    kind: str = "fact"  # fact, episode, open_loop

class DeleteMemoriesRequest(BaseModel):
    memory_ids: list[int]

class MemoryResponse(BaseModel):
    id: int
    content: str
    kind: str
    created_at: datetime
    importance: float

@router.get("/", response_model=List[MemoryResponse])
async def list_memories(
    query: Optional[str] = Query(None, description="Search query"),
    limit: int = 20,
    user: User = Depends(get_current_user),
    store: MemoryStore = Depends(get_memory_store)
):
    """List or search memories."""
    if query:
        memories = await store.retrieve_relevant(query, user.user_id, limit=limit)
    else:
        # If no query, just return recent ones (using a blank query effectively falls back to recency)
        memories = await store.retrieve_relevant("", user.user_id, limit=limit)
        
    return [
        MemoryResponse(
            id=m.id,
            content=m.content,
            kind=m.kind,
            created_at=m.created_at,
            importance=m.importance
        ) for m in memories
    ]

@router.post("/", response_model=dict)
async def create_memory(
    memory: MemoryCreate,
    user: User = Depends(get_current_user),
    store: MemoryStore = Depends(get_memory_store)
):
    """Create a new memory."""
    if memory.kind == "fact":
        mem_id = await store.store_fact(memory.content, user.user_id)
    elif memory.kind == "episode":
        mem_id = await store.store_episode(memory.content, user.user_id)
    elif memory.kind == "open_loop":
        mem_id = await store.store_open_loop(memory.content, user.user_id)
    else:
        # Default to fact
        mem_id = await store.store_fact(memory.content, user.user_id)
        
    return {"status": "ok", "id": mem_id}

@router.delete("/selected/bulk")
async def delete_selected_memories(
    request: DeleteMemoriesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete multiple memories by IDs."""
    if not request.memory_ids:
        return {"status": "ok", "deleted": 0}

    # Get memory IDs that belong to this user
    stmt_check = select(Memory.id).where(
        Memory.id.in_(request.memory_ids),
        Memory.user_id == user.user_id
    )
    result_check = await db.execute(stmt_check)
    valid_ids = result_check.scalars().all()

    if valid_ids:
        logger.info(f"Deleting {len(valid_ids)} memories and their vectors")
        # Delete vectors first
        for m_id in valid_ids:
            await db.execute(text("DELETE FROM memory_vectors WHERE id = :id"), {"id": m_id})
        
        # Delete memories
        stmt = delete(Memory).where(Memory.id.in_(valid_ids))
        result = await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Deleted {result.rowcount} memories")
        return {"status": "ok", "deleted": result.rowcount}
    
    return {"status": "ok", "deleted": 0}

@router.delete("/all/nuke")
async def nuke_all_memories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete all memories for the current user."""
    logger.info(f"Nuking all memories for user {user.user_id}")
    
    # Get all memory IDs for this user
    stmt_ids = select(Memory.id).where(Memory.user_id == user.user_id)
    result_ids = await db.execute(stmt_ids)
    memory_ids = result_ids.scalars().all()
    
    if memory_ids:
        logger.info(f"Deleting {len(memory_ids)} memories and their vectors")
        # Delete vectors first
        for m_id in memory_ids:
            await db.execute(text("DELETE FROM memory_vectors WHERE id = :id"), {"id": m_id})
        
        # Delete memories
        stmt = delete(Memory).where(Memory.user_id == user.user_id)
        result = await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Deleted {result.rowcount} memories")
        return {"status": "ok", "deleted": result.rowcount}
    
    return {"status": "ok", "deleted": 0}
