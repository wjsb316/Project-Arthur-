import asyncio
import json
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import sqlalchemy.event
import sqlite_vec

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test():
    db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(db_url, echo=True, connect_args={"check_same_thread": False})

    @sqlalchemy.event.listens_for(engine.sync_engine, "connect")
    def load_extensions(dbapi_conn, connection_record):
        try:
            # Attempt to load sqlite-vec
            # Based on ap/database.py logic
            # dbapi_conn is expected to be aiosqlite connection wrapper
            # We need to find the underlying sqlite3 connection
            
            # Print type to debug
            print(f"DEBUG: dbapi_conn type: {type(dbapi_conn)}")
            
            # In some versions of sqlalchemy/aiosqlite, dbapi_conn might be different
            # Let's try to find the sqlite3 connection
            if hasattr(dbapi_conn, "driver_connection"):
                print("DEBUG: has driver_connection")
                conn = dbapi_conn.driver_connection
                if hasattr(conn, "_conn"):
                     print("DEBUG: has _conn")
                     conn = conn._conn
            else:
                conn = dbapi_conn

            print(f"DEBUG: Final conn type: {type(conn)}")
            
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            logger.info("sqlite-vec extension loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sqlite-vec extension: {e}")

    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE chat_sessions (id INTEGER PRIMARY KEY, user_id TEXT)"))
        await conn.execute(text("CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, session_id INTEGER, content TEXT)"))  # noqa: E501
        # Create vector table
        await conn.execute(text("""
            CREATE VIRTUAL TABLE chat_message_vectors USING vec0(
                id INTEGER PRIMARY KEY,
                embedding float[4]
            );
        """))
        
        # Insert dummy data
        await conn.execute(text("INSERT INTO chat_sessions (id, user_id) VALUES (1, 'user1')"))
        await conn.execute(text("INSERT INTO chat_messages (id, session_id, content) VALUES (1, 1, 'hello')"))
        
        # Insert vector
        embedding = [0.1, 0.2, 0.3, 0.4]
        embedding_json = json.dumps(embedding)
        await conn.execute(text("INSERT INTO chat_message_vectors(id, embedding) VALUES (:id, :embedding)"), 
                           {"id": 1, "embedding": embedding_json})

    # Perform search
    async with AsyncSession(engine) as session:
        query_embedding = [0.1, 0.2, 0.3, 0.4]
        query_embedding_json = json.dumps(query_embedding)
        user_id = 'user1'
        
        search_sql = text("""
            SELECT s.id as session_id, vec_distance_cosine(v.embedding, :embedding) as distance
            FROM chat_message_vectors v
            JOIN chat_messages m ON v.id = m.id
            JOIN chat_sessions s ON m.session_id = s.id
            WHERE s.user_id = :user_id
            AND v.embedding MATCH :embedding
            ORDER BY distance ASC
            LIMIT 1
        """)
        
        print("Executing search query...")
        try:
            result = await session.execute(search_sql, {"embedding": query_embedding_json, "user_id": user_id})
            match = result.fetchone()
            print(f"Search result: {match}")
        except Exception as e:
            print(f"Search failed: {e}")
            import traceback
            traceback.print_exc()

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_test())
