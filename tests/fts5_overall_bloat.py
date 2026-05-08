import asyncio
import sys
import os
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_fts5_bloat():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    test_name = "BloatTestFood"
    
    # Repeatedly upsert the same item
    for i in range(100):
        await fb.upsert_food(test_name, 100+i, 1, 20, 1, 2, 0)
    
    conn = db.get_foodbank_conn()
    # In FTS5, if you use DELETE then INSERT, you might create many hidden segments
    # We can't easily check segment count via SQL, but we can check if the table size is reasonable.
    # Or just check that only one record exists.
    count = conn.execute("SELECT COUNT(*) FROM foods WHERE name = ?", (test_name,)).fetchone()[0]
    conn.close()
    
    if count == 1:
        print("✅ PASS: Only one record exists after multiple upserts.")
    else:
        print(f"❌ FAIL: Multiple records found: {count}")

if __name__ == "__main__":
    asyncio.run(test_fts5_bloat())
