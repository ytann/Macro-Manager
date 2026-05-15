import asyncio
import json
from app.services.extraction import parse_food_log
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def run_test(text):
    print(f"\nTesting: '{text}'")
    try:
        result = await parse_food_log(text, meal_id="test_meal")
        print(f"Result: {json.dumps(result.model_dump(), indent=2)}")
        
        # Basic validations
        for item in result.items:
            if item.grams <= 0:
                print(f"❌ FAIL: Item {item.name} has non-positive weight: {item.grams}")
            else:
                print(f"✅ PASS: Item {item.name} weight: {item.grams}g")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

async def main():
    test_cases = [
        "Dominos Garlic bread",
        "1 packet of masala banana chips",
        "Air fried Chicken THighs",
        "Fried Chicken Thighs",
        "KFC Medium CHicken Popcorn"
    ]
    
    print("Starting Extensive Extraction Tests...\n")
    for case in test_cases:
        await run_test(case)

if __name__ == "__main__":
    asyncio.run(main())
