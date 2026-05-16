import asyncio
from app.services.extraction import ExtractionService
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager

async def test_phonetic_errors():
    print("Testing Phonetic Errors...")
    db = DatabaseManager()
    fb = FoodbankService(db)
    ex = ExtractionService(fb)
    
    test_cases = [
        ("better garlic can't", "butter garlic naan"),
        ("apple cider vinigar", "apple cider vinegar"),
    ]
    
    for input_text, expected in test_cases:
        # Use is_voice=True to trigger the correction logic
        meal_data = await ex.parse(input_text, is_voice=True)
        extracted_names = [item.name.lower() for item in meal_data.items]
        
        # Check if the expected item is in the extracted names
        if any(expected in name for name in extracted_names):
            print(f"SUCCESS: '{input_text}' -> found '{expected}'")
        else:
            print(f"FAIL: '{input_text}' -> expected '{expected}', found {extracted_names}")
            return False
    return True

async def test_empty_input():
    print("Testing Empty Input...")
    db = DatabaseManager()
    fb = FoodbankService(db)
    ex = ExtractionService(fb)
    
    try:
        meal_data = await ex.parse("")
        if not meal_data.items:
            print("SUCCESS: Empty input returned no items.")
            return True
    except Exception as e:
        print(f"FAIL: Empty input crashed: {e}")
        return False

async def main():
    results = []
    results.append(await test_phonetic_errors())
    results.append(await test_empty_input())
    
    if all(results):
        print("\nALL EXTRACTION EDGE CASES PASSED")
        exit(0)
    else:
        print("\nSOME EXTRACTION EDGE CASES FAILED")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
