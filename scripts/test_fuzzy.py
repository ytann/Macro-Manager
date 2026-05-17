import asyncio
from app.services.database import DatabaseManager
from app.services.foodbank import FoodbankService

async def test_fuzzy():
    db_manager = DatabaseManager()
    foodbank = FoodbankService(db_manager)
    
    # Clear foods table to ensure clean test
    await asyncio.to_thread(
        db_manager.run_foodbank, 
        "DELETE FROM foods", 
        commit=True
    )
    
    # Setup test data
    test_foods = [
        {"name": "Palak ka Saag", "cal": 100, "p": 5, "c": 10, "f": 5},
        {"name": "Saag Chicken", "cal": 200, "p": 20, "c": 10, "f": 10},
        {"name": "Saag Gosht", "cal": 250, "p": 25, "c": 10, "f": 15},
    ]
    
    print("Upserting test foods...")
    for food in test_foods:
        await foodbank.upsert_food(
            name=food["name"],
            calories=food["cal"],
            protein=food["p"],
            carbs=food["c"],
            fat=food["f"],
            fiber=0,
            verified=1,
            source="test"
        )
    
    test_queries = [
        ("Saag Chicken", "Saag Chicken"),
        ("Saag Gosht", "Saag Gosht"),
        ("Chicken Saag", "Saag Chicken"),
        ("Palak Saag", "Palak ka Saag"),
        ("Random Saag", "NO MATCH FOUND"),
    ]
    
    for q, expected in test_queries:
        print(f"\nTesting query: {q}")
        result = await foodbank.search_food(q)
        actual = result['name'] if result else "NO MATCH FOUND"
        print(f"Expected: {expected} | Actual: {actual}")
        if actual == expected:
            print("✅ PASS")
        else:
            print("❌ FAIL")


if __name__ == "__main__":
    asyncio.run(test_fuzzy())
