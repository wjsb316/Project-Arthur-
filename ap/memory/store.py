"""SQLite-backed structured memory store with recency, decay weighting, and vector search."""

from __future__ import annotations

import logging
import time
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, text
from sqlalchemy.orm import selectinload

from ..models.memory import Memory

logger = logging.getLogger("arthur.ap.memory")

@dataclass
class MemoryEntry:
    """Represents a single retrieved memory item."""
    id: int
    user_id: str
    kind: str  # "fact", "episode", "open_loop"
    content: str
    importance: float
    decay_rate: float
    created_at: datetime
    last_accessed: datetime


class MemoryStore:
    """Persists structured memory entries using SQLAlchemy + sqlite-vec."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def _store(self, kind: str, content: str, user_id: str, *, importance: float = 1.0, decay_rate: float = 0.01) -> int:
        content = content[:2048]
        now = datetime.now(timezone.utc)
        
        async with self._session_factory() as session:
            memory = Memory(
                user_id=user_id,
                kind=kind,
                content=content,
                importance=importance,
                decay_rate=decay_rate,
                created_at=now,
                last_accessed=now
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            
            # TODO: Generate embedding and insert into vec0 table
            # embedding = await embedding_model.embed(content)
            # await session.execute(
            #     text("INSERT INTO memory_vectors(id, embedding) VALUES (:id, :embedding)"),
            #     {"id": memory.id, "embedding": serialize_float32(embedding)}
            # )
            # await session.commit()
            
            return memory.id

    async def store_fact(self, content: str, user_id: str, *, importance: float = 1.0, decay_rate: float = 0.01) -> int:
        return await self._store("fact", content, user_id, importance=importance, decay_rate=decay_rate)

    async def store_episode(self, content: str, user_id: str, *, importance: float = 1.0, decay_rate: float = 0.01) -> int:
        return await self._store("episode", content, user_id, importance=importance, decay_rate=decay_rate)

    async def store_open_loop(self, content: str, user_id: str, *, importance: float = 0.5, decay_rate: float = 0.02) -> int:
        return await self._store("open_loop", content, user_id, importance=importance, decay_rate=decay_rate)

    async def forget(self, entry_id: int, user_id: str) -> bool:
        async with self._session_factory() as session:
            stmt = delete(Memory).where(Memory.id == entry_id, Memory.user_id == user_id)
            result = await session.execute(stmt)
            
            # Also delete from vector table
            await session.execute(
                text("DELETE FROM memory_vectors WHERE id = :id"),
                {"id": entry_id}
            )
            
            await session.commit()
            return result.rowcount > 0

    async def retrieve_relevant(self, query: str, user_id: str, *, limit: int = 5) -> List[MemoryEntry]:
        """Retrieve memories relevant to the query string for a specific user.
        
        Uses a hybrid approach:
        1. If embeddings available: Vector search (semantic)
        2. Always: Recency/Decay/Keyword overlap (lexical)
        """
        now_ts = int(time.time())
        tokens = set(query.lower().split())
        
        async with self._session_factory() as session:
            # Note: Full vector search integration requires an embedding model in the loop.
            # For now, we rely on the lexical heuristic, but prepare the SQL path.
            
            # Example Vector Query (commented out until embedding model connected):
            # vector_candidates = await session.execute(
            #     text("SELECT id, distance FROM memory_vectors WHERE embedding MATCH :query_vec AND k = 20"),
            #     {"query_vec": ...}
            # )
            
            # Fallback / Baseline: Recency-biased fetch
            stmt = select(Memory).where(Memory.user_id == user_id).order_by(Memory.last_accessed.desc()).limit(100)
            result = await session.execute(stmt)
            rows = result.scalars().all()

        scored = []
        for row in rows:
            # Basic ranking logic logic port
            row_last_access = row.last_accessed.timestamp()
            age_hours = max(0.0, (now_ts - row_last_access) / 3600)
            recency_weight = 1 / (1 + age_hours)
            decay_weight = pow(2.71828, -row.decay_rate * age_hours)
            content_tokens = set(row.content.lower().split())
            overlap = len(tokens & content_tokens)
            score = (row.importance + overlap) * recency_weight * decay_weight
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [row for _, row in scored[:limit] if _ > 0]
        
        if selected:
            await self._mark_accessed([row.id for row in selected])

        return [self._row_to_entry(row) for row in selected]

    def _row_to_entry(self, row: Memory) -> MemoryEntry:
        return MemoryEntry(
            id=row.id,
            user_id=row.user_id,
            kind=row.kind,
            content=row.content,
            importance=row.importance,
            decay_rate=row.decay_rate,
            created_at=row.created_at,
            last_accessed=row.last_accessed,
        )

    async def _mark_accessed(self, entry_ids: Iterable[int]) -> None:
        ids = list(entry_ids)
        if not ids:
            return
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            stmt = update(Memory).where(Memory.id.in_(ids)).values(last_accessed=now)
            await session.execute(stmt)
            await session.commit()
