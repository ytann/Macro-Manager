import asyncio
import sys
import os
sys.path.append(os.getcwd())
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_upsert_with_source():
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    test_name = "SourceTestFood"
    test_source = "https://nutrition.gov/apple"
    
    try:
        # Note: Current upsert_food doesn't accept 'source'. 
        # This test will fail (TypeError) until the signature is updated.
        await fb.upsert_food(
            name=test_name, 
            calories=100, protein=1, carbs=20, fat=1, fiber=2, 
            verified=1, 
            source=test_source # This should be added to the method
        )
        print("✅ PASS: upsert_food accepts source argument.")
    except TypeError as e:
        print(f"❌ FAIL: upsert_food does not accept 'source' argument: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_upsert_with_source())
