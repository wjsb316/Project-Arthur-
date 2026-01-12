from __future__ import annotations

import logging
from typing import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import sqlalchemy.event

# Try to import sqlite_vec; handle failure gracefully for environments without it
try:
    import sqlite_vec
    HAS_SQLITE_VEC = True
except ImportError:
    HAS_SQLITE_VEC = False

from .config import load_settings

logger = logging.getLogger("arthur.ap.database")

class Base(DeclarativeBase):
    pass

# Global engine/sessionmaker
_engine = None
_async_session_maker = None

def get_engine():
    global _engine
    if _engine is None:
        settings = load_settings()
        # Ensure we use a single database for the ORM to manage relationships
        # We will use the 'professional_db_path' as the main DB or define a new one in settings
        # For now, let's assume we are consolidating into arthur.db in the same dir as professional.db
        db_path = settings.professional_db_path.with_name("arthur.db")
        db_url = f"sqlite+aiosqlite:///{db_path}"
        
        _engine = create_async_engine(
            db_url,
            echo=settings.log_level.upper() == "DEBUG",
        )
        
        if HAS_SQLITE_VEC:
            @sqlalchemy.event.listens_for(_engine.sync_engine, "connect")
            def load_extensions(dbapi_conn, connection_record):
                try:
                    dbapi_conn.enable_load_extension(True)
                    sqlite_vec.load(dbapi_conn)
                    dbapi_conn.enable_load_extension(False)
                    logger.info("sqlite-vec extension loaded successfully")
                except Exception as e:
                    logger.warning(f"Failed to load sqlite-vec extension: {e}")

    return _engine


def get_session_maker():
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_maker

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI routes."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session

async def init_db():
    """Initialize database tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Create standard tables
        await conn.run_sync(Base.metadata.create_all)
        
        # Create vector tables if they don't exist
        # We use a virtual table 'memory_vectors' linked to 'memory_entries.id'
        if HAS_SQLITE_VEC:
            await conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
                    id INTEGER PRIMARY KEY,
                    embedding float[384]
                );
            """))
