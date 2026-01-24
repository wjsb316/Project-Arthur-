import asyncio
from sqlalchemy import text
from ap.database import get_engine

async def inspect_schema():
    engine = get_engine()
    async with engine.connect() as conn:
        # Check sqlite_master for the create statement of memory_vectors
        result = await conn.execute(text("SELECT sql FROM sqlite_master WHERE name = 'memory_vectors'"))
        row = result.fetchone()
        if row:
            print(f"Schema for memory_vectors:\n{row[0]}")
        else:
            print("memory_vectors table not found.")

if __name__ == "__main__":
    asyncio.run(inspect_schema())
