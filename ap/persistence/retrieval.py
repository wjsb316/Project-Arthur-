"""Shared vector retrieval logic for various data stores."""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from sqlalchemy import text

from ..utils.embedding_factory import embedding_factory

logger = logging.getLogger("arthur.ap.persistence.retrieval")


class VectorRetriever:
    """Helper for performing vector similarity searches on standard tables."""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def retrieve_by_similarity(
        self,
        query: str,
        user_id: str,
        table_name: str,
        vector_table_name: str,
        id_column: str = "id",
        limit: int = 5,
        additional_filters: Optional[dict] = None,
    ) -> List[dict]:
        """Perform a vector similarity search joined with the main table.

        Args:
            query: The search query string.
            user_id: The user ID to filter by.
            table_name: The name of the main table (e.g., 'memory_entries').
            vector_table_name: The name of the vector table (e.g., 'memory_vectors').
            id_column: The primary key column name.
            limit: Maximum number of results.
            additional_filters: Optional dictionary of additional WHERE clauses.

        Returns:
            List[dict]: A list of rows (as dicts) with an added 'distance' key.
        """
        try:
            # Generate embedding for the query
            query_embedding = embedding_factory.get_embedding(query)
            query_embedding_json = json.dumps(query_embedding)

            # Construct SQL query
            # Note: We use raw SQL for the vector distance function as it's specific to sqlite-vec
            filter_clauses = ["m.user_id = :user_id"]
            if additional_filters:
                for col, val in additional_filters.items():
                    filter_clauses.append(f"m.{col} = :{col}")
            
            where_clause = " AND ".join(filter_clauses)
            
            sql = f"""
                SELECT m.*, vec_distance_cosine(v.embedding, :embedding) as distance
                FROM {vector_table_name} v
                JOIN {table_name} m ON v.id = m.{id_column}
                WHERE {where_clause}
                ORDER BY distance ASC
                LIMIT :limit
            """
            
            params = {
                "embedding": query_embedding_json,
                "user_id": user_id,
                "limit": limit
            }
            if additional_filters:
                params.update(additional_filters)

            async with self._session_factory() as session:
                result = await session.execute(text(sql), params)
                rows = result.fetchall()
                
                # Convert rows to dicts
                results = []
                for row in rows:
                    row_dict = dict(row._mapping)
                    results.append(row_dict)
                    
                return results

        except Exception as e:
            logger.error(f"Vector retrieval failed for {table_name}: {e}")
            return []
