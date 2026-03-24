"""SQLite-backed structured memory store with recency, decay weighting, and vector search."""

from __future__ import annotations

import logging
import time
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List

from sqlalchemy import select, update, delete, text

from ..models.memory import Memory
from ..utils.embedding_factory import embedding_factory

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

    async def _store(self, kind: str, content: str, user_id: str, *, importance: float = 1.0, decay_rate: float = 0.01) -> int:  # noqa: E501
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
            
            try:
                # Generate embedding and insert into vec0 table
                embedding = embedding_factory.get_embedding(content)
                embedding_json = json.dumps(embedding)
                
                await session.execute(
                    text("INSERT INTO memory_vectors(id, embedding) VALUES (:id, :embedding)"),
                    {"id": memory.id, "embedding": embedding_json}
                )
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to store memory vector: {e}")
                # We don't fail the whole operation if vector storage fails, but we log it.
            
            return memory.id

    async def store_fact(self, content: str, user_id: str, *, importance: float = 1.0, decay_rate: float = 0.01) -> int:
        return await self._store("fact", content, user_id, importance=importance, decay_rate=decay_rate)

    async def store_episode(self, content: str, user_id: str, *, importance: float = 1.0, decay_rate: float = 0.01) -> int:  # noqa: E501
        return await self._store("episode", content, user_id, importance=importance, decay_rate=decay_rate)

    async def store_open_loop(self, content: str, user_id: str, *, importance: float = 0.5, decay_rate: float = 0.02) -> int:  # noqa: E501
        return await self._store("open_loop", content, user_id, importance=importance, decay_rate=decay_rate)

    async def forget(self, entry_id: int, user_id: str) -> bool:
        async with self._session_factory() as session:
            stmt = delete(Memory).where(Memory.id == entry_id, Memory.user_id == user_id)
            result = await session.execute(stmt)
            
            if result.rowcount > 0:
                # Also delete from vector table
                await session.execute(
                    text("DELETE FROM memory_vectors WHERE id = :id"),
                    {"id": entry_id}
                )
            
            await session.commit()
            return result.rowcount > 0

    async def retrieve_relevant(
        self, query: str, user_id: str, *, limit: int = 5, similarity_threshold: float | None = None
    ) -> List[MemoryEntry]:
        """Retrieve memories relevant to the query string for a specific user.

        Uses a hybrid approach:
        1. If embeddings available: Vector search (semantic); only results with
           cosine similarity >= similarity_threshold (or the store default) are used.
        2. Fallback/Hybrid: Recency/Decay/Keyword overlap (lexical).

        Args:
            similarity_threshold: Override the store's minimum cosine similarity (0–1) for this call.
        """
        now_ts = int(time.time())
        tokens = set(query.lower().split())
        
        candidates = {}  # id -> (score, row)

        # 1. Vector Search using shared retriever
        try:
            from ..persistence.retrieval import VectorRetriever
            retriever = VectorRetriever(self._session_factory)
            
            vector_results = await retriever.retrieve_by_similarity(
                query=query,
                user_id=user_id,
                table_name="memory_entries",
                vector_table_name="memory_vectors",
                limit=limit * 2
            )
            
            from ..runtime_config import get_config
            threshold = (
                similarity_threshold
                if similarity_threshold is not None
                else get_config().get("similarity_threshold", 0.5)
            )
            for row_dict in vector_results:
                # distance is cosine distance (0-2). 0 = perfect match.
                similarity = max(0, 1 - row_dict['distance'])
                if similarity < threshold:
                    continue
                candidates[row_dict['id']] = {"vector_score": similarity, "id": row_dict['id']}
                
        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")

        async with self._session_factory() as session:
            # 2. Lexical / Recency Search (Baseline)
            # Fetch recent memories to mix in

            stmt = select(Memory).where(Memory.user_id == user_id).order_by(Memory.last_accessed.desc()).limit(100)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            
            # Index rows by ID for easy access
            memory_map = {row.id: row for row in rows}
            
            # Also fetch any missing rows from vector candidates
            missing_ids = [mid for mid in candidates.keys() if mid not in memory_map]
            if missing_ids:
                stmt_missing = select(Memory).where(Memory.id.in_(missing_ids))
                result_missing = await session.execute(stmt_missing)
                for row in result_missing.scalars():
                    memory_map[row.id] = row

        # Scoring Logic
        scored = []
        for mem_id, row in memory_map.items():
            # Base components
            row_last_access = row.last_accessed.timestamp()
            age_hours = max(0.0, (now_ts - row_last_access) / 3600)
            recency_weight = 1 / (1 + age_hours)
            decay_weight = pow(2.71828, -row.decay_rate * age_hours)
            
            # Lexical overlap
            content_tokens = set(row.content.lower().split())
            overlap = len(tokens & content_tokens)
            lexical_score = (row.importance + overlap)
            
            # Vector score
            vector_score = candidates.get(mem_id, {}).get("vector_score", 0.0)
            
            # Combined Score
            # If we have a high vector match, it should boost significantly.
            # If no vector match, we rely on lexical * recency.
            
            # Hybrid formula:
            # score = (Lexical * 0.3 + Vector * 0.7) * Recency * Decay
            # Normalize lexical roughly (assuming 0-5 overlap typically)
            norm_lexical = min(lexical_score / 5.0, 1.0)
            
            if vector_score > 0:
                combined_relevance = (norm_lexical * 0.3) + (vector_score * 0.7)
            else:
                combined_relevance = norm_lexical
                
            final_score = combined_relevance * recency_weight * decay_weight
            
            scored.append((final_score, row))

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
