import pytest
import asyncio
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService

@pytest.mark.asyncio
async def test_fuzzy_match_hit():
    """
    Test that a near-match (typo) in the food name still results in a cache hit.
    Example: 'Budhani Potato Chips' is in DB, we search for 'Budhani Chipss'.
    """
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    # 1. Seed the foodbank with a specific item
    food_name = "Zzz-Budhani-Potato-Chips-123"
    await fb.upsert_food(
        name=food_name,
        calories=500,
        protein=5,
        carbs=50,
        fat=30,
        fiber=2,
        verified=1
    )
    
    # 2. Search for the item with a typo
    typo_name = "Zzz-Budhani-Chipss-123" # Typo in the middle
    result = await fb.get_nutrition_data(typo_name)

    
    # 3. Verify it's a hit and not a fallback/web search
    assert result is not None, f"Failed to find {typo_name} via fuzzy matching"
    assert result['calories'] == 500, f"Expected 500 kcal, got {result.get('calories')}"
    assert result.get('verified') == 1, "Result should be verified (from DB)"

@pytest.mark.asyncio
async def test_fuzzy_match_miss():
    """
    Test that a completely different name does NOT result in a fuzzy match.
    """
    db = DatabaseManager()
    fb = FoodbankService(db)
    
    await fb.upsert_food(name="Apple", calories=52, protein=0.3, carbs=14, fat=0.2, fiber=2, verified=1)
    
    # Totally different food
    result = await fb.get_nutrition_data("Pizza")
    
    # It might return a fallback or attempt web search, but it should NOT return Apple's data
    if result:
        assert result.get('calories') != 52, "Should not have matched 'Apple' for 'Pizza'"

if __name__ == "__main__":
    asyncio.run(test_fuzzy_match_hit())
    asyncio.run(test_fuzzy_match_miss())
