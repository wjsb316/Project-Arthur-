import asyncio
from sqlalchemy import text
from ap.database import get_engine

async def inspect_schema():
    engine = get_engine()
    async with engine.connect() as conn:
        for table in ['memory_vectors', 'chat_message_vectors']:
            result = await conn.execute(text(f"SELECT sql FROM sqlite_master WHERE name = '{table}'"))
            row = result.fetchone()
            if row:
                print(f"Schema for {table}:\n{row[0]}")
            else:
                print(f"{table} table not found.")

if __name__ == "__main__":
    asyncio.run(inspect_schema())
