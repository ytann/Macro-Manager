import sys
import os
sys.path.append(os.getcwd())
from app.services.extraction import ExtractionService
import json

test_cases = [
    {"name": "Basic Mixed", "text": "2 boiled eggs and an apple", "expected_items": ["Egg", "Apple"]},
    {"name": "Regional Complex", "text": "1 plate misal pav and 1 glass of lassi", "expected_items": ["Misal Pav", "Lassi"]},
    {"name": "Mixed Quantities", "text": "1 piece of puran poli, 200g chicken breast, and 1 bowl of dal", "expected_items": ["Puran Poli", "Chicken Breast", "Dal"]},
    {"name": "Recipe Expansion", "text": "1 plate pani puri", "expected_items": ["Pani Puri"]},
]

def run_tests():
    service = ExtractionService()
    print("🚀 Batch 1: Basic & Regional\n")
    print(f"{'Test Case':<25} | {'Status':<10} | {'Calories':<12} | {'Items Found'}")
    print("-" * 70)
    
    for case in test_cases:
        try:
            result = service.parse(case['text'], meal_id="final_test")
            found_names = [i.name.lower() for i in result.items]
            missing = [exp for exp in case['expected_items'] if not any(exp.lower() in fn for fn in found_names)]
            status = "✅ PASS" if not missing else f"⚠️ MISSING: {missing}"
            print(f"{case['name']:<25} | {status:<10} | {result.total_calories:<12.1f} | {', '.join([i.name for i in result.items])}")
        except Exception as e:
            print(f"{case['name']:<25} | ❌ ERROR    | {'N/A':<12} | {e}")

if __name__ == "__main__":
    run_tests()
