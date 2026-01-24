import asyncio
from sqlalchemy import text
from ap.database import get_engine, init_db

async def fix_vector_db():
    engine = get_engine()
    async with engine.begin() as conn:
        print("Checking for existing 'memory_vectors' table...")
        
        # Check current schema
        result = await conn.execute(text("SELECT sql FROM sqlite_master WHERE name = 'memory_vectors'"))
        row = result.fetchone()
        
        if row:
            print(f"Current schema: {row[0]}")
            if "float[384]" in row[0]:
                print("Found 'float[384]' in schema. Dropping table 'memory_vectors' to allow recreation with correct dimensions...")
                await conn.execute(text("DROP TABLE memory_vectors"))
                print("Table dropped.")
            else:
                print("Table 'memory_vectors' does not appear to have 'float[384]'. Skipping drop.")
        else:
            print("Table 'memory_vectors' not found.")

    # Re-initialize DB to create the table with correct schema
    print("Running init_db() to recreate tables...")
    await init_db()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(fix_vector_db())
