import asyncio
import sys
import os
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_source_null_handling():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    try:
        # Test upserting with None as source
        await fb.upsert_food(
            name="NullSourceFood", 
            calories=10, protein=1, carbs=1, fat=1, fiber=1, 
            verified=0, 
            source=None
        )
        print("✅ PASS: Handled null source without crashing.")
    except TypeError:
        print("❌ FAIL: upsert_food still doesn't accept source.")
    except Exception as e:
        print(f"❌ FAIL: Crashed on null source: {e}")

if __name__ == "__main__":
    asyncio.run(test_source_null_handling())
