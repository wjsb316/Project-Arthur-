"""Persistence layer for chat history with vector search capability."""

from __future__ import annotations

import logging
import json
from typing import List, Optional
from sqlalchemy import select, text
from datetime import datetime, timezone

from .retrieval import VectorRetriever
from ..models.chat import ChatMessage, ChatSession
from ..utils.embedding_factory import embedding_factory

logger = logging.getLogger("arthur.ap.persistence.chat")

class ChatStore:
    """Interface for retrieving and storing chat history."""

    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._retriever = VectorRetriever(session_factory)

    async def retrieve_relevant_history(
        self,
        query: str,
        user_id: str,
        limit: int = 5
    ) -> List[ChatMessage]:
        """Retrieve relevant past chat messages using vector similarity.
        
        Note: This returns raw ChatMessage-like dicts.
        """
        return await self._retriever.retrieve_by_similarity(
            query=query,
            user_id=user_id,
            table_name="chat_messages",
            vector_table_name="chat_message_vectors",
            id_column="id",
            limit=limit
        )

    async def create_session(self, user_id: str, title: str) -> int:
        async with self._session_factory() as session:
            new_session = ChatSession(user_id=user_id, title=title)
            session.add(new_session)
            await session.commit()
            return new_session.id

    async def verify_and_get_session(self, session_id: int, user_id: str) -> int | None:
        """Verify a session belongs to the user and return its ID if valid."""
        async with self._session_factory() as session:
            stmt = select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            return existing.id if existing else None

    async def get_or_create_recent_session(self, user_id: str, title_hint: str) -> int:
        """Get the most recent session or create a new one if none exists or too old."""
        async with self._session_factory() as session:
            stmt = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc()).limit(1)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                return existing.id
            
            new_session = ChatSession(user_id=user_id, title=title_hint[:30])
            session.add(new_session)
            await session.commit()
            return new_session.id

    async def save_message(self, session_id: int, user_id: str, role: str, content: str) -> int:
        """Save a message and its embedding."""
        try:
            # Generate embedding
            doc_text = f"search_document: {content}"
            embedding = embedding_factory.get_embedding(doc_text)
            embedding_json = json.dumps(embedding)
            
            async with self._session_factory() as session:
                msg = ChatMessage(
                    session_id=session_id,
                    user_id=user_id,
                    role=role,
                    content=content
                )
                session.add(msg)
                await session.flush()
                
                # Insert vector
                await session.execute(text("""
                    INSERT INTO chat_message_vectors(id, embedding) VALUES (:id, :embedding)
                """), {"id": msg.id, "embedding": embedding_json})
                
                await session.commit()
                return msg.id
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            raise e
