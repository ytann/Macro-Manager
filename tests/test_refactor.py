import sys
import os
sys.path.append(os.getcwd())
from app.services.extraction import ExtractionService
import json

test_cases = [
    {"name": "Simple Mixed", "text": "2 boiled eggs and an apple"},
    {"name": "Regional Complex", "text": "1 plate misal pav and 1 glass of lassi"},
    {"name": "Mixed Quantities", "text": "1 piece of puran poli, 200g chicken breast, and 1 bowl of dal"},
]

def run_tests():
    service = ExtractionService()
    for case in test_cases:
        print(f"--- Test: {case['name']} ---")
        print(f"Input: {case['text']}")
        try:
            result = service.parse(case['text'], meal_id="refactor_test")
            print(f"Total Calories: {result.total_calories:.2f} kcal")
            print(f"Items: {[i.name for i in result.items]}")
            print("\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")

if __name__ == "__main__":
    run_tests()
