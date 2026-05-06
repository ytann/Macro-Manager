import sys
import os
import asyncio
sys.path.append(os.getcwd())
from app.services.extraction import ExtractionService
from app.services.foodbank import FoodbankService
from app.services.database import DatabaseManager
import json

test_cases = [
    {
        "name": "Basic Mixed",
        "text": "2 boiled eggs and an apple",
        "expected_items": ["Egg", "Apple"]
    },
    {
        "name": "Regional Complex",
        "text": "1 plate misal pav and 1 glass of lassi",
        "expected_items": ["Misal Pav", "Lassi"]
    },
    {
        "name": "Mixed Quantities",
        "text": "1 piece of puran poli, 200g chicken breast, and 1 bowl of dal",
        "expected_items": ["Puran Poli", "Chicken Breast", "Dal"]
    },
    {
        "name": "Recipe Expansion",
        "text": "1 plate pani puri",
        "expected_items": ["Pani Puri"] # Should contain Pani Puri (Total) and ingredients
    },
    {
        "name": "Guardrail Test",
        "text": "1 piece boiled egg, 1 plate misal pav, 1 bombay sandwich",
        "expected_items": ["Egg", "Misal Pav", "Bombay Sandwich"]
    },
    {
        "name": "Unknown/Rare Food",
        "text": "1 plate of dhokla and some thepla",
        "expected_items": ["Dhokla", "Thepla"]
    },
    {
        "name": "Volume Check (Light)",
        "text": "2 plate sev puri",
        "expected_items": ["Sev Puri"]
    },
    {
        "name": "Volume Check (Heavy)",
        "text": "2 plate rice",
        "expected_items": ["Rice"]
    }
]

async def run_tests():
    db_manager = DatabaseManager()
    foodbank = FoodbankService(db_manager)
    service = ExtractionService(foodbank)
    print("🚀 Starting Final Comprehensive Validation\n")
    print(f"{'Test Case':<25} | {'Status':<10} | {'Calories':<12} | {'Items Found'}")
    print("-" * 70)
    
    all_passed = True
    for case in test_cases:
        try:
            result = await service.parse(case['text'], meal_id="final_test")
            
            # Simple check: did it find the main expected items (case insensitive)?
            found_names = [i.name.lower() for i in result.items]
            missing = [exp for exp in case['expected_items'] if not any(exp.lower() in fn for fn in found_names)]
            
            status = "✅ PASS" if not missing else f"⚠️ MISSING: {missing}"
            if missing: all_passed = False
            
            print(f"{case['name']:<25} | {status:<10} | {result.total_calories:<12.1f} | {', '.join([i.name for i in result.items])}")
        except Exception as e:
            print(f"{case['name']:<25} | ❌ ERROR    | {'N/A':<12} | {e}")
            all_passed = False
    
    print("-" * 70)
    if all_passed:
        print("🎉 ALL TEST CASES PASSED SUCCESSFULLY!")
    else:
        print("⚠️ SOME TEST CASES FAILED. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(run_tests())

