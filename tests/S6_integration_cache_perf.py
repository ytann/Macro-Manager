import pytest
import asyncio
import time
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService

@pytest.mark.asyncio
async def test_canonicalization_performance_gain():
    """
    Verify that the canonicalization layer prevents slow web searches
    for near-matches, resulting in a significant performance gain.
    """
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    # 1. Seed a verified item
    food_name = "Ultra-Unique-Super-Food-XYZ"
    await fb.upsert_food(
        name=food_name, calories=100, protein=10, carbs=10, fat=10, fiber=1, verified=1
    )
    
    # 2. Measure time for near-match (should be fast)
    typo_name = "Ultra-Unique-Super-Food-XYZZ" # Typo
    
    start_time = time.perf_counter()
    result = await fb.get_nutrition_data(typo_name)
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    
    # 3. Assertions
    assert result is not None
    assert result['calories'] == 100
    assert result.get('verified') == 1, "Should have hit the verified DB entry"
    
    # We expect this to be very fast (< 100ms) compared to a web search (> 2s)
    assert duration < 0.5, f"Canonicalization too slow: {duration:.4f}s"
    print(f"Near-match resolution time: {duration:.4f}s")

if __name__ == "__main__":
    asyncio.run(test_canonicalization_performance_gain())
