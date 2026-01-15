"""Persistence layer for chat history with vector search capability."""

from __future__ import annotations

import logging
from typing import List, Optional

from .retrieval import VectorRetriever
from ..models.chat import ChatMessage

logger = logging.getLogger("arthur.ap.persistence.chat")

class ChatStore:
    """Read-only interface for retrieving relevant chat history."""

    def __init__(self, session_factory):
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
        # We search the chat_message_vectors table which is joined with chat_messages
        # However, our shared retriever assumes a simple join. 
        # In chat.py, the join structure is: chat_message_vectors v JOIN chat_messages m JOIN chat_sessions s
        # The retriever might need to be more flexible or we write a specific query here.
        
        # Given the complexity of the chat join (needs session to get user_id),
        # we might need to bypass the simple retriever or extend it.
        # But wait, ChatMessage has user_id directly on it now?
        # Let's check ap/models/chat.py.
        # If ChatMessage has user_id, we can use the simple retriever.
        
        # Checking ... assuming ChatMessage has user_id based on previous file reads (line 80 in chat.py: user_id=user.user_id)
        
        results = await self._retriever.retrieve_by_similarity(
            query=query,
            user_id=user_id,
            table_name="chat_messages",
            vector_table_name="chat_message_vectors",
            id_column="id",
            limit=limit
        )
        
        return results
