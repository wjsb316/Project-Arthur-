from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models.users import User
from .auth import get_current_user
from ..memory import MemoryStore
from ..database import get_session_maker

router = APIRouter(prefix="/api/memories", tags=["memories"])

# Dependency to get memory store (reusing the session maker)
def get_memory_store():
    return MemoryStore(get_session_maker())

class MemoryCreate(BaseModel):
    content: str
    kind: str = "fact"  # fact, episode, open_loop

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

@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: int,
    user: User = Depends(get_current_user),
    store: MemoryStore = Depends(get_memory_store)
):
    """Delete a memory."""
    success = await store.forget(memory_id, user.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "ok"}
